#!/usr/bin/env python3

import boto3
import csv
from datetime import datetime
from botocore.exceptions import ClientError

REGION = "us-east-1"

PROFILES = [
    "vpc1",
    "vpc2"
]

RECOMMENDED_POLICIES = {
    "ELBSecurityPolicy-TLS13-1-3-2021-06",
    "ELBSecurityPolicy-TLS13-1-3-FIPS-2023-04",
    "ELBSecurityPolicy-TLS13-1-2-Res-2021-06",
    "ELBSecurityPolicy-TLS13-1-2-Res-FIPS-2023-04",
    "ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09",
    "ELBSecurityPolicy-TLS13-1-3-PQ-2025-09",
    "ELBSecurityPolicy-TLS13-1-2-Res-FIPS-PQ-2025-09",
    "ELBSecurityPolicy-TLS13-1-3-FIPS-PQ-2025-09",
}

OUTPUT_FILE = (
    f"ELB17_NON_COMPLIANT_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)

findings = []


def is_compliant(policy):
    return policy in RECOMMENDED_POLICIES


for profile in PROFILES:

    print(f"\n[*] Analizando perfil {profile}")

    try:

        session = boto3.Session(profile_name=profile)

        elbv2 = session.client(
            "elbv2",
            region_name=REGION
        )

        paginator = elbv2.get_paginator(
            "describe_load_balancers"
        )

        for page in paginator.paginate():

            for lb in page["LoadBalancers"]:

                lb_name = lb["LoadBalancerName"]
                lb_arn = lb["LoadBalancerArn"]
                lb_type = lb["Type"]

                try:

                    listeners = elbv2.describe_listeners(
                        LoadBalancerArn=lb_arn
                    )["Listeners"]

                except ClientError as e:

                    print(
                        f"[ERROR] {lb_name}: "
                        f"{e.response['Error']['Message']}"
                    )

                    continue

                for listener in listeners:

                    protocol = listener.get("Protocol")

                    if protocol not in ("HTTPS", "TLS"):
                        continue

                    ssl_policy = listener.get(
                        "SslPolicy",
                        ""
                    )

                    if is_compliant(ssl_policy):
                        continue

                    findings.append({
                        "Profile": profile,
                        "Region": REGION,
                        "LoadBalancer": lb_name,
                        "LoadBalancerType": lb_type,
                        "ListenerArn": listener["ListenerArn"],
                        "Port": listener["Port"],
                        "Protocol": protocol,
                        "SslPolicy": ssl_policy,
                        "Status": "NON_COMPLIANT"
                    })

                    print(
                        f"[NON_COMPLIANT] "
                        f"{profile} | "
                        f"{lb_name} | "
                        f"{protocol}:{listener['Port']} | "
                        f"{ssl_policy}"
                    )

    except Exception as e:

        print(
            f"[ERROR] Perfil {profile}: {str(e)}"
        )


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as csvfile:

    fieldnames = [
        "Profile",
        "Region",
        "LoadBalancer",
        "LoadBalancerType",
        "ListenerArn",
        "Port",
        "Protocol",
        "SslPolicy",
        "Status"
    ]

    writer = csv.DictWriter(
        csvfile,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(findings)

print("\n========================================")
print(f"Región analizada: {REGION}")
print(f"Hallazgos ELB.17: {len(findings)}")
print(f"Reporte CSV: {OUTPUT_FILE}")
print("========================================")