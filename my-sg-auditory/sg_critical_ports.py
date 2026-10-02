import os
from collections import defaultdict

import boto3

from aws_utils import MEMBER_PROFILES, SECURITY_HUB_PROFILE, get_profile_name_from_account_id

CRITICAL_PORTS = {
    20, 21, 22, 23, 25, 110, 135, 143, 445,
    1433, 1434, 3000, 3306, 3389, 4333, 5000,
    5432, 5500, 5601, 8080, 8088, 8888, 9200, 9300
}
OPEN_CIDRS = {"0.0.0.0/0", "::/0"}
OUTPUT_DIR = "output"
HIGH_PRIORITY_PORTS = {22, 23, 3389, 3306, 5432, 8080, 8088, 8888, 9200, 9300}
MEDIUM_PRIORITY_PORTS = {21, 25, 110, 135, 143, 445, 1433, 1434, 3000, 4333, 5000, 5500, 5601}


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _classify_priority(protocol, from_port, to_port):
    if protocol == 'ALL':
        return 'ALTA'

    if isinstance(from_port, int) and isinstance(to_port, int):
        ports = range(from_port, to_port + 1)
        if any(port in HIGH_PRIORITY_PORTS for port in ports):
            return 'ALTA'
        if any(port in MEDIUM_PRIORITY_PORTS for port in ports):
            return 'MEDIA'

    return 'BAJA'


def _write_executive_summary(results, output_name):
    counts = {'ALTA': 0, 'MEDIA': 0, 'BAJA': 0}
    for item in results:
        level = item.get('Prioridad', 'BAJA')
        counts[level] = counts.get(level, 0) + 1

    summary_path = os.path.join(OUTPUT_DIR, f'{output_name}_resumen.txt')
    with open(summary_path, 'w', encoding='utf-8') as file:
        file.write('RESUMEN EJECUTIVO\n')
        file.write('=================\n')
        file.write(f'Total de hallazgos: {len(results)}\n')
        file.write(f'Alta prioridad: {counts.get("ALTA", 0)}\n')
        file.write(f'Media prioridad: {counts.get("MEDIA", 0)}\n')
        file.write(f'Baja prioridad: {counts.get("BAJA", 0)}\n\n')

        if results:
            file.write('TOP PRIORIDAD\n')
            file.write('------------\n')
            priority_order = {'ALTA': 0, 'MEDIA': 1, 'BAJA': 2}
            for item in sorted(results, key=lambda x: priority_order.get(x.get('Prioridad', 'BAJA'), 2)):
                file.write(
                    f"{item.get('SecurityGroupId', item.get('InstanceId', 'N/A'))} | "
                    f"{item.get('Prioridad', 'BAJA')} | {item.get('Protocolo')} | "
                    f"{item.get('PuertoInicial')} - {item.get('PuertoFinal')} | {item.get('CIDR')}\n"
                )

    print(f"   - Resumen ejecutivo guardado en {summary_path}")
    return summary_path


def _read_failed_sg_ids(file_path="output/sg_fallidos.txt"):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return {line.split(",")[0].strip() for line in file if line.strip()}
    except FileNotFoundError:
        return None


def _iter_securityhub_findings(region_name="us-east-1", sg_ids=None):
    sg_ids_to_check = set(sg_ids) if sg_ids else None
    seen = set()

    try:
        session = boto3.Session(profile_name=SECURITY_HUB_PROFILE, region_name=region_name)
        sh_client = session.client('securityhub', region_name=region_name)
    except Exception as e:
        print(f"⚠️ No se pudo crear la sesión para {SECURITY_HUB_PROFILE}: {e}")
        return

    filters = {
        'GeneratorId': [{'Value': 'aws-foundational-security-best-practices/v/1.0.0/EC2.19', 'Comparison': 'EQUALS'}],
        'ComplianceStatus': [{'Value': 'FAILED', 'Comparison': 'EQUALS'}],
        'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}]
    }

    try:
        paginator = sh_client.get_paginator('get_findings')
        for page in paginator.paginate(Filters=filters):
            for finding in page.get('Findings', []):
                resources = finding.get('Resources', [])
                if not resources:
                    continue

                resource = resources[0]
                security_group = resource.get('Details', {}).get('AwsEc2SecurityGroup', {})
                group_id = security_group.get('GroupId', 'None')
                account_id = finding.get('AwsAccountId', 'None')
                if sg_ids_to_check and group_id not in sg_ids_to_check:
                    continue

                finding_key = (account_id, group_id)
                if finding_key in seen:
                    continue
                seen.add(finding_key)

                yield {
                    'SecurityGroupId': group_id,
                    'AccountId': account_id,
                    'ProfileName': get_profile_name_from_account_id(account_id),
                    'EntornoSG': (resource.get('Tags', {}) or {}).get('Entorno', 'None'),
                    'GrupoSG': (resource.get('Tags', {}) or {}).get('Grupo', 'None'),
                    'IpPermissions': security_group.get('IpPermissions', [])
                }
    except Exception as e:
        print(f"⚠️ Error consultando Security Hub para {SECURITY_HUB_PROFILE}: {e}")


def _iter_opening_rules(ip_permissions):
    for permission in ip_permissions:
        protocol = permission.get('IpProtocol')
        ranges = list(permission.get('IpRanges', [])) + list(permission.get('Ipv6Ranges', []))
        if protocol == '-1':
            for ip_range in ranges:
                cidr = ip_range.get('CidrIp') or ip_range.get('CidrIpv6')
                if cidr in OPEN_CIDRS:
                    yield {
                        'Protocol': 'ALL',
                        'FromPort': 'ALL',
                        'ToPort': 'ALL',
                        'Cidr': cidr,
                        'CriticalPorts': sorted(CRITICAL_PORTS)
                    }
            continue

        if not protocol:
            continue

        from_port = permission.get('FromPort')
        to_port = permission.get('ToPort')
        if not isinstance(from_port, int) or not isinstance(to_port, int):
            continue

        for ip_range in ranges:
            cidr = ip_range.get('CidrIp') or ip_range.get('CidrIpv6')
            if cidr not in OPEN_CIDRS:
                continue

            if any(from_port <= port <= to_port for port in CRITICAL_PORTS):
                yield {
                    'Protocol': str(protocol).upper(),
                    'FromPort': from_port,
                    'ToPort': to_port,
                    'Cidr': cidr,
                    'CriticalPorts': sorted(
                        port for port in CRITICAL_PORTS if from_port <= port <= to_port
                    )
                }


def _iter_nist_ec2_9_findings(region_name="us-east-1"):
    try:
        session = boto3.Session(profile_name=SECURITY_HUB_PROFILE, region_name=region_name)
        sh_client = session.client('securityhub', region_name=region_name)
    except Exception as e:
        print(f"⚠️ No se pudo crear la sesión para {SECURITY_HUB_PROFILE}: {e}")
        return

    filters = {
        'GeneratorId': [{'Value': 'nist-800-53/v/5.0.0/EC2.9', 'Comparison': 'EQUALS'}],
        'ComplianceStatus': [{'Value': 'FAILED', 'Comparison': 'EQUALS'}]
    }

    try:
        paginator = sh_client.get_paginator('get_findings')
        for page in paginator.paginate(Filters=filters):
            for finding in page.get('Findings', []):
                account_id = finding.get('AwsAccountId', 'None')
                profile_name = get_profile_name_from_account_id(account_id)
                if profile_name not in MEMBER_PROFILES:
                    continue

                for resource in finding.get('Resources', []):
                    if resource.get('Type') != 'AwsEc2Instance':
                        continue
                    details = resource.get('Details', {}).get('AwsEc2Instance', {})
                    resource_id = resource.get('Id', '')
                    instance_id = details.get('InstanceId') or resource_id.rsplit('/', 1)[-1]
                    if not instance_id.startswith('i-'):
                        continue

                    yield {
                        'AccountId': account_id,
                        'ProfileName': profile_name,
                        'InstanceId': instance_id,
                        'Title': finding.get('Title', 'NIST EC2.9 FAILED'),
                        'PublicIpAddress': details.get('PublicIpAddress', 'N/A')
                    }
    except Exception as e:
        print(f"⚠️ Error consultando NIST EC2.9 en Security Hub: {e}")


def _build_sg_critical_list(region_name="us-east-1"):
    sg_ids = _read_failed_sg_ids()
    results = []

    for finding in _iter_securityhub_findings(region_name=region_name, sg_ids=sg_ids):
        for rule in _iter_opening_rules(finding['IpPermissions']):
            prioridad = _classify_priority(rule['Protocol'], rule['FromPort'], rule['ToPort'])
            results.append({
                'SecurityGroupId': finding['SecurityGroupId'],
                'AccountId': finding['AccountId'],
                'ProfileName': finding['ProfileName'],
                'EntornoSG': finding['EntornoSG'],
                'GrupoSG': finding['GrupoSG'],
                'Protocolo': rule['Protocol'],
                'PuertoInicial': rule['FromPort'],
                'PuertoFinal': rule['ToPort'],
                'PuertosCriticos': rule['CriticalPorts'],
                'CIDR': rule['Cidr'],
                'Prioridad': prioridad
            })

    return results


def _read_instance_mapping(file_path="output/mapeo_ec2.txt"):
    mapping = defaultdict(list)
    sg_metadata = {}
    try:
        with open("output/sg_fallidos.txt", 'r', encoding='utf-8') as file:
            for line in file:
                parts = [part.strip() for part in line.split(',')]
                if len(parts) >= 2:
                    sg_metadata[parts[0]] = {
                        'AccountId': parts[1],
                        'ProfileName': get_profile_name_from_account_id(parts[1])
                    }
    except FileNotFoundError:
        pass

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                if not line.strip():
                    continue
                parts = [part.strip() for part in line.split(',')]
                if len(parts) < 5:
                    continue
                sg_id, instance_id, entorno, grupo, name = parts[:5]
                metadata = sg_metadata.get(sg_id, {})
                account_id = parts[5] if len(parts) > 5 else metadata.get('AccountId', 'None')
                profile_name = parts[6] if len(parts) > 6 else metadata.get('ProfileName', 'None')
                mapping[(account_id, sg_id)].append({
                    'AccountId': account_id,
                    'ProfileName': profile_name,
                    'InstanceId': instance_id,
                    'EntornoInst': entorno,
                    'GrupoInst': grupo,
                    'InstanceName': name,
                    'PublicIP': parts[7] if len(parts) > 7 else 'N/A',
                })
    except FileNotFoundError:
        return defaultdict(list)
    return mapping


def _write_instance_port_summary(results, nist_findings, output_name):
    instances = {}
    for item in results:
        key = (item['AccountId'], item['InstanceId'])
        summary = instances.setdefault(key, {
            'ProfileName': item['ProfileName'],
            'InstanceId': item['InstanceId'],
            'InstanceName': item['InstanceName'],
            'PublicIP': item['PublicIP'],
            'Ports': set(),
            'SecurityGroups': set(),
            'CIDRs': set(),
            'Priorities': set(),
            'NistEc2_9': key in nist_findings
        })
        summary['Ports'].update(item['PuertosCriticos'])
        summary['SecurityGroups'].add(item['SecurityGroupId'])
        summary['CIDRs'].add(item['CIDR'])
        summary['Priorities'].add(item['Prioridad'])

    priority_order = {'CRITICA': 0, 'ALTA': 1, 'MEDIA': 2, 'BAJA': 3}
    summary_path = os.path.join(OUTPUT_DIR, f'{output_name}_resumen.txt')
    exposed_count = sum(item['NistEc2_9'] for item in instances.values())
    with open(summary_path, 'w', encoding='utf-8') as file:
        file.write('RESUMEN DE PUERTOS CRITICOS POR INSTANCIA\n')
        file.write('=========================================\n')
        file.write(f"Instancias con puertos criticos: {len(instances)}\n")
        file.write(f"Instancias con NIST EC2.9 FAILED: {exposed_count}\n\n")
        file.write('Perfil | Instancia | Nombre | Puertos criticos expuestos | SG | CIDR | EC2.9 | Prioridad instancia | PublicIP\n')

        for item in sorted(instances.values(), key=lambda value: (value['InstanceId'], value['ProfileName'])):
            if item['NistEc2_9']:
                instance_priority = 'CRITICA'
            else:
                instance_priority = min(
                    item['Priorities'], key=lambda priority: priority_order.get(priority, 99)
                )
            file.write(
                f"{item['ProfileName']} | {item['InstanceId']} | {item['InstanceName']} | "
                f"{', '.join(map(str, sorted(item['Ports'])))} | "
                f"{', '.join(sorted(item['SecurityGroups']))} | {', '.join(sorted(item['CIDRs']))} | "
                f"{'FAILED' if item['NistEc2_9'] else 'No'} | {instance_priority} | {item['PublicIP']}\n"
            )

    print(f"   - Resumen por instancia guardado en {summary_path}")
    return summary_path


def _write_nist_ec2_9_report(findings):
    output_file = os.path.join(OUTPUT_DIR, 'instancias_nist_ec2_9.txt')
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write('Perfil | AccountId | InstanceId | PublicIpAddress | Control | Prioridad | Titulo\n')
        for item in sorted(findings.values(), key=lambda value: (value['InstanceId'], value['ProfileName'])):
            file.write(
                f"{item['ProfileName']} | {item['AccountId']} | {item['InstanceId']} | "
                f"{item['PublicIpAddress']} | nist-800-53/v/5.0.0/EC2.9 | CRITICA | {item['Title']}\n"
            )
    print(f"   - Hallazgos NIST EC2.9 guardados en {output_file}")


def identificar_sg_critical_ports(region_name="us-east-1"):
    """Identifica SGs fallidos con reglas de ingreso críticas y públicas."""
    print("\n--- 5. Ejecutando: SGs con Puertos Críticos ---")
    _ensure_output_dir()

    results = _build_sg_critical_list(region_name=region_name)
    output_file = os.path.join(OUTPUT_DIR, 'sg_critical_ports.txt')

    header = "No, SecurityGroupId, AccountId, Perfil, Tag Entorno, Tag Grupo, Protocolo, Puerto Inicial, Puerto Final, Puertos Criticos, CIDR, Prioridad"
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(header + "\n")
        for idx, item in enumerate(results, start=1):
            line = (
                f"{idx}, {item['SecurityGroupId']}, {item['AccountId']}, {item['ProfileName']}, {item['EntornoSG']}, "
                f"{item['GrupoSG']}, {item['Protocolo']}, {item['PuertoInicial']}, "
                f"{item['PuertoFinal']}, {';'.join(map(str, item['PuertosCriticos']))}, "
                f"{item['CIDR']}, {item['Prioridad']}\n"
            )
            file.write(line)

    _write_executive_summary(results, 'sg_critical_ports')
    print(f"✅ Encontrados {len(results)} registros de puertos críticos.")
    print(f"   - Output guardado en {output_file}")
    return results


def identificar_critical_ports_by_instance(region_name="us-east-1", sg_critical=None):
    """Relaciona puertos críticos con instancias EC2 usando el mapeo de SG -> instancias."""
    print("\n--- 6. Ejecutando: Puertos Críticos por Instancia ---")
    _ensure_output_dir()

    if sg_critical is None:
        sg_critical = _build_sg_critical_list(region_name=region_name)
    instance_mapping = _read_instance_mapping()
    nist_findings = {
        (item['AccountId'], item['InstanceId']): item
        for item in _iter_nist_ec2_9_findings(region_name=region_name)
    }
    _write_nist_ec2_9_report(nist_findings)

    results = []
    for item in sg_critical:
        sg_id = item['SecurityGroupId']
        for instance in instance_mapping.get((item['AccountId'], sg_id), []):
            instance_key = (instance['AccountId'], instance['InstanceId'])
            nist_failed = instance_key in nist_findings
            results.append({
                'SecurityGroupId': sg_id,
                'AccountId': instance['AccountId'],
                'ProfileName': instance['ProfileName'],
                'InstanceId': instance['InstanceId'],
                'EntornoInst': instance['EntornoInst'],
                'GrupoInst': instance['GrupoInst'],
                'InstanceName': instance['InstanceName'],
                'PublicIP': instance['PublicIP'],
                'Protocolo': item['Protocolo'],
                'PuertoInicial': item['PuertoInicial'],
                'PuertoFinal': item['PuertoFinal'],
                'PuertosCriticos': item['PuertosCriticos'],
                'CIDR': item['CIDR'],
                'Prioridad': item['Prioridad'],
                'PrioridadInstancia': 'CRITICA' if nist_failed else item['Prioridad'],
                'NistEc2_9': nist_failed
            })

    output_file = os.path.join(OUTPUT_DIR, 'puertos_criticos_por_instancia.txt')
    header = "No, Perfil, AccountId, Instance ID, Tag Entorno, Tag Grupo, Nombre, SecurityGroupId, Protocolo, Puerto Inicial, Puerto Final, Puertos Criticos, CIDR, Prioridad Puerto, Prioridad Instancia, NIST EC2.9, PublicIP"

    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(header + "\n")
        for idx, item in enumerate(results, start=1):
            line = (
                f"{idx}, {item['ProfileName']}, {item['AccountId']}, {item['InstanceId']}, "
                f"{item['EntornoInst']}, {item['GrupoInst']}, {item['InstanceName']}, "
                f"{item['SecurityGroupId']}, {item['Protocolo']}, {item['PuertoInicial']}, "
                f"{item['PuertoFinal']}, {';'.join(map(str, item['PuertosCriticos']))}, "
                f"{item['CIDR']}, {item['Prioridad']}, {item['PrioridadInstancia']}, "
                f"{'FAILED' if item['NistEc2_9'] else 'No'}, {item['PublicIP']}\n"
            )
            file.write(line)

    _write_instance_port_summary(results, nist_findings, 'puertos_criticos_por_instancia')
    print(f"✅ Encontradas {len(results)} asociaciones instancias-puertos críticos.")
    print(f"   - Output guardado en {output_file}")
    return results