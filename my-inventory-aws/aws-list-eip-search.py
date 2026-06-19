import subprocess
import json
import csv

IP_FILE = "ip-list.txt"
OUTPUT_FILE = "resultado_eips.csv"
REGION = "us-east-1"
PROFILES = ["vpc1", "vpc2"]


def load_ips(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def run_aws_cli(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        return None


def get_eips(profile):
    cmd = [
        "aws", "ec2", "describe-addresses",
        "--region", REGION,
        "--profile", profile,
        "--output", "json"
    ]
    data = run_aws_cli(cmd)
    return data.get("Addresses", []) if data else []


def get_instance_tags(profile, instance_id):
    cmd = [
        "aws", "ec2", "describe-instances",
        "--instance-ids", instance_id,
        "--region", REGION,
        "--profile", profile,
        "--output", "json"
    ]
    data = run_aws_cli(cmd)
    if not data:
        return {}

    try:
        tags = data["Reservations"][0]["Instances"][0].get("Tags", [])
        return {t["Key"]: t["Value"] for t in tags}
    except (IndexError, KeyError):
        return {}


def get_eni_tags(profile, eni_id):
    cmd = [
        "aws", "ec2", "describe-network-interfaces",
        "--network-interface-ids", eni_id,
        "--region", REGION,
        "--profile", profile,
        "--output", "json"
    ]
    data = run_aws_cli(cmd)
    if not data:
        return {}

    try:
        tags = data["NetworkInterfaces"][0].get("TagSet", [])
        return {t["Key"]: t["Value"] for t in tags}
    except (IndexError, KeyError):
        return {}


def extract_tags(tags_dict):
    return {
        "Entorno": tags_dict.get("Entorno", ""),
        "Grupo": tags_dict.get("Grupo", "")
    }


def main():
    ips_to_search = load_ips(IP_FILE)
    results = []

    # Recorrer perfiles
    for profile in PROFILES:
        print(f"\n🔎 Consultando perfil: {profile}")

        eips = get_eips(profile)

        for ip in ips_to_search:
            found = False

            for eip in eips:
                if eip.get("PublicIp") == ip:
                    found = True

                    allocation_id = eip.get("AllocationId", "")
                    instance_id = eip.get("InstanceId", "")
                    eni_id = eip.get("NetworkInterfaceId", "")

                    tags = {}

                    # Prioridad: instancia
                    if instance_id:
                        tags = get_instance_tags(profile, instance_id)

                    # Si no hay instancia, intentar ENI (NLB / otros)
                    elif eni_id:
                        tags = get_eni_tags(profile, eni_id)

                    filtered_tags = extract_tags(tags)

                    print(f"✅ {ip} encontrada en {profile}")

                    results.append({
                        "IP": ip,
                        "Profile": profile,
                        "Encontrada": "SI",
                        "AllocationId": allocation_id,
                        "InstanceId": instance_id,
                        "NetworkInterfaceId": eni_id,
                        "Entorno": filtered_tags["Entorno"],
                        "Grupo": filtered_tags["Grupo"]
                    })

                    break

            if not found:
                print(f"❌ {ip} NO encontrada en {profile}")

                results.append({
                    "IP": ip,
                    "Profile": profile,
                    "Encontrada": "NO",
                    "AllocationId": "",
                    "InstanceId": "",
                    "NetworkInterfaceId": "",
                    "Entorno": "",
                    "Grupo": ""
                })

    # Guardar CSV
    with open(OUTPUT_FILE, "w", newline="") as csvfile:
        fieldnames = [
            "IP", "Profile", "Encontrada",
            "AllocationId", "InstanceId",
            "NetworkInterfaceId", "Entorno", "Grupo"
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n📄 Resultados exportados a {OUTPUT_FILE}")


if __name__ == "__main__":
    main()