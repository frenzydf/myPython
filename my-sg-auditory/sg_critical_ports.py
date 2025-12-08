import boto3
import json

accounts = ['vpc1', 'vpc2']
print("Resource arn, Tag Entorno, Tag Grupo, Protocolo, Puerto Inicial, Puerto Final, CIDR")
count = 0
for account in accounts:
    session = boto3.Session(profile_name=account, region_name="us-east-1")
    sh_client = session.client('securityhub')
    control_id="aws-foundational-security-best-practices/v/1.0.0/EC2.19"
    filters = {
            'GeneratorId': [{'Value': control_id, 'Comparison': 'EQUALS'}],
            'ComplianceStatus': [{'Value': 'FAILED', 'Comparison': 'EQUALS'}],
            'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}]
        }
    paginator = sh_client.get_paginator('get_findings')
    filter_paginator = {'Filters': filters}
    for page in paginator.paginate(**filter_paginator):
        findings = page.get('Findings', [])
        for finding in findings:
            resource_arn = finding.get('Resources', [{}])[0].get('Id', 'None')
            resource_tags = finding.get('Resources', [{}])[0].get('Tags', {})
            tags_list = [{'Key': k, 'Value': v} for k, v in resource_tags.items()]
            entorno = 'None'
            grupo = 'None'
            key_entorno='Entorno'
            key_grupo='Grupo'
            for tag in tags_list:
                key = tag.get('Key') or tag.get('key')
                value = tag.get('Value') or tag.get('value')
                if key == key_entorno: entorno = value
                elif key == key_grupo: grupo = value
            resource_details = finding.get('Resources', [{}])[0].get('Details', {})
            ip_permissions = resource_details["AwsEc2SecurityGroup"]["IpPermissions"]
            for permission in ip_permissions:
                protocol = permission.get("IpProtocol")
                if protocol == "-1":
                    if "IpRanges" in permission and permission["IpRanges"]:
                        for ip_range in permission["IpRanges"]:
                            cidr_ip = ip_range.get("CidrIp")
                            if cidr_ip == "0.0.0.0/0":
                                count += 1
                                print(f"{count}, {resource_arn}, {entorno}, {grupo}, ALL, ALL, ALL, {cidr_ip}")
                elif protocol:
                    from_port = permission.get("FromPort", "N/A")
                    to_port = permission.get("ToPort", "N/A")
                    if "IpRanges" in permission and permission["IpRanges"]:
                        for ip_range in permission["IpRanges"]:
                            cidr_ip = ip_range.get("CidrIp")
                            if cidr_ip == "0.0.0.0/0" and (to_port == 22 or to_port == 3389):
                                count += 1
                                print(f"{count}, {resource_arn}, {entorno}, {grupo}, {protocol.upper()}, {from_port}, {to_port}, {cidr_ip}")

