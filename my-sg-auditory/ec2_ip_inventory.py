import boto3


def obtener_info_ip_instancia(instance_id,ec2):
    """
    Identifica si una instancia es pública/privada y devuelve su IP pública si existe.
    """
    try:
        # 2. Describir la instancia por su ID
        response = ec2.describe_instances(
            InstanceIds=[instance_id]
        )

        # La información de la instancia se encuentra en la lista 'Reservations'
        # y luego dentro de la lista 'Instances'.
        instance_data = response['Reservations'][0]['Instances'][0]
        
        # 3. Identificar si es pública o privada
        # Una instancia se considera pública si tiene una 'PublicIpAddress' asignada.
        # También se puede verificar si la propiedad 'PublicDnsName' está presente.
        
        public_ip = instance_data.get('PublicIpAddress')
        private_ip = instance_data.get('PrivateIpAddress')

        print(f"--- Información para la Instancia ID: **{instance_id}** ---")
        print(f"IP Privada: **{private_ip}**")

        if public_ip:
            print("Tipo de Instancia: **Pública** 🟢")
            print(f"IP Pública Asignada: **{public_ip}**")
        else:
            # Si no hay PublicIpAddress, generalmente es una instancia privada
            # lanzada en una subred privada, o la IP pública fue desasociada.
            # Nota: También podría ser una instancia en una subred pública 
            # que fue lanzada sin asignación automática de IP pública.
            print("Tipo de Instancia: **Privada** 🔒 (o sin IP pública asignada)")
            print("IP Pública Asignada: **N/A**")

    except Exception as e:
        print(f"Error al procesar la instancia {instance_id}: {e}")

# --- Ejemplo de Uso ---
# Reemplaza 'i-xxxxxxxxxxxxxxxx' con el ID real de tu instancia EC2
#INSTANCE_ID_A_CONSULTAR = 'i-0123456789abcdef0' 
#obtener_info_ip_instancia(INSTANCE_ID_A_CONSULTAR)

# --- Para listar todas las instancias y sus IPs ---
def listar_todas_las_ips():
    accounts = ['vpc1', 'vpc2']
    for account in accounts:
        session = boto3.Session(profile_name=account, region_name='us-east-1')
        ec2 = session.client('ec2', region_name='us-east-1') 
        try:
            paginator = ec2.get_paginator('describe_instances')
            pages = paginator.paginate()
            for page in pages:
                for reservation in page['Reservations']:
                    for instance in reservation['Instances']:
                        instance_id = instance['InstanceId']
                        public_ip = instance.get('PublicIpAddress', 'NO')
                        status = "Pública" if public_ip != 'N/A' else "Privada"
                        print(f"{instance_id}, {account}, {status}, {public_ip}")
        except Exception as e:
            print(f"Error al listar las instancias: {e}")

if __name__ == "__main__":
    listar_todas_las_ips()