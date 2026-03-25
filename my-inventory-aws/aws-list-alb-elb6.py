import boto3

def list_lb_deletion_protection():
    # Inicializar el cliente de ELBv2
    session = boto3.Session(profile_name='securityhub')
    client = session.client('elbv2')
    
    # Imprimir cabecera del CSV
    print("Name,Type,Scheme,DeletionProtection")

    try:
        # Paginación para manejar cuentas con muchos Load Balancers
        paginator = client.get_paginator('describe_load_balancers')
        
        for page in paginator.paginate():
            for lb in page['LoadBalancers']:
                lb_arn = lb['LoadBalancerArn']
                lb_name = lb['LoadBalancerName']
                lb_type = lb['Type']
                lb_scheme = lb['Scheme']
                
                # Obtener los atributos de cada Load Balancer
                attrs = client.describe_load_balancer_attributes(LoadBalancerArn=lb_arn)
                
                # Buscar el valor de deletion_protection.enabled
                protection = "false"
                for attr in attrs['Attributes']:
                    if attr['Key'] == 'deletion_protection.enabled':
                        protection = attr['Value']
                        break
                
                # Imprimir la línea en formato CSV
                if protection == "false":
                    print(f"{lb_name},{lb_type},{lb_scheme},{protection}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_lb_deletion_protection()