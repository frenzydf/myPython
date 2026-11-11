import argparse
import ipaddress
import re
import sys
import time
import boto3

QUERY_FILE = "test-query.txt"
OUTPUT_FILE = "ips.txt"
AWS_PROFILE = "vpc1"
AWS_REGION = "us-east-1"
DEFAULT_IP_FIELD = "ClientIP"
DEFAULT_SAVED_WINDOW_S = -7 * 86400   # si el saved query no trae START=

POLL_INTERVAL = 2
MAX_WAIT = 120


def to_seconds(value: str, unit: str) -> int:
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    return int(value) * multipliers[unit.lower()]


def parse_window(text: str) -> int:
    """Convierte '7d', '12h', '-30m', '1w' a segundos negativos (hacia atrás desde ahora)."""
    m = re.fullmatch(r'-?(\d+)([smhdw])', text.strip(), re.IGNORECASE)
    if not m:
        raise ValueError(f"Ventana inválida: '{text}' (ejemplos: 5m, 12h, 7d)")
    return -to_seconds(m.group(1), m.group(2))


def get_saved_query(name: str) -> tuple[str, list[str], int | None, int | None]:
    """
    Obtiene un saved query de CloudWatch Logs Insights por nombre completo
    (incluye la carpeta, p. ej. 'WAF/Weekly Top IP Report').

    Devuelve (query_string, log_group_names).
    """
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    client = session.client("logs")

    matches = []
    kwargs: dict = {"queryDefinitionNamePrefix": name}
    while True:
        resp = client.describe_query_definitions(**kwargs)
        matches.extend(resp.get("queryDefinitions", []))
        token = resp.get("nextToken")
        if not token:
            break
        kwargs["nextToken"] = token

    exact = [q for q in matches if q["name"] == name]
    if not exact:
        available = ", ".join(sorted(q["name"] for q in matches)) or "(ninguno)"
        print(f"[ERROR] No se encontró el saved query '{name}'. Coincidencias por prefijo: {available}")
        sys.exit(1)

    qd = exact[0]
    query, groups, start, end = parse_query_text(qd["queryString"])
    groups = groups or [_arn_to_name(g) for g in qd.get("logGroupNames", [])]
    return query, groups, start, end


def _arn_to_name(item: str) -> str:
    """Convierte un ARN de log group en su nombre; deja intactos los nombres."""
    if item.startswith("arn:") and ":log-group:" in item:
        return item.split(":log-group:", 1)[1].rstrip(":*")
    return item


def parse_query_text(raw: str) -> tuple[str, list[str], int | None, int | None]:
    """
    Separa las cabeceras SOURCE ... | del texto del query.

    Soporta una o varias cláusulas (formato de la consola de CloudWatch):
        SOURCE "arn:..." START=-5m END=0s |
        SOURCE "arn:..." | SOURCE "arn:..." |
    y múltiples ARNs separados por comas.

    Devuelve (query, log_group_names, start_offset_s, end_offset_s).
    Los offsets son negativos (hacia atrás desde ahora) o None si no hay START/END.
    """
    log_groups: list[str] = []
    start_seconds: int | None = None
    end_seconds: int | None = None
    rest = raw.strip()

    while True:
        m = re.match(r'SOURCE\s+(.*?)\s*\|\s*', rest, re.IGNORECASE | re.DOTALL)
        if not m:
            break
        clause = m.group(1)
        rest = rest[m.end():]

        sm = re.search(r'START=(-?\d+)([smhdw])', clause, re.IGNORECASE)
        em = re.search(r'END=(-?\d+)([smhdw])', clause, re.IGNORECASE)
        if sm and start_seconds is None:
            start_seconds = to_seconds(sm.group(1), sm.group(2))
        if em and end_seconds is None:
            end_seconds = to_seconds(em.group(1), em.group(2))
        clause = re.sub(r'(START|END)=\S+', '', clause, flags=re.IGNORECASE)

        for tok in re.findall(r'"([^"]+)"|\'([^\']+)\'|([^\s,]+)', clause):
            item = next(g for g in tok if g)
            name = _arn_to_name(item)
            if name not in log_groups:
                log_groups.append(name)

    return rest.strip(), log_groups, start_seconds, end_seconds


def parse_query_file(path: str) -> tuple[str, list[str], int, int]:
    """Lee un archivo de query y devuelve (query, log_groups, start_offset, end_offset)."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    query, log_groups, start, end = parse_query_text(raw)
    return query, log_groups, (-300 if start is None else start), (0 if end is None else end)

def run_query(query: str, log_groups: list[str], start_offset: int, end_offset: int,
              ip_field: str = DEFAULT_IP_FIELD) -> list[str]:
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
    print(f"    Campo IP : {ip_field}")
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

    # ── Extraer IPs del campo indicado (sin duplicados, orden preservado) ─────
    def is_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    rows = result["results"]
    field_names = {f["field"] for row in rows for f in row}
    if rows and ip_field not in field_names:
        print(f"[!] El campo '{ip_field}' no existe en los resultados. Campos: {sorted(field_names)}")
        print("    Use --ip-field para indicar la columna correcta.")
        sys.exit(1)

    ips: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for field in row:
            if field["field"] == ip_field:
                ip = field["value"].strip()
                if ip and is_ip(ip) and ip not in seen:
                    seen.add(ip)
                    ips.append(ip)

    return ips


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ejecuta un query de CloudWatch Logs Insights y genera ips.txt")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--query-file", default=QUERY_FILE,
                     help=f"Archivo con el query (default: {QUERY_FILE})")
    src.add_argument("--saved-query", metavar="NAME",
                     help="Nombre completo de un saved query, p. ej. 'WAF/Weekly Top IP Report'")
    p.add_argument("--window", help="Ventana hacia atrás (5m, 12h, 7d). Para saved queries el default es "
                                    "7d; para archivos, la del encabezado SOURCE.")
    p.add_argument("--log-group", action="append", default=[],
                   help="Log group (repetible). Reemplaza a los del query si se indica.")
    p.add_argument("--ip-field", default=DEFAULT_IP_FIELD,
                   help=f"Columna del resultado que contiene la IP (default: {DEFAULT_IP_FIELD})")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.saved_query:
        query, log_groups, q_start, q_end = get_saved_query(args.saved_query)
        if args.window:
            start_offset, end_offset = parse_window(args.window), 0
        else:
            start_offset = DEFAULT_SAVED_WINDOW_S if q_start is None else q_start
            end_offset = 0 if q_end is None else q_end
        print(f"[*] Saved query '{args.saved_query}' obtenido de CloudWatch")
    else:
        query, log_groups, start_offset, end_offset = parse_query_file(args.query_file)
        if args.window:
            start_offset = parse_window(args.window)
            end_offset = 0
        print(f"[*] Query leído desde '{args.query_file}'")

    if args.log_group:
        log_groups = args.log_group

    # start_query(logGroupNames=...) solo acepta nombres, no ARNs
    log_groups = [lg.split(":log-group:", 1)[1].rstrip(":*") if lg.startswith("arn:") and ":log-group:" in lg
                  else lg for lg in log_groups]

    if not log_groups:
        print("[ERROR] No hay log groups definidos. Use --log-group para indicarlos.")
        sys.exit(1)

    ips = run_query(query, log_groups, start_offset, end_offset, args.ip_field)

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
