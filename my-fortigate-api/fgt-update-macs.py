import openpyxl
import requests
import os

from builtins import open
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

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
print(results)

# Open workbook (Intune xlsx File)
workbook = openpyxl.load_workbook('intune.xlsx')
worksheet = workbook.worksheets[0]
#worksheet = workbook.get_sheet_by_name('Sheet1')
last_row = worksheet.max_row

# Read MACs from intune file
for row in range(2,last_row+1):
    cell_value = worksheet['C' + str(row)].value
    