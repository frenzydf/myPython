# mapear_otros.py
import boto3
from collections import defaultdict
from aws_utils import get_tags_from_resource

def chunk_list(lista, tamano_chunk):
    """Divide una lista en trozos del tamaño especificado."""
    for i in range(0, len(lista), tamano_chunk):
        yield lista[i:i + tamano_chunk]

def mapear_otros_recursos(sg_fallidos_data, region_name):
    """
    Identifica recursos No-EC2 asociados a SGs fallidos, usando perfiles de AWS CLI.
    Audita RDS, ALB/NLB y ENIs (con chunking para ENIs).
    """
    print("\n--- 3. Ejecutando: Mapeo de SGs a Otros Recursos ---")
    
    # 1. Agrupar SGs por ProfileName (que representa la cuenta)
    sgs_por_profile = defaultdict(list)
    for sg in sg_fallidos_data:
        sgs_por_profile[sg['ProfileName']].append(sg)
    
    all_results = []
    
    # 2. Iterar por cada perfil para crear la sesión de auditoría
    for profile_name, sg_list in sgs_por_profile.items():
        sg_ids = [sg['SecurityGroupId'] for sg in sg_list]
        print(f"   > Auditando {len(sg_ids)} SGs usando el Perfil: {profile_name}")
        
        try:
            session = boto3.Session(profile_name=profile_name, region_name=region_name)
        except Exception as e:
            print(f"❌ ERROR: No se pudo crear la sesión con el perfil {profile_name}. Razón: {e}")
            continue

        # ===============================================
        # Sub-objetivo A: Bases de Datos (RDS/Aurora)
        # ===============================================
        try:
            rds_client = session.client('rds', region_name=region_name)
            response = rds_client.describe_db_instances()
            
            for db_instance in response.get('DBInstances', []):
                resource_arn = db_instance.get('DBInstanceArn')
                resource_id = db_instance.get('DBInstanceIdentifier')
                
                # Obtener Tags de RDS
                tags_resp = rds_client.list_tags_for_resource(ResourceName=resource_arn)
                tags_list = tags_resp.get('TagList', [])
                entorno, grupo = get_tags_from_resource(tags_list)
                
                # Buscar SGs asociados
                for sg in db_instance.get('VpcSecurityGroups', []):
                    if sg['VpcSecurityGroupId'] in sg_ids:
                        all_results.append({
                            'SecurityGroupId': sg['VpcSecurityGroupId'],
                            'ResourceType': 'RDS_DBInstance',
                            'ResourceId': resource_id,
                            'EntornoRecurso': entorno,
                            'GrupoRecurso': grupo
                        })
        except Exception as e:
            print(f"⚠️ Error al consultar RDS en perfil {profile_name}: {e}")

        # ===============================================
        # Sub-objetivo B: Load Balancers (ALB/NLB)
        # ===============================================
        try:
            elbv2_client = session.client('elbv2', region_name=region_name)
            response = elbv2_client.describe_load_balancers()
            
            for lb in response.get('LoadBalancers', []):
                resource_arn = lb.get('LoadBalancerArn')
                resource_id = lb.get('LoadBalancerName')
                
                # Obtener Tags de ALB
                tags_resp = elbv2_client.describe_tags(ResourceArns=[resource_arn])
                tags_list = tags_resp['TagDescriptions'][0].get('Tags', [])
                entorno, grupo = get_tags_from_resource(tags_list)
                
                # Buscar SGs asociados
                for sg_id in lb.get('SecurityGroups', []):
                    if sg_id in sg_ids:
                        all_results.append({
                            'SecurityGroupId': sg_id,
                            'ResourceType': lb.get('Type').upper() + '_LoadBalancer',
                            'ResourceId': resource_id,
                            'EntornoRecurso': entorno,
                            'GrupoRecurso': grupo
                        })
        except Exception as e:
            print(f"⚠️ Error al consultar ELBv2 en perfil {profile_name}: {e}")

        # ===============================================
        # Sub-objetivo C: Network Interfaces (ENIs)
        # ===============================================
        """
        try:
            ec2_client = session.client('ec2', region_name=region_name)
            
            # 💡 CORRECCIÓN: Iterar sobre los lotes de 200 SG IDs
            for sg_chunk in chunk_list(sg_ids, 200):
                print(f"      - Consultando ENIs para lote de {len(sg_chunk)} SGs en {profile_name}...")
                
                # Boto3 debe manejar la paginación internamente si el resultado es grande, 
                # pero el filtro de entrada (Values) debe ser <= 200
                response = ec2_client.describe_network_interfaces(
                    Filters=[
                        {'Name': 'group-id', 'Values': sg_chunk}, # Filtro por el lote de SGs (<= 200)
                        {'Name': 'attachment.instance-id', 'Values': ['']}, # ENIs no adjuntas a EC2
                    ]
                )

                for eni in response.get('NetworkInterfaces', []):
                    eni_id = eni.get('NetworkInterfaceId')
                    eni_tags = eni.get('TagSet', [])
                    
                    entorno, grupo = get_tags_from_resource(eni_tags)

                    # Verificar si la ENI está asociada a alguno de los SGs de este lote
                    for sg in eni.get('Groups', []):
                        if sg['GroupId'] in sg_chunk:
                            all_results.append({
                                'SecurityGroupId': sg['GroupId'],
                                'ResourceType': 'Network_Interface',
                                'ResourceId': eni_id,
                                'EntornoRecurso': entorno,
                                'GrupoRecurso': grupo
                            })
        except Exception as e:
            # Capturar errores dentro del bucle de chunking para continuar con las otras cuentas
            print(f"⚠️ Error fatal en consulta de ENIs en perfil {profile_name}: {e}")
        """    
    # 3. Escribir el output a archivo (Objetivo 3)
    with open('output/mapeo_otros.txt', 'w', encoding='utf-8') as f:
        for item in all_results:
            # Formato: [SG ID], [Tipo de Recurso], [ID del Recurso], [Tag Entorno Recurso], [Tag Grupo Recurso]
            line = f"{item['SecurityGroupId']}, {item['ResourceType']}, {item['ResourceId']}, {item['EntornoRecurso']}, {item['GrupoRecurso']}\n"
            f.write(line)

    print(f"✅ Encontrados {len(all_results)} asociaciones SG-Otros Recursos.")
    print("   - Output guardado en mapeo_otros.txt")