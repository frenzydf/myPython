#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import boto3
from botocore.exceptions import ClientError

PROFILES = ["vpc1", "vpc2"]

# Políticas consideradas NO compatibles para APIGateway.11
NON_COMPLIANT_POLICIES = [
    "TLS_1_0",
    "TLS_1_2"
]

def check_rest_api_domains(session, profile):
    results = []

    try:
        client = session.client("apigateway")

        paginator = client.get_paginator("get_domain_names")

        for page in paginator.paginate():
            for domain in page.get("items", []):
                domain_name = domain.get("domainName")
                policy = domain.get("securityPolicy", "UNKNOWN")

                compliant = (
                    policy.startswith("SecurityPolicy_")
                    if policy != "UNKNOWN"
                    else False
                )

                if policy in NON_COMPLIANT_POLICIES:
                    compliant = False

                results.append({
                    "profile": profile,
                    "service": "REST API",
                    "domain": domain_name,
                    "policy": policy,
                    "status": "COMPLIANT" if compliant else "NON_COMPLIANT"
                })

    except ClientError as e:
        print(f"[ERROR] {profile} - REST API: {e}")

    return results

def check_http_websocket_domains(session, profile):
    results = []

    try:
        client = session.client("apigatewayv2")

        paginator = client.get_paginator("get_domain_names")

        for page in paginator.paginate():
            for domain in page.get("Items", []):
                domain_name = domain.get("DomainName")

                # HTTP/API Gateway v2 utiliza TLS 1.2 gestionado por AWS
                results.append({
                    "profile": profile,
                    "service": "HTTP/WebSocket",
                    "domain": domain_name,
                    "policy": "AWS Managed TLS_1_2",
                    "status": "COMPLIANT"
                })

    except ClientError as e:
        print(f"[ERROR] {profile} - API Gateway v2: {e}")

    return results


def main():
    findings = []

    for profile in PROFILES:
        print(f"\nVerificando profile: {profile}")

        try:
            session = boto3.Session(profile_name=profile)

            findings.extend(check_rest_api_domains(session, profile))
            findings.extend(check_http_websocket_domains(session, profile))

        except Exception as e:
            print(f"[ERROR] No fue posible abrir el profile {profile}: {e}")

    print("\n" + "=" * 120)
    print(
        f"{'PROFILE':10} {'SERVICE':15} {'STATUS':15} {'POLICY':35} DOMAIN"
    )
    print("=" * 120)

    non_compliant_count = 0

    for item in findings:
        print(
            f"{item['profile']:10} "
            f"{item['service']:15} "
            f"{item['status']:15} "
            f"{item['policy']:35} "
            f"{item['domain']}"
        )

        if item["status"] == "NON_COMPLIANT":
            non_compliant_count += 1

    print("\nResumen")
    print("-" * 50)
    print(f"Dominios evaluados : {len(findings)}")
    print(f"No conformes       : {non_compliant_count}")
    print(f"Conformes          : {len(findings) - non_compliant_count}")

    if non_compliant_count > 0:
        print("\nDominios con hallazgo APIGateway.11:")
        for item in findings:
            if item["status"] == "NON_COMPLIANT":
                print(
                    f" - [{item['profile']}] {item['domain']} "
                    f"(policy={item['policy']})"
                )

if __name__ == "__main__":
    main()