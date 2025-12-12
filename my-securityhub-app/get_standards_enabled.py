import boto3
import re
from botocore.exceptions import ClientError


def main(account_name):
    try:
        session = boto3.Session(profile_name=account_name)
        securityhub = session.client('securityhub', 'us-east-1')
        enabled_standards_list = [] #Lista para iterar los standards
        response = securityhub.get_enabled_standards()
        standards_enabled = response["StandardsSubscriptions"]
        print("-" * 50)
        for standard in standards_enabled:
            enabled_standards_list.append(standard['StandardsSubscriptionArn'])
        print(f"Se encontraron {len(enabled_standards_list)} estándares habilitados.")
        print("-" * 50)
    except ClientError as e:
        print(f"Error de AWS: {e}")
        print("Se requieren los permisos `securityhub:GetFindings` y región/credenciales correctas.")
    except Exception as e:
        print(f"Ocurrió un error: {e}")
    return securityhub, enabled_standards_list
    
