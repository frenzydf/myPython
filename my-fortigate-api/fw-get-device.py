import requests
import os
#import json
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

url = "https://192.168.200.1:4443/api/v2/monitor/user/device/query"
auth_token = os.environ.get('APIKEY02')
headers = {
  'Authorization': 'Bearer '+auth_token
}

response = requests.request("GET", url, headers=headers, verify=False)
results = response.json()['results']
total=len(results)

for i in range(0,total):
  try:
    mac=results[i]['mac']
    addr=results[i]['ipv4_address']
    interface=results[i]['detected_interface']
    osname=results[i]['os_name']
    last_seen=results[i]['last_seen']
    print(f"{mac}   {addr.ljust(18)} {interface.ljust(18)} {osname.ljust(10)} {last_seen} ")
  except KeyError:
    continue

print('Total Devices: '+str(total))