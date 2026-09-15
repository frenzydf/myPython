#!/usr/bin/env python3

import boto3
import csv
from datetime import datetime
from botocore.exceptions import ClientError

REGION = "us-east-1"
PROFILES = ["vpc1", "vpc2"]

OUTPUT_FILE = (
    f"Cognito.6-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
)


def evaluate_profile(profile_name):

    session = boto3.Session(
        profile_name=profile_name,
        region_name=REGION
    )

    client = session.client("cognito-idp")

    results = []

    paginator = client.get_paginator("list_user_pools")

    for page in paginator.paginate(MaxResults=60):

        for pool in page["UserPools"]:

            pool_id = pool["Id"]
            pool_name = pool["Name"]

            try:

                response = client.describe_user_pool(
                    UserPoolId=pool_id
                )

                user_pool = response["UserPool"]

                deletion_protection = user_pool.get(
                    "DeletionProtection",
                    "INACTIVE"
                )

                compliance = (
                    "COMPLIANT"
                    if deletion_protection == "ACTIVE"
                    else "NON_COMPLIANT"
                )

                remediation = (
                    "No action required"
                    if compliance == "COMPLIANT"
                    else (
                        "Run: aws cognito-idp update-user-pool "
                        f"--user-pool-id {pool_id} "
                        "--deletion-protection ACTIVE"
                    )
                )

                results.append({
                    "Profile": profile_name,
                    "Region": REGION,
                    "UserPoolName": pool_name,
                    "UserPoolId": pool_id,
                    "DeletionProtection": deletion_protection,
                    "Compliance": compliance,
                    "Remediation": remediation
                })

            except ClientError as error:

                results.append({
                    "Profile": profile_name,
                    "Region": REGION,
                    "UserPoolName": pool_name,
                    "UserPoolId": pool_id,
                    "DeletionProtection": "ERROR",
                    "Compliance": "ERROR",
                    "Remediation": str(error)
                })

    return results


def main():

    all_results = []

    for profile in PROFILES:

        print(f"\n[+] Evaluando perfil: {profile}")

        try:
            all_results.extend(
                evaluate_profile(profile)
            )

        except Exception as error:
            print(
                f"[ERROR] {profile}: {error}"
            )

    non_compliant = 0

    print("\n=== RESULTADOS ===\n")

    for item in all_results:

        if item["Compliance"] == "NON_COMPLIANT":
            non_compliant += 1

        print(
            f"{item['Profile']} | "
            f"{item['UserPoolName']} | "
            f"{item['DeletionProtection']} | "
            f"{item['Compliance']}"
        )

    print("\n=== RESUMEN ===")
    print(f"Total User Pools : {len(all_results)}")
    print(f"NON_COMPLIANT    : {non_compliant}")

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:

        fieldnames = [
            "Profile",
            "Region",
            "UserPoolName",
            "UserPoolId",
            "DeletionProtection",
            "Compliance",
            "Remediation"
        ]

        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in all_results:
            writer.writerow(row)

    print(
        f"\nCSV generado: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()