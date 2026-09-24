import re
import sys
import time
import boto3

QUERY_FILE = "test-query.txt"
OUTPUT_FILE = "ips.txt"
AWS_PROFILE = "vpc1"
AWS_REGION = "us-east-1"

POLL_INTERVAL = 2
MAX_WAIT = 120


def parse_query_file(path: str) -> tuple[str, list[str], int, int]:
    """
    Extrae log groups, ventana de tiempo y query puro desde el archivo.

    Soporta la cabecera que exporta la consola de CloudWatch:
        SOURCE "arn:..." START=-5m END=0s |
    o múltiples ARNs separados por comas.

    Devuelve (query_string, log_group_names, start_offset_seconds, end_offset_seconds).
    start_offset_seconds es negativo (hacia atrás desde ahora).
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    # ── Extraer log groups desde SOURCE ──────────────────────────────────────
    log_groups: list[str] = []
    source_line_match = re.match(
        r'SOURCE\s+(.*?)\s+START=(-?\d+)([smhd])\s+END=(-?\d+)([smhd])\s*\|',
        raw.strip(), re.IGNORECASE
    )

    def to_seconds(value: str, unit: str) -> int:
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        return int(value) * multipliers[unit.lower()]

    start_seconds = -300   # default: -5 minutos
    end_seconds   = 0

    if source_line_match:
        arns_raw = source_line_match.group(1)
        start_seconds = to_seconds(source_line_match.group(2), source_line_match.group(3))
        end_seconds   = to_seconds(source_line_match.group(4), source_line_match.group(5))

        # Extraer cada ARN o nombre entre comillas o sin ellas
        tokens = re.findall(r'"([^"]+)"|\'([^\']+)\'|(\S+)', arns_raw)
        raw_groups = [next(g for g in grp if g) for grp in tokens]

        # Si es un ARN (arn:aws:logs:...), extraer solo el nombre del log group
        for item in raw_groups:
            if item.startswith("arn:"):
                # ARN format: arn:aws:logs:region:account:log-group:/name/here
                parts = item.split(":")
                # El nombre del log group está después de "log-group:"
                lg_index = next(
                    (i + 1 for i, p in enumerate(parts) if p == "log-group"),
                    None
                )
                if lg_index and lg_index < len(parts):
                    log_groups.append(parts[lg_index])
                else:
                    # fallback: último segmento del ARN
                    log_groups.append(parts[-1])
            else:
                log_groups.append(item)

    # ── Eliminar la línea SOURCE … | para quedarnos solo con el query ────────
    query = re.sub(
        r'SOURCE\s+.*?START=\S+\s+END=\S+\s*\|\s*\n?',
        '', raw, flags=re.IGNORECASE
    ).strip()

    return query, log_groups, start_seconds, end_seconds


def run_query(query: str, log_groups: list[str], start_offset: int, end_offset: int) -> list[str]:
    """Ejecuta el query en CloudWatch Logs Insights y devuelve la lista de IPs."""

    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    client  = session.client("logs")

    now        = int(time.time())
    start_time = now + start_offset   # start_offset es negativo
    end_time   = now + end_offset

    print(f"[*] Iniciando query en CloudWatch Logs Insights...")
    print(f"    Perfil   : {AWS_PROFILE}")
    print(f"    Región   : {AWS_REGION}")
    print(f"    Ventana  : últimos {abs(start_offset) // 60} minutos")
    for lg in log_groups:
        print(f"    LogGroup : {lg}")

    # start_query acepta logGroupNames (lista de nombres/ARNs) o logGroupName (único)
    kwargs: dict = {
        "startTime": start_time,
        "endTime":   end_time,
        "queryString": query,
    }
    if log_groups:
        kwargs["logGroupNames"] = log_groups

    response = client.start_query(**kwargs)
    query_id = response["queryId"]
    print(f"[*] QueryId: {query_id}")

    # ── Polling hasta que termine ─────────────────────────────────────────────
    elapsed = 0
    while elapsed < MAX_WAIT:
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

        result = client.get_query_results(queryId=query_id)
        status = result["status"]
        print(f"    Estado : {status}  ({elapsed}s)")

        if status in ("Complete", "Failed", "Cancelled", "Timeout"):
            break

    if status != "Complete":
        print(f"[!] El query terminó con estado: {status}")
        sys.exit(1)

    # ── Extraer IPs del campo ClientIP ────────────────────────────────────────
    ips: list[str] = []
    for row in result["results"]:
        for field in row:
            if field["field"] == "ClientIP":
                ip = field["value"].strip()
                if ip:
                    ips.append(ip)

    return ips


def main() -> None:
    query, log_groups, start_offset, end_offset = parse_query_file(QUERY_FILE)

    print(f"[*] Query leído desde '{QUERY_FILE}'")

    ips = run_query(query, log_groups, start_offset, end_offset)

    if not ips:
        print("[!] No se encontraron IPs. Se sobreescribirá ips.txt vacío.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(ips))
        if ips:
            fh.write("\n")   # newline final

    print(f"[OK] {len(ips)} IP(s) escritas en '{OUTPUT_FILE}'")
    for ip in ips:
        print(f"    {ip}")


if __name__ == "__main__":
    main()
