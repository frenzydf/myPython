import requests
import datetime
import ipaddress
import json
import boto3
import os
import logging
from typing import Dict


def read_api() -> Dict[str, any]:
    url = os.environ.get('ELK_URL')
    logging.info('ELK - Connecting to ELK API')
    auth_token = os.environ.get('ELK_APIKEY')
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
    json_data["query"]["bool"]["filter"][0]["range"]["@timestamp"]["gte"] = new_gte
    json_data["query"]["bool"]["filter"][0]["range"]["@timestamp"]["lte"] = new_lte
    with open(json_file, "w") as f:
        json.dump(json_data, f)

def write_related_ips(related_ip: str) -> None:
    count=1
    count_ip=0
    logging.info('LOCAL - Opening WhiteList.txt file')
    with open("IP_WhiteList.txt",'w') as f:
        for ip in related_ip:
            try:
                ip_address_obj = ipaddress.IPv4Address(ip['key'])
                ip_address = ip['key']
                if not ip_address_obj.is_private:
                    if count == 1:
                        f.write(ip_address)
                        count+=1
                    else:
                        f.write('\n'+ip_address)
                        count+=1
                else:
                    count_ip+=1
            except KeyError as e:
                logging.error(f'Error: {e}')
        logging.info(f'LOCAL - IP Count Filtered: {count_ip-1}')
        logging.info(f'LOCAL - IP Count added to WhiteList.txt: {count-1}')

def upload_file_s3() -> None:
    bucketname = os.environ.get('SEC_BUCKET')
    logging.info("S3 - Updating Bucket whitelist")
    s3 = boto3.resource('s3')
    s3.Object(bucketname,'Whitelist/IP_WhiteList.txt').delete()
    s3.meta.client.upload_file('IP_WhiteList.txt',bucketname,'Whitelist/IP_WhiteList.txt')
    logging.info("S3 - Updated Bucket whitelist complete")

def main_time() -> None:
    now = datetime.datetime.now() + datetime.timedelta(hours=5)
    now_range = now + datetime.timedelta(days = -5)
    gte_timestamp = now_range.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    lte_timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    update_json_timestamps("query.json", gte_timestamp, lte_timestamp)

def log_definition():
    logging.basicConfig(filename='api_logs.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    log_definition()
    logging.info("LOCAL - Starting IP WhiteList")
    main_time()
    results = read_api()
    if not results:
        logging.error("Connection Error API ELK")
        return
    logging.info(f'ELK - WhiteList IP received from ELK: {len(results)}')
    write_related_ips(results)
    upload_file_s3()
