import boto3


def identificar_sg_critical_ports():
    accounts = ['vpc1', 'vpc2']
    output_file = "sg_critical_ports.txt"

    header = "No, Resource arn, Tag Entorno, Tag Grupo, Protocolo, Puerto Inicial, Puerto Final, CIDR"

    print(header)

    count = 0

    with open(output_file, "w") as file:
        file.write(header + "\n")

        for account in accounts:
            session = boto3.Session(profile_name=account, region_name="us-east-1")
            sh_client = session.client('securityhub')

            control_id = "aws-foundational-security-best-practices/v/1.0.0/EC2.19"

            filters = {
                'GeneratorId': [{'Value': control_id, 'Comparison': 'EQUALS'}],
                'ComplianceStatus': [{'Value': 'FAILED', 'Comparison': 'EQUALS'}],
                'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}]
            }

            paginator = sh_client.get_paginator('get_findings')

            for page in paginator.paginate(Filters=filters):
                findings = page.get('Findings', [])

                for finding in findings:
                    resource = finding.get('Resources', [{}])[0]

                    resource_arn = resource.get('Id', 'None')
                    resource_id = resource.get('Details', {}).get('AwsEc2SecurityGroup', {}).get('GroupId', 'None')
                    resource_tags = resource.get('Tags', {})

                    entorno = resource_tags.get('Entorno', 'None')
                    grupo = resource_tags.get('Grupo', 'None')

                    resource_details = resource.get('Details', {})
                    ip_permissions = resource_details.get("AwsEc2SecurityGroup", {}).get("IpPermissions", [])

                    for permission in ip_permissions:
                        protocol = permission.get("IpProtocol")

                        # Caso 1: Todo abierto
                        if protocol == "-1":
                            for ip_range in permission.get("IpRanges", []):
                                cidr_ip = ip_range.get("CidrIp")

                                if cidr_ip == "0.0.0.0/0":
                                    count += 1
                                    line = f"{count}, {resource_id}, {entorno}, {grupo}, ALL, ALL, ALL, {cidr_ip}"
                                    print(line)
                                    file.write(line + "\n")

                        # Caso 2: Puertos críticos
                        elif protocol:
                            from_port = permission.get("FromPort")
                            to_port = permission.get("ToPort")

                            critical_ports = [20, 21, 22, 23, 25, 110, 135, 143, 445,
                                              1433, 1434, 3000, 3306, 3389, 4333, 5000,
                                              5432, 5500, 5601, 8080, 8088, 8888, 9200, 9300]

                            if isinstance(from_port, int) and isinstance(to_port, int):
                                for ip_range in permission.get("IpRanges", []):
                                    cidr_ip = ip_range.get("CidrIp")

                                    if cidr_ip == "0.0.0.0/0" and any(from_port <= p <= to_port for p in critical_ports):
                                        count += 1
                                        line = f"{count},{resource_id},{entorno},{grupo},{protocol.upper()},{from_port},{to_port},{cidr_ip}"
                                        print(line)
                                        file.write(line + "\n")

    print(f"\nResultados guardados en: {output_file}")
    return count