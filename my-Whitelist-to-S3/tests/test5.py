import boto3
import json
from typing import Dict
from botocore.exceptions import ClientError


def get_secrets() -> Dict[str, any]:
    print('LOCAL - Getting Secrets')
    try:
        secret_name = "SEC_CUCKOO_SECRETS"
        region_name = "us-east-1"
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager',region_name=region_name)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        secret_data = json.loads(secret)
        keys = ["ELK_URL", "ELK_APIKEY", "SEC_BUCKET"]
        data_dict = {key: secret_data[f"{key}"] for key in keys}
        print('LOCAL - GET Secrets OK')
        return data_dict
    except ClientError as e:
        print(f'LOCAL - Error fetching data from Secrets: {e}')
        raise e

def main() -> None:
    secrets = get_secrets()
    elk_url = secrets['ELK_URL']
    print(elk_url)

if __name__ == '__main__':
    main()
