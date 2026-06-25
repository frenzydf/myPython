#!/usr/bin/env python3

import boto3

PROFILES = ["vpc1", "vpc2"]
REGION = "us-east-1"


def get_findings(profile):
    session = boto3.Session(profile_name=profile)
    client = session.client("securityhub", region_name=REGION)

    paginator = client.get_paginator("get_findings")

    response_iterator = paginator.paginate(
        Filters={
            "GeneratorId": [
                {
                    "Value": "aws-foundational-security-best-practices/v/1.0.0/EC2.9",
                    "Comparison": "EQUALS"
                }
            ],
            "ComplianceStatus": [
                {
                    "Value": "FAILED",
                    "Comparison": "EQUALS"
                }
            ],
            "WorkflowStatus": [
                {
                    "Value": "NEW",
                    "Comparison": "EQUALS"
                }
            ]
        }
    )

    for page in response_iterator:
        for finding in page["Findings"]:
            process_finding(finding)


def process_finding(finding):
    account_id = finding.get("AwsAccountId", "")

    # Control ID
    generator = finding.get("GeneratorId", "")
    control_id = generator.split("/")[-1] if "/" in generator else ""

    instance_id = ""
    tag_name = ""
    tag_entorno = ""

    resources = finding.get("Resources", [])

    if resources:
        resource = resources[0]

        if resource.get("Type") == "AwsEc2Instance":

            # Instance ID / ARN
            instance_id = resource.get("Id", "")

            # ✅ TAGS COMO DICCIONARIO (tu caso real)
            tags = resource.get("Tags", {})

            if isinstance(tags, dict):
                tag_name = tags.get("Name", "")
                tag_entorno = tags.get("Entorno", "")

    print(f"{tag_name},{account_id},{control_id},{instance_id},{tag_entorno}")


if __name__ == "__main__":
    for profile in PROFILES:
        get_findings(profile)