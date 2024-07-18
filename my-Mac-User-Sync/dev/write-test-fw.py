import requests
import json
import os
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ip_address = os.environ.get('IP_FGT_TEST')
admin_port = os.environ.get('ADM_PORT_TEST')
endpoint = 'api/v2/cmdb/system.dhcp/server/2'
auth_token = os.environ.get('APIKEY_TEST')

url = 'https://{}:{}/{}'.format(ip_address,admin_port,endpoint)
headers = {
  'Authorization': 'Bearer '+auth_token,
  'Content-Type': 'application/json'
}

reserved_addresses = []

payload = json.dumps({
  "id": 2,
  "reserved-address": [
    {
      "id": 1,
      "type": "mac",
      "ip": "192.168.1.221",
      "mac": "11:22:33:44:55:21",
      "action": "reserved"
    },
    {
      "id": 2,
      "type": "mac",
      "ip": "192.168.1.222",
      "mac": "11:22:33:44:55:22",
      "action": "reserved"
    },
    {
      "id": 3,
      "type": "mac",
      "ip": "192.168.1.223",
      "mac": "11:22:33:44:55:23",
      "action": "reserved"
    },
    {
      "id": 4,
      "type": "mac",
      "ip": "192.168.1.224",
      "mac": "11:22:33:44:55:24",
      "action": "reserved"
    },
    {
      "id": 5,
      "type": "mac",
      "ip": "192.168.1.225",
      "mac": "11:22:33:44:55:25",
      "action": "reserved"
    },
    {
      "id": 6,
      "type": "mac",
      "ip": "192.168.1.226",
      "mac": "11:22:33:44:55:26",
      "action": "reserved"
    }
  ]
})

#print(payload)
response = requests.request("PUT", url, headers=headers, data=payload, verify=False)
print(response.text)