#!/usr/bin/env python3

import boto3
from botocore.exceptions import ClientError

PROFILE = "vpc2"


def main():
    session = boto3.Session(profile_name=PROFILE)

    efs = session.client("efs")
    ec2 = session.client("ec2")

    print("\n=== EFS.6 Validation Report ===\n")

    paginator = efs.get_paginator("describe_file_systems")

    for page in paginator.paginate():
        for fs in page["FileSystems"]:

            fs_id = fs["FileSystemId"]
            fs_name = "N/A"

            for tag in fs.get("Tags", []):
                if tag["Key"] == "Name":
                    fs_name = tag["Value"]

            print(f"\nFileSystem: {fs_id} ({fs_name})")

            try:
                mts = efs.describe_mount_targets(
                    FileSystemId=fs_id
                )["MountTargets"]

                if not mts:
                    print("  No mount targets found")
                    continue

                for mt in mts:
                    subnet_id = mt["SubnetId"]
                    mt_id = mt["MountTargetId"]

                    subnet = ec2.describe_subnets(
                        SubnetIds=[subnet_id]
                    )["Subnets"][0]

                    public_ip_on_launch = subnet.get(
                        "MapPublicIpOnLaunch", False
                    )

                    status = (
                        "NON_COMPLIANT"
                        if public_ip_on_launch
                        else "COMPLIANT"
                    )

                    print(
                        f"  MountTarget : {mt_id}\n"
                        f"  Subnet      : {subnet_id}\n"
                        f"  AZ          : {mt['AvailabilityZoneName']}\n"
                        f"  Public IP   : {public_ip_on_launch}\n"
                        f"  Status      : {status}\n"
                    )

            except ClientError as e:
                print(f"  ERROR: {e}")


if __name__ == "__main__":
    main()
