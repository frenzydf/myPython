import requests
import os
import datetime
from typing import Dict
from builtins import open
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def get_secrets(idx) -> Dict[str, any]:
  print('LOCAL - Getting Secrets')
  data_dict = {
    "APIKEY": os.environ.get('APIKEY0{}'.format(idx)),
    "IP_FGT": os.environ.get('IP_FGT0{}'.format(idx)),
    "ADM_PORT": os.environ.get('ADM_PORT0{}'.format(idx)),
    "LOCATION": os.environ.get('LOCATION0{}'.format(idx))
  }
  print('LOCAL - GET Secrets OK')
  return data_dict

def connect_to_api(sec_data: Dict[str, any], idx) -> Dict[str, any]:
  try:
    print('FW - Connecting to FW API')
    endpoint = 'api/v2/monitor/system/config/backup?destination=file&scope=global'
    url = 'https://{}:{}'.format(sec_data['IP_FGT'],sec_data['ADM_PORT'])
    headers = {'Authorization': 'Bearer '+sec_data['APIKEY']}
    my_url = '{}/{}'.format(url,endpoint)
    response = requests.get(my_url, headers=headers, verify=False)
    print(f'FW - GET Backup from FGT_0{idx}_OMNI response: {response.status_code}')
    return response
  except requests.exceptions.RequestException as e:
      print(f'Error fetching data from FW API: {e}')

def save_file(secret_data: Dict[str, any], response, idx):
  now = datetime.datetime.now()
  timestamp = now.strftime("%H%M_%Y%m%d%M%S")
  filename = "FGT-0{}-KLYM_7-2_{}.conf".format(idx,timestamp)
  print(f"LOCAL - Saving Backup to FGT-0{idx}: ", filename)
  folder = secret_data['LOCATION']
  file_path = os.path.join(folder,filename)
  with open(file_path, 'wb') as f:
      f.write(response.content)
  print(f"LOCAL - Backup to FGT-0{idx}: ", filename, " OK")

def main() -> None:
  print('LOCAL - Starting Get Backup FW')
  for i in range (1, 3):
    secrets = get_secrets(i)
    response = connect_to_api(secrets, i)
    save_file(secrets, response, i)
  print('LOCAL - Ending Get Backup FW')

main()
