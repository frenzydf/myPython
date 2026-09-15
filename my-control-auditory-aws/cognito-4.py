#!/usr/bin/env python3

import boto3
import csv
from datetime import datetime
from botocore.exceptions import ClientError

REGION = "us-east-1"
PROFILES = ["vpc1", "vpc2"]

OUTPUT_FILE = (
    f"Cognito.4-{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"
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

                addons = user_pool.get("UserPoolAddOns", {})

                advanced_security = addons.get(
                    "AdvancedSecurityMode",
                    "DISABLED"
                )

                if advanced_security == "ENFORCED":
                    compliance = "COMPLIANT"
                    remediation = "No action required"
                else:
                    compliance = "NON_COMPLIANT"
                    remediation = (
                        "Enable Threat Protection "
                        "(AdvancedSecurityMode=ENFORCED)"
                    )

                results.append({
                    "Profile": profile_name,
                    "Region": REGION,
                    "UserPoolName": pool_name,
                    "UserPoolId": pool_id,
                    "AdvancedSecurityMode": advanced_security,
                    "Compliance": compliance,
                    "Remediation": remediation
                })

            except ClientError as error:

                results.append({
                    "Profile": profile_name,
                    "Region": REGION,
                    "UserPoolName": pool_name,
                    "UserPoolId": pool_id,
                    "AdvancedSecurityMode": "ERROR",
                    "Compliance": "ERROR",
                    "Remediation": str(error)
                })

    return results


def main():

    all_results = []

    for profile in PROFILES:

        print(f"\n[+] Evaluando perfil: {profile}")

        try:
            profile_results = evaluate_profile(profile)

            all_results.extend(profile_results)

        except Exception as error:
            print(
                f"[ERROR] Perfil {profile}: {error}"
            )

    print("\nResumen\n")

    non_compliant_count = 0

    for item in all_results:

        if item["Compliance"] == "NON_COMPLIANT":
            non_compliant_count += 1

        print(
            f"{item['Profile']} | "
            f"{item['UserPoolName']} | "
            f"{item['Compliance']} | "
            f"{item['AdvancedSecurityMode']}"
        )

    print(
        f"\nTotal User Pools: {len(all_results)}"
    )

    print(
        f"NON_COMPLIANT: {non_compliant_count}"
    )

    fieldnames = [
        "Profile",
        "Region",
        "UserPoolName",
        "UserPoolId",
        "AdvancedSecurityMode",
        "Compliance",
        "Remediation"
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:

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