import requests
import logging
import json
import os
from typing import Set, List, Dict
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def connect_to_api() -> Dict[str, any]:   
    ip_address = os.environ.get('IP_FGT02')
    admin_port = os.environ.get('ADM_PORT02')
    auth_token = os.environ.get('APIKEY02')
    url = 'https://{}:{}'.format(ip_address,admin_port)
    headers = {'Authorization': 'Bearer '+auth_token}
    return url, headers

def get_firewall_list() -> Set[str]:
    try:
        endpoint = 'api/v2/cmdb/firewall/address'
        url, headers = connect_to_api()
        my_url = '{}/{}'.format(url,endpoint)
        logging.info("FW - Reading Firewall API Get Address List")
        response = requests.get(my_url, headers=headers, verify=False)
        response.raise_for_status()
        logging.info(f'FW - API Response Code: {response.status_code}')
        results = response.json()["results"]
        logging.info(f'FW - API Response LEN: {len(results)}')
        set1 = set([
            r['name'].replace("IPW_", "", 1)
            for r in results
            if r['name'].startswith("IPW_")
            ])
        logging.info(f'FW - Found {len(set1)} IPW_ Adress Objects')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error fetching data from FW API: {e}')
    return set1

def get_whitelist_file() -> Set[str]:
    logging.info('LOCAL - Reading WhiteList.txt file')
    with open("IP_WhiteList.txt", "r") as f:
        ip_white_list = [line.strip() for line in f.readlines()]
    set2 = set(ip_white_list)
    logging.info(f'LOCAL - Found {len(ip_white_list)} in WhiteList.txt registers')
    return set2

def fw_del_ip(to_delete_list: List[str]) -> None:
    logging.info(f'FW - DEL {len(to_delete_list)} Address list in progress')
    count = 0
    skiped = 0
    for ip in to_delete_list:
        if ip in ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]:
            skiped +=1
        else:
            endpoint = 'api/v2/cmdb/firewall/address/IPW_{}'.format(ip)
            url, headers = connect_to_api()
            my_url = '{}/{}'.format(url,endpoint)
            print(my_url)
            response = requests.delete(my_url, headers=headers, verify=False)
            count +=1
            print(response)
    logging.info(f'FW - DEL {count} Address deleted and {skiped} skiped')

def fw_post_ip(addr_list: List[str]) -> None:
    logging.info(f'FW - POST {len(addr_list)} Address list in progress')
    ip_list_to_send = [
        {
            "name": "IPW_"+ip,
            "subnet": ip+"/32",
            "comment": "created api whitelist"
        }
        for ip in addr_list
    ]
    endpoint = 'api/v2/cmdb/firewall/address'
    url, headers = connect_to_api()
    my_url = '{}/{}'.format(url,endpoint)
    response = requests.post(my_url, headers=headers, data=json.dumps(ip_list_to_send), verify=False)
    logging.info(f'FW - POST FW response code: {response.status_code}')
    logging.info(f'FW - IP address created count: {len(ip_list_to_send)}')

def fw_put_grp(addr_list: List[str]) -> None:
    try:
        url, headers = connect_to_api()
        logging.info(f'FW - PUT {len(addr_list)} Address Group in progress')
        addr_list_prefix = [f"IPW_{num}" for num in addr_list]
        ip_list_to_send = [addr_list_prefix[i:i+599] for i in range(0, len(addr_list_prefix), 599) if i < 2399]
        if len(ip_list_to_send) < 2399:
            logging.error('Exeded capacity 2400')
        payloads = [json.dumps({"member": [{"name": num} for num in sublist]}) for sublist in ip_list_to_send]
        endpoints = ['{}/api/v2/cmdb/firewall/addrgrp/FW_Whitelist_{}'.format(url, i) for i in range(1, 5)]
        for i in range(4):
            response = requests.put(endpoints[i], headers=headers, data=payloads[i], verify=False)
            logging.info(f'FW - PUT code Group FW_whitelist_{i+1}: {response.status_code}')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error fetching data from API: {e}')

def fw_purge_grp() -> None:
    try:
        url, headers = connect_to_api()
        logging.info('FW - Execute Purge WhiteList Group')
        ip_addresses = ["1.1.1.1", "2.2.2.2", "3.3.3.3", "4.4.4.4"]
        payloads = [json.dumps({"member": [{"name": f"IPW_{ip_address}"}]}) for ip_address in ip_addresses]
        endpoints = ['{}/api/v2/cmdb/firewall/addrgrp/FW_Whitelist_{}'.format(url, i) for i in range(1, 5)]
        for i in range(4):
            response = requests.put(endpoints[i], headers=headers, data=payloads[i], verify=False)
            logging.info(f'FW - PUT code Purge FW_Whitelist_{i+1} response: {response.status_code}')
    except requests.exceptions.RequestException as e:
        logging.error(f'Error fetching data from API: {e}')

def delete_list(addr_list: Set[str], new_ip_list: Set[str]) -> None:
    to_delete_list = list(addr_list - new_ip_list)
    if to_delete_list:
        fw_del_ip(to_delete_list)
    else:
        logging.info("LOCAL - No addresses to delete []")

def create_list(addr_list: Set[str], new_ip_list: Set[str]) -> None:
    to_create_list = list(new_ip_list - addr_list)
    if to_create_list:
        fw_post_ip(to_create_list)
    else:
        logging.info("LOCAL - No addresses to create []")

def log_definition():
    logging.basicConfig(filename='api_logs.log', level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

def main() -> None:
    log_definition()
    fw_purge_grp()
    firewall_ips = get_firewall_list()
    whitelist_ips = get_whitelist_file()
    delete_list(firewall_ips, whitelist_ips)
    create_list(firewall_ips, whitelist_ips)
    fw_put_grp(list(whitelist_ips))
    logging.info("LOCAL - END IP WhiteList")