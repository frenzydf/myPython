#!/usr/bin/env python3

import boto3
from botocore.config import Config

PROFILE = "vpc1"
GENERATOR_ID = "nist-800-53/v/5.0.0/ELB.17"


def get_environment(text):
    """
    Detecta ambiente según el nombre.
    """
    text = text.upper()

    if "PRD" in text or "PROD" in text:
        return "PRD"
    elif "DEV" in text:
        return "DEV"
    elif "QAS" in text or "QA" in text:
        return "QAS"
    elif "UAT" in text:
        return "UAT"
    else:
        return "N/A"


def main():

    session = boto3.Session(profile_name=PROFILE)

    sh = session.client(
        "securityhub",
        config=Config(retries={"max_attempts": 10})
    )

    paginator = sh.get_paginator("get_findings")

    pages = paginator.paginate(
        Filters={
            "GeneratorId": [
                {
                    "Value": GENERATOR_ID,
                    "Comparison": "EQUALS"
                }
            ],
            "ComplianceStatus": [
                {
                    "Value": "FAILED",
                    "Comparison": "EQUALS"
                }
            ],
            "RecordState": [
                {
                    "Value": "ACTIVE",
                    "Comparison": "EQUALS"
                }
            ]
        }
    )

    printed = set()

    for page in pages:

        for finding in page["Findings"]:

            account_id = finding.get("AwsAccountId", "")

            for resource in finding.get("Resources", []):

                resource_arn = resource.get("Id", "")

                env = get_environment(resource_arn)

                key = f"{account_id}|{resource_arn}"

                if key in printed:
                    continue

                printed.add(key)

                print(
                    f"{account_id},ELB.17,{resource_arn},{env}"
                )


if __name__ == "__main__":
    main()
