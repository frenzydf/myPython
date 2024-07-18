import requests
import pandas as pd
import os

from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Process function
def process_mac(name):
  global total
  global results
  global intune_email
  global revised
  global tocreate, index
  index+=1
  for i in range(0,total):
    try:
      mac=results[i]['mac']
      if name == mac:
        print(index, name," Cuenta con reserva ",intune_email[revised])
        revised+=1
        return
    except KeyError:
      continue
  print(index, name," No cuenta con reserva")
  tocreate+=1

# Connect to API
url = "https://192.168.200.1:4443/api/v2/cmdb/system.dhcp/server/8?access_token=p3Qmmkt8cyqzrmbk841yhknp9HbGdH"
#auth_token = os.environ.get('APIKEY_02')
headers = {
#  'Authorization': 'Bearer '+ auth_token
}
# Define API response
response = requests.get(url, headers=headers, verify=False)
results = response.json()['results'][0]['reserved-address']
total=len(results)
# Open Excel File
df = pd.read_excel('intune.xlsx')
df2 = df.dropna()
intune_mac = df2['mac']
intune_email = df2['email']

# Process each mac form 
revised = 0
tocreate = 0
index = 0
print("____________________________________")
print("Registros en Intune con reserva DHCP")
print("------------------------------------")
intune_mac.apply(process_mac)
#Print Resume
print("___________________________________")
print(revised," Reservas encontradas")
print(tocreate," Reservas por crear")
print(index, "Registros de Intune revisados")

#Reservas por Eliminar
tosave=0
toerase=0
print("____________________________________")
print("Reservas DHCP vs Intune")
print("------------------------------------")
for x in range(0,total):
  exists=False
  y=0
  for inmac in intune_mac:
    try:
      mac=results[x]['mac']
      if mac==inmac:
        exists=True; y+=1
        break
      else:
        y+=1
    except KeyError:
      continue
  if exists:
    print(mac," Existe ",intune_email[y-1])
    tosave+=1
  else:
    print(mac," Borrar")
    toerase+=1
#Print Resume
print("___________________________________")
print(tosave," Reservas existentes")
print(toerase," Reservas por borrar")
print(total, "Reservas en Firewall")