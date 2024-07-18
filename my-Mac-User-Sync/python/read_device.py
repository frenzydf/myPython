import requests
import os
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def read_api():
  ip_address = os.environ.get('IP_FGT03')
  admin_port = os.environ.get('ADM_PORT03')
  endpoint = 'api/v2/monitor/user/device/query'
  auth_token = os.environ.get('APIKEY03')

  url = 'https://{}:{}/{}'.format(ip_address,admin_port,endpoint)
  headers = {
    'Authorization': 'Bearer '+auth_token
  }

  response = requests.request("GET", url, headers=headers, verify=False)
  results = response.json()['results']
  total=len(results)

  reserved_hostnames = []
  for i in range(0,total):
    try:
      mac=results[i]['mac']
      ipaddr=results[i]['ipv4_address']
      interface=results[i]['detected_interface']
      hostname=results[i]['hostname']
      last_seen=results[i]['last_seen']
      is_online=results[i]['is_online']
      if interface == "onCorp_v309":
        reserved_hostname = {
          "macaddr": mac,
          "ipaddr": ipaddr,
          "hostname": hostname,
          "lastseen": last_seen
        }
        if reserved_hostname not in reserved_hostnames:
          reserved_hostnames.append(reserved_hostname)
          print(f"{mac}   {ipaddr.ljust(18)} {interface.ljust(18)} {hostname.ljust(20)} {last_seen} {is_online}")
    except KeyError:
      continue
  return(reserved_hostnames)