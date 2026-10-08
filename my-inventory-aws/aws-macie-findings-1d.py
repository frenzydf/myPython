import boto3
import os
from datetime import datetime, timedelta, timezone

# ------------------------
# Configuración
# ------------------------
REGION = "us-east-1"
AWS_PROFILE = "security"
DAYS_BACK = 1

# Mapeo de AccountId → consola VPC
ACCOUNT_VPC_MAP = {
    os.environ.get("AccountId_1", ""): "VPC1",
    os.environ.get("AccountId_2", ""): "VPC2",
}

# ------------------------
# Cliente Macie
# ------------------------
session = boto3.Session(profile_name=AWS_PROFILE)
macie = session.client("macie2", region_name=REGION)

# ------------------------
# Ventana de tiempo (último día)
# ------------------------
since = datetime.now(timezone.utc) - timedelta(days=DAYS_BACK)
until = datetime.now(timezone.utc)

# ------------------------
# Listar findings con paginación
# ------------------------
finding_ids = []
paginator = macie.get_paginator("list_findings")

pages = paginator.paginate(
    findingCriteria={
        "criterion": {
            "updatedAt": {
                "gte": int(since.timestamp() * 1000),  # Macie usa milisegundos
                "lte": int(until.timestamp() * 1000),
            }
        }
    },
    sortCriteria={
        "attributeName": "severity.score",
        "orderBy": "DESC",
    },
)

for page in pages:
    finding_ids.extend(page.get("findingIds", []))

if not finding_ids:
    print("No se encontraron findings en el último día.")
    exit(0)

# ------------------------
# Obtener detalle de findings
# (la API acepta máximo 25 IDs por llamada)
# ------------------------
all_findings = []
chunk_size = 25

for i in range(0, len(finding_ids), chunk_size):
    chunk = finding_ids[i : i + chunk_size]
    response = macie.get_findings(findingIds=chunk)
    all_findings.extend(response.get("findings", []))

# ------------------------
# Ordenar por severidad (High → Medium → Low)
# Macie usa severity.description con valores: High, Medium, Low
# severity.score: High=3, Medium=2, Low=1
# ------------------------
SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFORMATIONAL": 3}

all_findings.sort(
    key=lambda f: SEVERITY_ORDER.get(
        f.get("severity", {}).get("description", "LOW").upper(), 99
    )
)

# ------------------------
# Imprimir findings
# Format: Severity / Type / BucketName / VPC / User / PublicAccess
# ------------------------
print(f"\n{'='*90}")
print(f"  Macie Findings — último día  ({since.strftime('%Y-%m-%d %H:%M')} UTC → {until.strftime('%Y-%m-%d %H:%M')} UTC)")
print(f"  Total encontrados: {len(all_findings)}")
print(f"{'='*90}\n")

for f in all_findings:
    # --- Severidad (Macie usa description: High/Medium/Low) ---
    severity = f.get("severity", {}).get("description", "Low")

    # --- Tipo de finding ---
    finding_type = f.get("type", "Unknown")

    # --- Bucket afectado ---
    resources_affected = f.get("resourcesAffected", {})
    s3_bucket = resources_affected.get("s3Bucket", {})
    bucket_name = s3_bucket.get("name", "N/A")

    # --- Cuenta → VPC ---
    account_id = f.get("accountId", "")
    vpc_label = ACCOUNT_VPC_MAP.get(account_id, account_id)  # fallback al account ID si no matchea

    # --- Usuario que originó el evento ---
    actor = f.get("policyDetails", {}) or {}
    actor_user = (
        actor.get("actor", {})
             .get("userIdentity", {})
             .get("assumedRole", {})
             .get("principalId", "")
        or actor.get("actor", {})
                .get("userIdentity", {})
                .get("iamUser", {})
                .get("principalId", "")
        or actor.get("actor", {})
                .get("userIdentity", {})
                .get("root", {})
                .get("principalId", "")
        or "N/A"
    )
    # Tomar solo la parte final del principalId (e.g. "AROA.../extwpalomino" → "extwpalomino")
    if ":" in actor_user:
        actor_user = actor_user.split(":")[-1]

    # --- Acceso público del bucket ---
    public_access = s3_bucket.get("publicAccess", {})
    effective_perm = (
        public_access.get("effectivePermission", "NOT_PUBLIC")
        .upper()
        .replace(" ", "_")
    )

    print(
        f"{severity} / {finding_type} / {bucket_name} / {vpc_label} / {actor_user} / {effective_perm}"
    )

print()
