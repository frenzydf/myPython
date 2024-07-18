import requests
import os
#import json
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

url = "https://172.19.0.135:4443/api/v2/cmdb/vpn.ipsec/phase1-interface"
auth_token = os.environ.get('APIKEY01')
headers = {
  'Authorization': 'Bearer '+auth_token
}

response = requests.request("GET", url, headers=headers, verify=False)
results = response.json()['results']
total=len(results)

for i in range(0,total):
  try:
    name=results[i]['name']
    interface=results[i]['interface']
    proposal=results[i]['proposal']
    remote_gw=results[i]['remote-gw']
    remotegw_ddns=results[i]['remotegw-ddns']
    print(f"{name},{interface},{proposal},{remote_gw},{remotegw_ddns}")
  except KeyError:
    continue

print('Total Tunnels: '+str(total))