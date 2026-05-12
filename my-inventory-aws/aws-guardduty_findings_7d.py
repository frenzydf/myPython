import boto3
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# ------------------------
# Configuración
# ------------------------
REGION = "us-east-1"
AWS_PROFILE = "security"
EXCLUDED_FINDING_TYPE = "UnauthorizedAccess:EC2/MaliciousIPCaller.Custom"
DAYS_BACK = 7

# ------------------------
# Cliente GuardDuty
# ------------------------
session = boto3.Session(profile_name=AWS_PROFILE)
gd = session.client("guardduty", region_name=REGION)

# ------------------------
# Detector ID
# ------------------------
detectors = gd.list_detectors().get("DetectorIds", [])
if not detectors:
    raise Exception("GuardDuty no está habilitado en esta región")

DETECTOR_ID = detectors[0]

# ------------------------
# Ventana de tiempo
# ------------------------
since = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
since_epoch = int(since.timestamp())

# ------------------------
# Listar findings
# ------------------------
response = gd.list_findings(
    DetectorId=DETECTOR_ID,
    FindingCriteria={
        "Criterion": {
            "updatedAt": {"Gte": since_epoch}
        }
    }
)

finding_ids = response.get("FindingIds", [])
if not finding_ids:
    exit(0)

# ------------------------
# Detalle de findings
# ------------------------
findings = gd.get_findings(
    DetectorId=DETECTOR_ID,
    FindingIds=finding_ids
)["Findings"]

# ------------------------
# Ordenar por FindingType
# ------------------------
findings_by_type = defaultdict(list)
for f in findings:
    ftype = f.get("Type", "")
    if ftype != EXCLUDED_FINDING_TYPE:
        findings_by_type[ftype].append(f)

# ------------------------
# Procesar findings
# ------------------------
for finding_type in sorted(findings_by_type.keys()):
    for f in findings_by_type[finding_type]:

        # Severidad textual
        sev = f.get("Severity", 0)
        if sev >= 7:
            severity = "HIGH"
        elif sev >= 4:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        account_id = f.get("AccountId", "")
        count = f.get("Service", {}).get("Count", 0)

        # ------------------------
        # EC2 details (si aplica)
        # ------------------------
        instance = f.get("Resource", {}).get("InstanceDetails", {})
        instance_id = instance.get("InstanceId", "None")

        tags = instance.get("Tags", [])
        name_tag = next((t["Value"] for t in tags if t["Key"] == "Name"), "None")
        entorno_tag = next((t["Value"] for t in tags if t["Key"] == "Entorno"), "None")
        grupo_tag = next((t["Value"] for t in tags if t["Key"] == "Grupo"), "None")

        # ------------------------
        # Acciones específicas
        # ------------------------
        action = f.get("Service", {}).get("Action", {})
        extra_info = ""

        # DNS / Trojan / DGA
        if "DnsRequestAction" in action:
            domain = action["DnsRequestAction"].get("Domain", "None")
            extra_info = f"/ {domain}"

        # S3 Exfiltration
        elif finding_type.startswith("Exfiltration:S3"):
            aws_api_call = action.get("AwsApiCallAction", {})
            user = aws_api_call.get("RemoteIpDetails", {}) \
                               .get("User", {}).get("UserName", "None")
            api = aws_api_call.get("Api", "None")
            action_type = aws_api_call.get("Api", "None")

            extra_info = f"/ {user} / {action_type} / {api}"

        print(
            f"{severity} / {finding_type} / "
            f"{account_id} / {instance_id} / "
            f"{name_tag} / {entorno_tag} / {grupo_tag} / "
            f"Count:{count} {extra_info}"
        )