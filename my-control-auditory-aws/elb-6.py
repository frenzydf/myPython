#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError, ProfileNotFound

REGION = "us-east-1"
PROFILES = ["vpc1", "vpc2"]


def get_load_balancers_without_delete_protection(profile):
    """
    Obtiene los ALB/NLB sin Delete Protection habilitado.
    """
    session = boto3.Session(
        profile_name=profile,
        region_name=REGION
    )

    elbv2 = session.client("elbv2")

    resultados = []

    paginator = elbv2.get_paginator("describe_load_balancers")

    for page in paginator.paginate():
        for lb in page["LoadBalancers"]:

            try:
                response = elbv2.describe_load_balancer_attributes(
                    LoadBalancerArn=lb["LoadBalancerArn"]
                )

                delete_protection = "false"

                for attr in response["Attributes"]:
                    if attr["Key"] == "deletion_protection.enabled":
                        delete_protection = attr["Value"]
                        break

                if delete_protection.lower() != "true":
                    resultados.append({
                        "Profile": profile,
                        "Region": REGION,
                        "Name": lb["LoadBalancerName"],
                        "Type": lb["Type"],
                        "Scheme": lb["Scheme"],
                        "DNSName": lb["DNSName"],
                        "State": lb["State"]["Code"],
                        "DeleteProtection": delete_protection
                    })

            except ClientError as e:
                print(
                    f"[ERROR] {profile} - "
                    f"{lb['LoadBalancerName']}: {e}"
                )

    return resultados


def main():
    all_results = []

    for profile in PROFILES:

        try:
            print(f"\nConsultando profile: {profile}")

            results = get_load_balancers_without_delete_protection(profile)
            all_results.extend(results)

        except ProfileNotFound:
            print(f"[ERROR] El profile '{profile}' no existe.")
        except Exception as e:
            print(f"[ERROR] Profile {profile}: {e}")

    print("\n" + "=" * 100)
    print("BALANCEADORES SIN DELETE PROTECTION")
    print("=" * 100)

    if not all_results:
        print("\nTodos los balanceadores tienen Delete Protection habilitado.")
        return

    for lb in all_results:
        print(
            f"\nProfile: {lb['Profile']}"
            f"\nRegion: {lb['Region']}"
            f"\nNombre: {lb['Name']}"
            f"\nTipo: {lb['Type']}"
            f"\nScheme: {lb['Scheme']}"
            f"\nEstado: {lb['State']}"
            f"\nDNS: {lb['DNSName']}"
            f"\nDelete Protection: {lb['DeleteProtection']}"
        )


if __name__ == "__main__":
    main()