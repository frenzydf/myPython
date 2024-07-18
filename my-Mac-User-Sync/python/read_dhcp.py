import requests
import os
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def read_api():
    ip_address = os.environ.get('IP_FGT03')
    admin_port = os.environ.get('ADM_PORT03')
    endpoint = 'api/v2/cmdb/system.dhcp/server/13'
    auth_token = os.environ.get('APIKEY03')

    url = 'https://{}:{}/{}'.format(ip_address,admin_port,endpoint)
    headers = {
    'Authorization': 'Bearer '+auth_token
    }

    response = requests.request("GET", url, headers=headers, verify=False)
    results = response.json()['results'][0]['reserved-address']
    total=len(results)

    reserved_dhcp = []
    for i in range(0,total):
        try:
            mac=results[i]['mac']
            ip=results[i]['ip']
            print(mac, ip)
        except KeyError:
            continue
    return(reserved_dhcp)