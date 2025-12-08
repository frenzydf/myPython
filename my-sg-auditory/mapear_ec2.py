# mapear_ec2.py
import boto3
from collections import defaultdict
from aws_utils import get_tags_from_resource

def chunk_list(lista, tamano_chunk):
    """Divide una lista en trozos del tamaño especificado."""
    for i in range(0, len(lista), tamano_chunk):
        yield lista[i:i + tamano_chunk]

def mapear_ec2(sg_fallidos_data, region_name):
    """
    Identifica instancias EC2 asociadas a SGs fallidos, usando perfiles de AWS CLI.
    """
    print("\n--- 2. Ejecutando: Mapeo de SGs a Instancias EC2 y sus Tags ---")
    
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
            ec2_client = session.client('ec2')
        except Exception as e:
            print(f"❌ ERROR: No se pudo crear la sesión con el perfil {profile_name}. Razón: {e}")
            continue

        # 3. Consultar EC2 en lotes (chunks) de 200
        for sg_chunk in chunk_list(sg_ids, 200):
            try:
                response = ec2_client.describe_instances(
                    Filters=[{'Name': 'instance.group-id', 'Values': sg_chunk}]
                )

                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        # 4. Procesar la instancia y extraer sus tags
                        instance_id = instance['InstanceId']
                        instance_tags = instance.get('Tags', [])
                        
                        entorno_inst, grupo_inst = get_tags_from_resource(instance_tags)
                        
                        # 5. Escribir resultados por cada asociación SG-Instancia
                        for sg in instance.get('SecurityGroups', []):
                            if sg['GroupId'] in sg_chunk:
                                all_results.append({
                                    'SecurityGroupId': sg['GroupId'],
                                    'InstanceId': instance_id,
                                    'EntornoInst': entorno_inst,
                                    'GrupoInst': grupo_inst
                                })
            
            except Exception as e:
                print(f"⚠️ Error al consultar EC2 en perfil {profile_name}: {e}")
                continue

    # 6. Escribir el output a archivo (Objetivo 2)
    with open('output/mapeo_ec2.txt', 'w', encoding='utf-8') as f:
        for item in all_results:
            # Formato: [SG ID], [Instance ID], [Tag Entorno Instancia], [Tag Grupo Instancia]
            line = f"{item['SecurityGroupId']}, {item['InstanceId']}, {item['EntornoInst']}, {item['GrupoInst']}\n"
            f.write(line)
    
    print(f"✅ Encontradas {len(all_results)} asociaciones SG-Instancia.")
    print("   - Output guardado en mapeo_ec2.txt")