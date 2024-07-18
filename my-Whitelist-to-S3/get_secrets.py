import json
import boto3
import logging
from typing import Dict
from botocore.exceptions import ClientError

def main() -> Dict[str, any]:
    logging.info('LOCAL - Getting Secrets')
    try:
        secret_name = "SEC_CUCKOO_SECRETS"
        region_name = "us-east-1"
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager',region_name=region_name)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        secret_data = json.loads(secret)
        logging.info('LOCAL - GET Secrets OK')
        return secret_data
    except ClientError as e:
        logging.error(f'LOCAL - Error fetching data from Secrets: {e}')
        raise e