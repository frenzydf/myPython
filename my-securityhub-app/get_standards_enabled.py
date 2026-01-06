import boto3
import logging
from botocore.exceptions import ClientError


def main(securityhub_client, account_name: str) -> list:
    enabled_standards_list = []
    try:
        response = securityhub_client.get_enabled_standards()
        standards_enabled = response["StandardsSubscriptions"]
        for standard in standards_enabled:
            enabled_standards_list.append(standard['StandardsSubscriptionArn'])
        logging.info(f"Se encontraron {len(enabled_standards_list)} estándares habilitados en la cuenta {account_name}.")
        
    except ClientError as e:
        logging.error(f"Error de AWS (ClientError) al consultar estándares habilitados en la cuenta {account_name}: {e}")
        raise e

    except Exception as e:
        logging.error(f"Ocurrió un error: {e}")
        raise e
    
    return enabled_standards_list
    
