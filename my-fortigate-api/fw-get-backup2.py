import os
import requests
import boto3
import json
import datetime
import logging
from typing import Dict
from botocore.exceptions import ClientError
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def get_secrets() -> Dict[str, any]:
    logging.info('LOCAL - Getting Secrets')
    try:
        secret_name = "SEC_CUCKOO_SECRETS"
        region_name = "us-east-1"
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager',region_name=region_name)
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret = get_secret_value_response['SecretString']
        secret_data = json.loads(secret)
        keys = ["IP_FGT", "ADM_PORT", "APIKEY", "LOCATION"]
        data_dict = {key: [secret_data[f"{key}0{idx}"] for idx in range(1, 3)] for key in keys}
        logging.info('LOCAL - GET Secrets OK')
        return data_dict
    except ClientError as e:
        logging.error(f'LOCAL - Error fetching data from Secrets: {e}')
        raise e

def connect_to_api(sec_data: Dict[str, any], idx) -> Dict[str, any]:
    try:
        logging.info('FW - Connecting to FW API')
        endpoint = 'api/v2/monitor/system/config/backup?destination=file&scope=global'
        url = 'https://{}:{}'.format(sec_data['IP_FGT'][idx],sec_data['ADM_PORT'][idx])
        headers = {'Authorization': 'Bearer '+sec_data['APIKEY'][idx]}
        my_url = '{}/{}'.format(url,endpoint)
        response = requests.get(my_url, headers=headers, verify=False)
        logging.info(f'FW - GET Backup from FGT_0{idx+1}_OMNI response: {response.status_code}')
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f'Error fetching data from FW API: {e}')

def save_file(secret_data: Dict[str, any], response: Dict[str, any], idx):
    now = datetime.datetime.now()
    timestamp = now.strftime("%H%M_%Y%m%d%M%S")
    filename = "FGT-0{}-KLYM_7-2_{}.conf".format(idx+1,timestamp)
    logging.info(f'LOCAL - Saving Backup to FGT-0{idx+1}: {filename}')
    folder = secret_data['LOCATION'][idx]
    file_path = os.path.join(folder,filename)
    with open(file_path, 'wb') as f:
        f.write(response.content)
    logging.info(f'LOCAL - Backup to FGT-0{idx+1}: {filename}  OK')

def main() -> None:
    logging.info('LOCAL - Starting Get Backup FW')
    secrets = get_secrets()
    for i in range (0, 2):
        response = connect_to_api(secrets, i)
        save_file(secrets, response, i)
    logging.info('LOCAL - Ending Get Backup FW')

def log_define() -> None:
    logging.basicConfig(filename='api_logs.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    log_define()
    main()
