import requests
import os
#import json
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

url = "https://172.19.0.135:4443/api/v2/cmdb/router/static"
auth_token = os.environ.get('APIKEY01')
headers = {
  'Authorization': 'Bearer '+auth_token
}

response = requests.request("GET", url, headers=headers, verify=False)
results = response.json()['results']
total=len(results)

for i in range(0,total):
  try:
    destination=results[i]['dst']
    gateway=results[i]['gateway']
    device=results[i]['device']
    status=results[i]['status']
    print(f"{destination},{gateway},{device},{status}")
  except KeyError:
    continue

print('Total Routes: '+str(total))