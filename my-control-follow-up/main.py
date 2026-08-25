#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import boto3
import pandas as pd
from datetime import datetime
from botocore.config import Config

# ============================================================
# CONFIGURACION
# ============================================================

REGION = "us-east-1"

PROFILE_SECURITY = "security"

ACCOUNT_PROFILES = [
    "vpc1",
    "vpc2"
]

EXCEL_FILE = r"G:\Mi unidad\Belcorp\Seguimiento controles.xlsx"

BUCKET_NAME = "belc-securityhub-cspm"

S3_BASE_PATH = "securityhub-cspm"

OUTPUT_FILE = (
    f"securityhub_findings_"
    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
)

# ============================================================
# SESIONES AWS
# ============================================================

security_session = boto3.Session(
    profile_name=PROFILE_SECURITY,
    region_name=REGION
)

s3_client = security_session.client(
    "s3",
    config=Config(
        retries={
            "max_attempts": 10
        }
    )
)

# ============================================================
# EXCEL
# ============================================================

def load_controls():

    df = pd.read_excel(EXCEL_FILE)

    controls = []

    for value in df.iloc[:, 0].dropna():

        value = str(value).strip()

        match = re.match(
            r"^([A-Za-z0-9\.-]+)\s+-\s+(.*)$",
            value
        )

        if not match:
            continue

        controls.append({
            "id": match.group(1).strip(),
            "title": match.group(2).strip()
        })

    return controls


# ============================================================
# S3
# ============================================================

def get_latest_json_files():

    today = datetime.now()

    prefix = (
        f"{S3_BASE_PATH}/"
        f"{today:%Y}/"
        f"{today:%m}/"
        f"{today:%d}/"
    )

    response = s3_client.list_objects_v2(
        Bucket=BUCKET_NAME,
        Prefix=prefix
    )

    latest_files = {}

    pattern = re.compile(
        r"control_status_(VPC\d+)_(\d{8})_(\d{6})\.json$"
    )

    for obj in response.get("Contents", []):

        key = obj["Key"]

        filename = os.path.basename(key)

        match = pattern.search(filename)

        if not match:
            continue

        account = match.group(1)
        file_time = match.group(3)

        if account not in latest_files:

            latest_files[account] = {
                "time": file_time,
                "key": key
            }

            continue

        if file_time > latest_files[account]["time"]:

            latest_files[account] = {
                "time": file_time,
                "key": key
            }

    return latest_files


def load_json_from_s3(key):

    response = s3_client.get_object(
        Bucket=BUCKET_NAME,
        Key=key
    )

    body = response["Body"].read()

    return json.loads(body)


# ============================================================
# CONTROLES
# ============================================================

def extract_standard_name(arn):

    marker = ":subscription/"

    if marker not in arn:
        return None

    return arn.split(marker)[1]


def build_control_catalog():

    latest_files = get_latest_json_files()

    catalog = {}

    for account, data in latest_files.items():

        print(
            f"Cargando JSON {account}: "
            f"{data['key']}"
        )

        document = load_json_from_s3(
            data["key"]
        )

        controls = document.get(
            "Controls",
            {}
        )

        for control_id, control_data in controls.items():

            if control_id not in catalog:

                catalog[control_id] = control_data

    return catalog


# ============================================================
# SECURITY HUB
# ============================================================

def query_findings(profile, generator_id):

    print(
        f"Profile={profile} "
        f"GeneratorId={generator_id}"
    )

    session = boto3.Session(
        profile_name=profile,
        region_name=REGION
    )

    client = session.client(
        "securityhub"
    )

    paginator = client.get_paginator(
        "get_findings"
    )

    filters = {

        "GeneratorId": [
            {
                "Value": generator_id,
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

    findings = []

    for page in paginator.paginate(
        Filters=filters
    ):
        findings.extend(
            page.get("Findings", [])
        )

    return findings


# ============================================================
# TAGS
# ============================================================

def get_tags(resource):

    tags = resource.get(
        "Tags",
        {}
    )

    entorno = tags.get(
        "Entorno",
        "None"
    )

    grupo = tags.get(
        "Grupo",
        "None"
    )

    if not entorno:
        entorno = "None"

    if not grupo:
        grupo = "None"

    return entorno, grupo


# ============================================================
# GENERACION REPORTE
# ============================================================

def write_results(
    file_handle,
    control_id,
    title,
    findings
):

    header = (
        f"{control_id} - {title}"
    )

    print("\n" + header)

    file_handle.write(
        header + "\n\n"
    )

    total = 0

    for finding in findings:

        account_id = finding.get(
            "AwsAccountId",
            "None"
        )

        product_fields = finding.get(
            "ProductFields",
            {}
        )

        control = product_fields.get(
            "ControlId",
            control_id
        )

        resources = finding.get(
            "Resources",
            []
        )

        resource_id = "None"
        entorno = "None"
        grupo = "None"

        if resources:

            resource = resources[0]

            resource_id = resource.get(
                "Id",
                "None"
            )

            entorno, grupo = (
                get_tags(resource)
            )

        line = (
            f"{account_id},"
            f"{control},"
            f"{resource_id},"
            f"{entorno},"
            f"{grupo}"
        )

        print(line)

        file_handle.write(
            line + "\n"
        )

        total += 1

    total_line = (
        f"Total findings: {total}"
    )

    print(total_line)

    file_handle.write(
        "\n" +
        total_line +
        "\n\n"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Cargando controles..."
    )

    controls = load_controls()

    print(
        f"Controles encontrados: "
        f"{len(controls)}"
    )

    print(
        "Construyendo catálogo..."
    )

    control_catalog = (
        build_control_catalog()
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as report:

        for item in controls:

            control_id = item["id"]
            title = item["title"]

            control_data = (
                control_catalog.get(
                    control_id
                )
            )

            if not control_data:

                report.write(
                    f"{control_id} - {title}\n\n"
                )

                report.write(
                    "No encontrado en JSON\n\n"
                )

                continue

            standard_arn = (
                control_data.get(
                    "standard"
                )
            )

            standard_name = (
                extract_standard_name(
                    standard_arn
                )
            )

            if not standard_name:

                report.write(
                    f"{control_id} - {title}\n\n"
                )

                report.write(
                    "No fue posible extraer standard\n\n"
                )

                continue

            generator_id = (
                f"{standard_name}/"
                f"{control_id}"
            )

            merged_findings = []

            for profile in ACCOUNT_PROFILES:

                try:

                    findings = query_findings(
                        profile,
                        generator_id
                    )

                    merged_findings.extend(
                        findings
                    )

                except Exception as e:

                    print(
                        f"ERROR {profile}: {e}"
                    )

            write_results(
                report,
                control_id,
                title,
                merged_findings
            )

    print("\n")
    print("=" * 60)
    print(
        f"Archivo generado: "
        f"{OUTPUT_FILE}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()