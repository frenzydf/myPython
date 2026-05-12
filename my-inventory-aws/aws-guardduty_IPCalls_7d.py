import boto3
from datetime import datetime, timedelta, timezone

# ------------------------
# Configuración
# ------------------------
REGION = "us-east-1"
FINDING_TYPE = "UnauthorizedAccess:EC2/MaliciousIPCaller.Custom"
DAYS_BACK = 7

# ------------------------
# Inicializar cliente
# ------------------------
session = boto3.Session(profile_name='security')
gd = session.client('guardduty', region_name=REGION)

# ------------------------
# Obtener Detector ID
# ------------------------
detectors = gd.list_detectors()["DetectorIds"]
if not detectors:
    raise Exception("GuardDuty no está habilitado en esta región")

DETECTOR_ID = detectors[0]

# ------------------------
# Calcular timestamp (últimos 7 días)
# ------------------------
since = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
since_epoch = int(since.timestamp())

# ------------------------
# Listar Findings
# ------------------------
response = gd.list_findings(
    DetectorId=DETECTOR_ID,
    FindingCriteria={
        "Criterion": {
            "type": {
                "Eq": [FINDING_TYPE]
            },
            "updatedAt": {
                "Gte": since_epoch
            }
        }
    }
)

finding_ids = response.get("FindingIds", [])

if not finding_ids:
    print("FindingType,AccountId,InstanceId,RemoteIp,Name,Entorno,Grupo,Protocol,LocalPort,UpdatedAt")
    exit(0)

# ------------------------
# Obtener detalles de los Findings
# ------------------------
findings_detail = gd.get_findings(
    DetectorId=DETECTOR_ID,
    FindingIds=finding_ids
)["Findings"]

# ------------------------
# Imprimir encabezado CSV
# ------------------------
print("FindingType,AccountId,InstanceId,RemoteIp,Name,Entorno,Grupo,Protocol,LocalPort,UpdatedAt")

# ------------------------
# Procesar e imprimir resultados CSV
# ------------------------
for f in findings_detail:
    updated_at = f.get("UpdatedAt", "")
    updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))

    # ✅ Condición simple: solo últimos 7 días
    if updated_dt < since:
        continue

    action = f.get("Service", {}).get("Action", {}).get("NetworkConnectionAction", {})
    # imprimir el Tag 'Name' si existe, sino vacío
    tag_name = f.get("Resource", {}).get("InstanceDetails", {}).get("Tags", [])
    name_tag = next((tag['Value'] for tag in tag_name if tag['Key'] == 'Name'), "")
    entorno_tag = next((tag['Value'] for tag in tag_name if tag['Key'] == 'Entorno'), "")
    grupo_tag = next((tag['Value'] for tag in tag_name if tag['Key'] == 'Grupo'), "")
    account_id = f.get("AccountId", "")
    instance_id = f.get("Resource", {}).get("InstanceDetails", {}).get("InstanceId", "")
    remote_ip = action.get("RemoteIpDetails", {}).get("IpAddressV4", "")
    protocol = action.get("Protocol", "")
    count = f.get("Service", {}).get("Count", 0)
    local_port = action.get("LocalPortDetails", {}).get("Port", "")

    print(
        f"MEDIUM / {FINDING_TYPE} / "
        f"{account_id} / {instance_id} / "
        f"{name_tag} / {entorno_tag} / {grupo_tag} / {remote_ip} /{protocol}-{local_port} / Count:{count}"
    )