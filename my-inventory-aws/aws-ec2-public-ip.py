import boto3
from datetime import datetime, timezone, timedelta

PROFILES = ["vpc1", "vpc2"]
REGION = "us-east-1"

GMT_MINUS_5 = timezone(timedelta(hours=-5))


def get_tag_value(tags, key):
    if not tags:
        return None
    for tag in tags:
        if tag.get("Key") == key:
            return tag.get("Value")
    return None


def get_account_id(session):
    sts = session.client("sts")
    return sts.get_caller_identity()["Account"]


def get_elastic_ips(session):
    """
    Retorna un dict:
    {instance_id: public_ip}
    """
    ec2 = session.client("ec2", region_name=REGION)
    eips = {}

    response = ec2.describe_addresses()
    for addr in response.get("Addresses", []):
        instance_id = addr.get("InstanceId")
        public_ip = addr.get("PublicIp")
        if instance_id and public_ip:
            eips[instance_id] = public_ip

    return eips


def list_ec2_with_public_ip(profile):
    session = boto3.Session(profile_name=profile, region_name=REGION)
    ec2 = session.client("ec2")

    account_id = get_account_id(session)
    elastic_ips = get_elastic_ips(session)

    paginator = ec2.get_paginator("describe_instances")

    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for instance in reservation.get("Instances", []):

                instance_id = instance["InstanceId"]
                public_ipv4 = instance.get("PublicIpAddress")
                elastic_ip = elastic_ips.get(instance_id)

                # Mostrar si tiene Elastic IP o Public IPv4
                if not elastic_ip and not public_ipv4:
                    continue

                ip_to_show = elastic_ip if elastic_ip else public_ipv4

                tags = instance.get("Tags", [])
                name = get_tag_value(tags, "Name")
                grupo = get_tag_value(tags, "Grupo")
                entorno = get_tag_value(tags, "Entorno")

                launch_time = instance.get("LaunchTime")
                if launch_time:
                    launch_time = launch_time.astimezone(GMT_MINUS_5)
                    launch_time_str = launch_time.strftime("%Y/%m/%d %H:%M GMT-5")
                else:
                    launch_time_str = None

                platform_details = instance.get("PlatformDetails")

                print(
                    f"{account_id},"
                    f"{name},"
                    f"{instance_id},"
                    f"{instance['State']['Name']},"
                    f"{grupo},"
                    f"{entorno},"
                    f"{instance['InstanceType']},"
                    f"{ip_to_show},"
                    f"{elastic_ip},"
                    f"{launch_time_str},"
                    f"{platform_details}"
                )


if __name__ == "__main__":
    for profile in PROFILES:
        list_ec2_with_public_ip(profile)