import requests
import json
import os
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
url = "https://192.168.1.119:4443/api/v2/cmdb/system.dhcp/server/2"

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
    }
  ]
})
headers = {
  'Authorization': 'Bearer mQdmGf55yfmzyQnqznfb7fGNps6pqq',
  'Content-Type': 'application/json'
}

response = requests.request("PUT", url, headers=headers, data=payload, verify=False)

print(response.text)
