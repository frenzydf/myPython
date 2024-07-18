import requests
import boto3
import json
import datetime
import ipaddress
import logging
from typing import Dict
from botocore.exceptions import ClientError

def get_secrets(secret_data: Dict[str, any]) -> Dict[str, any]:
    logging.info('LOCAL - Reading ELK Secrets')
    keys = ["ELK_URL", "ELK_APIKEY", "SEC_BUCKET"]
    data_dict = {key: secret_data[f"{key}"] for key in keys}
    logging.info('LOCAL - ELK Secrets OK')
    return data_dict


def read_api(secret_data: Dict[str, any]) -> Dict[str, any]:
    url = secret_data['ELK_URL']
    logging.info('ELK - Connecting to ELK API')
    auth_token = secret_data['ELK_APIKEY']
    headers = {
        'Content-Type': 'application/json', 
        'Authorization': 'Apikey '+auth_token
    }
    with open ("query.json","r") as f: json_data = json.load(f)
    payload = json.dumps(json_data)
    try:
        response = requests.request("GET", url, headers=headers, data=payload)
        logging.info(f'ELK - Connected to ELK API Response code: {response.status_code}')
        if response.status_code == 200:
            return response.json()['aggregations']['ips']['buckets']
        else:
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f'ELK - Error fetching data from API: {e}')

def update_json_timestamps(json_file: Dict[str, any], new_gte: str, new_lte: str) -> None:
    with open(json_file, "r") as f:
        json_data = json.load(f)
    json_data["query"]["bool"]["filter"][1]["range"]["@timestamp"]["gte"] = new_gte
    json_data["query"]["bool"]["filter"][1]["range"]["@timestamp"]["lte"] = new_lte
    with open(json_file, "w") as f:
        json.dump(json_data, f)

def write_related_ips(related_ip: str) -> None:
    count_ip_filtered=0
    count_ip=0
    logging.info('LOCAL - Opening WhiteList.txt file')
    with open("IP_WhiteList.txt",'w') as f:
        for ip in related_ip:
            try:
                ip_address_obj = ipaddress.IPv4Address(ip['key'])
                ip_address = ip['key']
                if not ip_address_obj.is_private:
                    if count_ip == 0:
                        f.write(ip_address)
                        count_ip+=1
                    else:
                        f.write('\n'+ip_address)
                        count_ip+=1
                else:
                    count_ip_filtered+=1
            except KeyError as e:
                logging.error(f'Error: {e}')
        logging.info(f'LOCAL - IP Count Filtered: {count_ip_filtered}')
        logging.info(f'LOCAL - IP Count added to WhiteList.txt: {count_ip}')

def upload_file_s3(secret_data: Dict[str, any]) -> None:
    bucketname = secret_data['SEC_BUCKET']
    logging.info("S3 - Updating Bucket whitelist")
    s3 = boto3.resource('s3')
    s3.Object(bucketname,'Whitelist/IP_WhiteList.txt').delete()
    s3.meta.client.upload_file('IP_WhiteList.txt',bucketname,'Whitelist/IP_WhiteList.txt')
    logging.info("S3 - Updated Bucket whitelist complete")

def main_time() -> None:
    now = datetime.datetime.now() + datetime.timedelta(hours=5)
    now_range = now + datetime.timedelta(days = -7)
    gte_timestamp = now_range.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    lte_timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    update_json_timestamps("query.json", gte_timestamp, lte_timestamp)

def log_definition():
    logging.basicConfig(filename='api_logs.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

def main(secrets: Dict[str, any]):
    log_definition()
    logging.info("LOCAL - Starting IP WhiteList")
    main_time()
    my_secrets = get_secrets(secrets)
    results = read_api(my_secrets)
    if not results:
        logging.error("Connection Error API ELK")
        return
    logging.info(f'ELK - WhiteList IP received from ELK: {len(results)}')
    write_related_ips(results)
    upload_file_s3(my_secrets)
