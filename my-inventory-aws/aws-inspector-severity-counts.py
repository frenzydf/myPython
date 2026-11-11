import boto3

# ------------------------
# Configuración
# ------------------------
REGION = "us-east-1"
AWS_PROFILE = "vpc2"

# ------------------------
# Cliente Inspector v2
# ------------------------
session = boto3.Session(profile_name=AWS_PROFILE)
inspector = session.client("inspector2", region_name=REGION)

# ------------------------
# CRITICAL / HIGH / MEDIUM: agregación por cuenta (calculada por el servicio)
# ------------------------
totals = {"critical": 0, "high": 0, "medium": 0}

kwargs = {"aggregationType": "ACCOUNT"}
while True:
    response = inspector.list_finding_aggregations(**kwargs)
    for resp in response.get("responses", []):
        counts = resp.get("accountAggregation", {}).get("severityCounts", {})
        for key in totals:
            totals[key] += counts.get(key, 0)

    next_token = response.get("nextToken")
    if not next_token:
        break
    kwargs["nextToken"] = next_token

# ------------------------
# LOW: la agregación no lo devuelve, se cuenta paginando list_findings (solo ACTIVE)
# ------------------------
paginator = inspector.get_paginator("list_findings")
pages = paginator.paginate(
    filterCriteria={
        "severity": [{"comparison": "EQUALS", "value": "LOW"}],
        "findingStatus": [{"comparison": "EQUALS", "value": "ACTIVE"}],
    },
    PaginationConfig={"PageSize": 100},
)
low = sum(len(page.get("findings", [])) for page in pages)

# ------------------------
# Resultado
# ------------------------
print(f"Inspector findings ({AWS_PROFILE} / {REGION})")
print(f"CRITICAL {totals['critical']}")
print(f"HIGH {totals['high']}")
print(f"MEDIUM {totals['medium']}")
print(f"LOW {low}")
print(f"TOTAL {totals['critical'] + totals['high'] + totals['medium'] + low}")
