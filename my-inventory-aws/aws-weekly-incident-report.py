"""
Reporte Semanal de Incidentes (GuardDuty + Macie).
"""
import os
from datetime import datetime, timedelta, timezone

import boto3

# ------------------------
# Configuración
# ------------------------
REGION = "us-east-1"
AWS_PROFILE = "security"
DAYS_BACK = 7

MALICIOUS_IP_TYPE = "UnauthorizedAccess:EC2/MaliciousIPCaller.Custom"
BACKLOG_TYPES = {"DefenseEvasion:EC2/UnusualDNSResolver"}
BACKLOG_LOW_TYPES = {"Recon:EC2/PortProbeUnprotectedPort"}
BACKLOG_GROUP_KEYWORDS = ("security-tenable",)  # se busca en tags Name/Grupo

# Mapeo de AccountId → consola VPC (Macie)
ACCOUNT_VPC_MAP = {
    os.environ.get("AccountId_1", ""): "VPC1",
    os.environ.get("AccountId_2", ""): "VPC2",
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "Incident-Reports")
ROOT_COPY_NAME = "Incident-Weekly-Report.txt"

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFORMATIONAL": 3}


# ------------------------
# GuardDuty
# ------------------------
def severity_label(score):
    if score >= 7:
        return "HIGH"
    if score >= 4:
        return "MEDIUM"
    return "LOW"


def get_tag(tags, key):
    return next((t.get("Value", "None") for t in tags if t.get("Key") == key), "None")


def fetch_guardduty_findings(gd, since):
    detectors = gd.list_detectors().get("DetectorIds", [])
    if not detectors:
        raise Exception("GuardDuty no está habilitado en esta región")
    detector_id = detectors[0]

    # updatedAt en GuardDuty se expresa en milisegundos. Sin filtro de service.archived,
    # por lo que se incluyen también los findings archivados.
    criteria = {"Criterion": {"updatedAt": {"Gte": int(since.timestamp() * 1000)}}}

    ids = []
    for page in gd.get_paginator("list_findings").paginate(
        DetectorId=detector_id, FindingCriteria=criteria
    ):
        ids.extend(page.get("FindingIds", []))

    findings = []
    for i in range(0, len(ids), 50):  # get_findings acepta máximo 50 IDs
        resp = gd.get_findings(DetectorId=detector_id, FindingIds=ids[i : i + 50])
        findings.extend(resp.get("Findings", []))
    return findings


def classify_guardduty(f):
    """
    Devuelve (sección, sort_key, línea, ioc_ip, ioc_domain).
    sección: 'main' | 'investigate' | 'backlog'
    """
    ftype = f.get("Type", "")
    severity = severity_label(f.get("Severity", 0))
    account_id = f.get("AccountId", "")
    service = f.get("Service", {}) or {}
    count = service.get("Count", 0)
    archived = bool(service.get("Archived", False))
    action = service.get("Action", {}) or {}

    instance = (f.get("Resource", {}) or {}).get("InstanceDetails", {}) or {}
    instance_id = instance.get("InstanceId") or "None"
    tags = instance.get("Tags", []) or []
    name_tag = get_tag(tags, "Name")
    entorno_tag = get_tag(tags, "Entorno")
    grupo_tag = get_tag(tags, "Grupo")

    domain = (action.get("DnsRequestAction") or {}).get("Domain")
    net = action.get("NetworkConnectionAction") or {}
    api = action.get("AwsApiCallAction") or {}

    base = (
        f"{severity} / {ftype} / {account_id} / {instance_id} / "
        f"{name_tag} / {entorno_tag} / {grupo_tag}"
    )

    # ---- Backlog ----
    is_tenable = any(
        k in f"{name_tag} {grupo_tag}".lower() for k in BACKLOG_GROUP_KEYWORDS
    )
    if (
        archived
        or is_tenable
        or ftype in BACKLOG_TYPES
        or (severity == "LOW" and ftype in BACKLOG_LOW_TYPES)
    ):
        line = f"{base} / Count:{count}"
        if domain:
            line += f" / {domain}"
        return "backlog", (SEVERITY_ORDER[severity], ftype), line, None, None

    # ---- Principal: MaliciousIPCaller ----
    if ftype == MALICIOUS_IP_TYPE:
        remote_ip = (net.get("RemoteIpDetails") or {}).get("IpAddressV4", "None")
        protocol = net.get("Protocol", "None")
        port = (net.get("LocalPortDetails") or {}).get("Port", "None")
        line = f"{base} / {remote_ip} / {protocol}-{port} / Count:{count}"
        return "main", (2, SEVERITY_ORDER[severity], ftype), line, remote_ip, None

    # ---- Principal: dominios a bloquear (cualquier severidad) ----
    if domain:
        line = f"{base} / Count:{count} / {domain}"
        return "main", (0, SEVERITY_ORDER[severity], ftype), line, None, domain

    # ---- Principal: Exfiltration S3 ----
    if ftype.startswith("Exfiltration:S3"):
        remote_ip = (api.get("RemoteIpDetails") or {}).get("IpAddressV4", "None")
        user = (
            (api.get("RemoteIpDetails") or {}).get("User", {}) or {}
        ).get("UserName") or "None"
        api_name = api.get("Api", "None")
        line = (
            f"{severity} / {ftype} / {account_id} / {instance_id} / Count:{count} / "
            f"{user} / {api_name} / {api_name} ({remote_ip})"
        )
        return "main", (1, SEVERITY_ORDER[severity], ftype), line, None, None

    # ---- Investigate: LOW, o MEDIUM sin instancia (información insuficiente) ----
    if severity == "LOW" or (severity == "MEDIUM" and instance_id == "None"):
        line = f"{base} / Count:{count}"
        remote_ip = (api.get("RemoteIpDetails") or {}).get("IpAddressV4")
        if remote_ip:
            line += f" {remote_ip}"
        return "investigate", (SEVERITY_ORDER[severity], ftype), line, None, None

    # ---- Resto de HIGH/MEDIUM con información suficiente → principal ----
    line = f"{base} / Count:{count}"
    return "main", (1, SEVERITY_ORDER[severity], ftype), line, None, None


# ------------------------
# Macie
# ------------------------
def fetch_macie_findings(macie, since, until):
    ids = []
    for page in macie.get_paginator("list_findings").paginate(
        findingCriteria={
            "criterion": {
                "updatedAt": {
                    "gte": int(since.timestamp() * 1000),
                    "lte": int(until.timestamp() * 1000),
                }
            }
        }
    ):
        ids.extend(page.get("findingIds", []))

    findings = []
    for i in range(0, len(ids), 25):  # get_findings acepta máximo 25 IDs
        findings.extend(macie.get_findings(findingIds=ids[i : i + 25]).get("findings", []))
    return findings


def macie_line(f):
    severity = f.get("severity", {}).get("description", "Low")
    finding_type = f.get("type", "Unknown")
    s3_bucket = (f.get("resourcesAffected", {}) or {}).get("s3Bucket", {}) or {}
    bucket_name = s3_bucket.get("name", "N/A")
    account_id = f.get("accountId", "")
    vpc_label = ACCOUNT_VPC_MAP.get(account_id, account_id)

    identity = (
        ((f.get("policyDetails") or {}).get("actor") or {}).get("userIdentity") or {}
    )
    actor_user = (
        (identity.get("assumedRole") or {}).get("principalId")
        or (identity.get("iamUser") or {}).get("principalId")
        or (identity.get("root") or {}).get("principalId")
        or "N/A"
    )
    if ":" in actor_user:
        actor_user = actor_user.split(":")[-1]

    effective = (
        (s3_bucket.get("publicAccess") or {})
        .get("effectivePermission", "NOT_PUBLIC")
        .upper()
        .replace(" ", "_")
    )
    sort_key = SEVERITY_ORDER.get(severity.upper(), 99)
    line = f"{severity} / {finding_type} / {bucket_name} / {vpc_label} / {actor_user} / {effective}"
    return sort_key, line


# ------------------------
# Reporte
# ------------------------
def build_report(gd_findings, macie_findings):
    sections = {"main": [], "investigate": [], "backlog": []}
    ioc_ips, ioc_domains = [], []

    for f in gd_findings:
        section, key, line, ip, domain = classify_guardduty(f)
        sections[section].append((key, line))
        if section == "main":
            if ip and ip not in ioc_ips:
                ioc_ips.append(ip)
            if domain and domain not in ioc_domains:
                ioc_domains.append(domain)

    main_lines = []
    ip_block_started = False
    for key, line in sorted(sections["main"], key=lambda x: x[0]):
        # Salto de línea antes del bloque MaliciousIPCaller (grupo 2)
        if key[0] == 2 and not ip_block_started:
            ip_block_started = True
            if main_lines:
                main_lines.append("")
        main_lines.append(line)
    macie_lines = [l for _, l in sorted((macie_line(f) for f in macie_findings), key=lambda x: x[0])]
    investigate = [l for _, l in sorted(sections["investigate"], key=lambda x: x[0])]
    backlog = [l for _, l in sorted(sections["backlog"], key=lambda x: x[0])]

    lines = ["Incident Weekly Report"]
    lines.extend(main_lines)
    if macie_lines:
        lines.append("")
        lines.extend(macie_lines)
    lines.append("")
    lines.append("-" * 87 + "IoC" + "-" * 52)
    lines.extend(ioc_ips + ioc_domains)
    lines.append("-" * 87 + "Investigate" + "-" * 46)
    lines.extend(investigate)
    lines.append("-" * 87 + "Backlog" + "-" * 50)
    lines.extend(backlog)
    return lines


def save_report(lines, now):
    content = "\n".join(lines) + "\n"
    dated_dir = os.path.join(REPORTS_DIR, now.strftime("%Y"), now.strftime("%m"))
    os.makedirs(dated_dir, exist_ok=True)
    dated_path = os.path.join(dated_dir, f"Incident-Weekly-Report_{now.strftime('%Y-%m-%d')}.txt")
    root_path = os.path.join(BASE_DIR, ROOT_COPY_NAME)
    for path in (dated_path, root_path):  # la copia raíz se reemplaza en cada ejecución
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    return dated_path, root_path


def main():
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=DAYS_BACK)

    session = boto3.Session(profile_name=AWS_PROFILE)
    gd = session.client("guardduty", region_name=REGION)
    macie = session.client("macie2", region_name=REGION)

    gd_findings = fetch_guardduty_findings(gd, since)
    macie_findings = fetch_macie_findings(macie, since, now)

    lines = build_report(gd_findings, macie_findings)
    print("\n".join(lines))

    dated_path, root_path = save_report(lines, now)
    print(f"\nReporte guardado en:\n  {dated_path}\n  {root_path}")


if __name__ == "__main__":
    main()
