import mysql.connector
import requests
import json
import os
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def read_data_from_db():
    connection = mysql.connector.connect(user = 'root', password = 'root', host='localhost', port ="3306", database='db')
    cursor = connection.cursor()
    sql_query = "SELECT ip, mac FROM dhcp_list"
    cursor.execute(sql_query)
    data = cursor.fetchall()
    return data

def send_data_to_api(results):
    ip_address = os.environ.get('IP_FGT03')
    admin_port = os.environ.get('ADM_PORT03')
    endpoint = 'api/v2/cmdb/system.dhcp/server/13'
    auth_token = os.environ.get('APIKEY03')
    url = 'https://{}:{}/{}'.format(ip_address,admin_port,endpoint)
    headers = {'Authorization': 'Bearer '+auth_token}
    
    reserved_addresses = []
    id=0
    for result in results:
        ip, mac = result
        reserved_address = {"id": id, "type": "mac", "ip": ip, "mac": mac, "action": "reserved"}
        reserved_addresses.append(reserved_address)
        id+=1
    payload = {"id": 13,"reserved-address": reserved_addresses}
    response = requests.request("PUT", url, headers=headers, data=json.dumps(payload), verify=False)
    return response