import boto3
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError

def check_public_write(s3_client, bucket_name):
    """
    Verifica si el bucket permite escritura pública.
    Retorna 'SÍ' si es público o hay riesgo, 'NO' si está protegido.
    """
    try:
        # 1. Verificar el Policy Status (la forma más fiable de AWS)
        session = boto3.Session(profile_name='vpc1')
        s3_client = session.client('s3')
        status = s3_client.get_bucket_policy_status(Bucket=bucket_name)
        if status['PolicyStatus']['IsPublic']:
            # Si la política es pública, verificamos si permite escritura
            # Por simplicidad en este script, si la política es pública marcamos riesgo
            return "SÍ (Policy)"
    except ClientError:
        # Si no hay política, no es público por ese medio
        pass

    try:
        # 2. Verificar ACLs
        acl = s3_client.get_bucket_acl(Bucket=bucket_name)
        for grant in acl['Grants']:
            grantee = grant.get('Grantee', {})
            # URI para 'All Users' (público general)
            if grantee.get('URI') == 'http://acs.amazonaws.com/groups/global/AllUsers':
                if grant['Permission'] in ['WRITE', 'FULL_CONTROL']:
                    return "SÍ (ACL)"
    except ClientError:
        pass

    return "NO"

def list_recent_buckets():
    s3 = boto3.client('s3')
    hace_una_semana = datetime.now(timezone.utc) - timedelta(days=7)
    
    response = s3.list_buckets()
    buckets = response.get('Buckets', [])

    # Cabecera de la tabla con el nuevo campo
    header = f"{'FECHA':<10} | {'NOMBRE':<30} | {'ENTORNO':<10} | {'GRUPO':<10} | {'ESC. PÚBLICA'}"
    print(header)
    print("-" * len(header))

    for bucket in buckets:
        creacion = bucket['CreationDate']
        
        if creacion >= hace_una_semana:
            nombre = bucket['Name']
            tags_dict = {'Entorno': '-', 'Grupo': '-'}
            
            # Obtener Tags
            try:
                tagging = s3.get_bucket_tagging(Bucket=nombre)
                for tag in tagging['TagSet']:
                    if tag['Key'] in tags_dict:
                        tags_dict[tag['Key']] = tag['Value']
            except ClientError:
                pass

            # Obtener Escritura Pública
            escritura_pub = check_public_write(s3, nombre)

            # Formatear fecha
            fecha_fmt = creacion.strftime("%d/%m/%y")
            
            print(f"{fecha_fmt:<10} | {nombre:<30} | {tags_dict['Entorno']:<10} | {tags_dict['Grupo']:<10} | {escritura_pub}")

if __name__ == "__main__":
    list_recent_buckets()