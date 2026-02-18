import boto3
from botocore.exceptions import ClientError 

# Función para obtener las instancias EC2 del archivo instancias-sg.txt
def get_ec2_instances_from_file(file_path):
    instances = []
    try:
        with open(file_path, 'r') as file:
            for line in file:
                instance_id = line.strip()
                if instance_id:
                    instances.append(instance_id)
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no se encontró.")
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
    return instances

# Función para obtener los grupos de seguridad asociados a una instancia EC2
def get_security_groups_for_instance(instance_id, profile_name):
    try:
        session = boto3.Session(profile_name=profile_name)
        ec2 = session.client('ec2')
        response = ec2.describe_instances(InstanceIds=[instance_id])
        security_groups = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                for sg in instance.get('SecurityGroups', []):
                    security_groups.append(sg['GroupId'])
        return security_groups
    except ClientError as e:
        print(f"Error al obtener los grupos de seguridad para la instancia {instance_id}: {e}")
        return []

if __name__ == "__main__":
    # Especifica el perfil de AWS y la ruta del archivo con las instancias
    profile_name = 'vpc2'
    file_path = 'instancias-sg.txt'
    
    # Obtener las instancias EC2 desde el archivo
    instance_ids = get_ec2_instances_from_file(file_path)
    
    # Imprimir los grupos de seguridad asociados a cada instancia, Imprimir en formato instance-id,sg-id
    for instance_id in instance_ids:
        security_groups = get_security_groups_for_instance(instance_id, profile_name)
        for sg in security_groups:
            print(f"{instance_id},{sg}")