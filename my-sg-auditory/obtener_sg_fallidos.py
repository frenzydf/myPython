# obtener_sg_fallidos.py
import boto3
from aws_utils import get_tags_from_resource, get_profile_name_from_account_id

SECURITY_HUB_PROFILE = 'securityhub'

def obtener_sg_fallidos(region_name="us-east-1", control_id="aws-foundational-security-best-practices/v/1.0.0/EC2.19"):
    print(f"\n--- 1. Ejecutando: Obtener SG Fallidos de Security Hub ({region_name}) ---")
    try:
        session = boto3.Session(profile_name=SECURITY_HUB_PROFILE, region_name=region_name)
        sh_client = session.client('securityhub')
    except Exception as e:
        print(f"❌ Error al inicializar el cliente Boto3: {e}")
        exit()
    
    sg_fallidos_data = []
    filters = {
        'GeneratorId': [{'Value': control_id, 'Comparison': 'EQUALS'}],
        'ComplianceStatus': [{'Value': 'FAILED', 'Comparison': 'EQUALS'}],
        'WorkflowStatus': [{'Value': 'NEW', 'Comparison': 'EQUALS'}]
    }
    try:
        paginator = sh_client.get_paginator('get_findings')
        parametros_paginacion = {'Filters': filters}

        for pagina in paginator.paginate(**parametros_paginacion):
            findings = pagina.get('Findings', [])
            for finding in findings:
                resource_arn = finding.get('Resources', [{}])[0].get('Id', 'None')
                sg_id = resource_arn.split('/')[-1]
                account_id = finding.get('AwsAccountId', 'None')
                profile_name = get_profile_name_from_account_id(account_id)
                resource_tags = finding.get('Resources', [{}])[0].get('Tags', {})
                tags_list = [{'Key': k, 'Value': v} for k, v in resource_tags.items()]
                entorno, grupo = get_tags_from_resource(tags_list)
                sg_fallidos_data.append({
                    'SecurityGroupId': sg_id,
                    'AccountId': account_id,
                    'ProfileName': profile_name,
                    'EntornoSG': entorno,
                    'GrupoSG': grupo
                })
    except Exception as e:
        print(f"❌ ERROR al obtener hallazgos de Security Hub: {e}")
        return []
    print(f"✅ Encontrados {len(sg_fallidos_data)} Security Groups fallidos.")
    # Escribir el output a archivo (Objetivo 1)
    with open('sg_fallidos.txt', 'w', encoding='utf-8') as f:
        for item in sg_fallidos_data:
            # Formato: [SG ID], [Account ID], [Tag Entorno SG], [Tag Grupo SG]
            line = f"{item['SecurityGroupId']}, {item['AccountId']}, {item['EntornoSG']}, {item['GrupoSG']}\n"
            f.write(line)
    print("   - Output guardado en sg_fallidos.txt")
    
    return sg_fallidos_data