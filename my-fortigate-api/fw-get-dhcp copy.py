import requests
import pandas as pd
import os

from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Process function
def process_mac(name):
  global total
  global results
  
  for i in range(0,total):
    try:
      mac=results[i]['mac']
      if name == mac:
        print(name," Cuenta con reserva")
        return
    except KeyError:
      continue
  print(name," No cuenta con reserva")

# Connect to API
url = "https://192.168.200.1:4443/api/v2/cmdb/system.dhcp/server/8"
auth_token = os.environ.get('APIKEY_02')
headers = {
  'Authorization': 'Bearer '+ auth_token
}
# Define API response
response = requests.get(url, headers=headers, verify=False)
results = response.json()['results'][0]['reserved-address']
total=len(results)
# Open Excel File
df = pd.read_excel('intune.xlsx')
df2 = df.dropna()
intune_mac = df2['mac']
# Process each mac form 
intune_mac.apply(process_mac)
