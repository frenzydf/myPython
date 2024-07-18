# Updating Indicator of Compromise to a s3 txt file 
# files should be 'src/ioc.txt' for a local file with new IoCs 
# and 'cloud/actual.txt' to download actual IoCs in S3
# anyway you can edit folder and names as you wish

import os
import openpyxl
import boto3
from termcolor import colored

# Function for write new lines 

def WriteFile(valor):
    f = open('cloud/actual.txt', "a")
    f.write('\n')
    f.write(valor)
    print("{}\t Added to a IoC".format(
        colored(valor, 'green')
    ))
    f.close()

# Function for search ioc in a whitelist
def find_addr(address):
    row=1
    for row in range(1,last_row+1):
        cell_value = worksheet['A' + str(row)].value
        if address == cell_value:
            timedate = worksheet['B' + str(row)].value
            elastic_ip_id = worksheet['C' + str(row)].value
            print(address, "Found in AWS", timedate, " ",elastic_ip_id)
            return True
    return False

# 1. Download the IoC file from AWS S3 using boto3
bucketname = os.environ.get('IOC_BUCKET')
print('Downloading AWS S3 File...')
s3 = boto3.resource('s3')
bucket = s3.Bucket(bucketname)
s3.meta.client.download_file(bucketname,'ioc-fw.txt','cloud/actual.txt')
print('ioc-fw.txt File Downloaded')

# 2. Whitelist IPs on a local file
#Open File
workbook = openpyxl.load_workbook('whitelist.xlsx')
worksheet = workbook.worksheets[0]
#worksheet = workbook.get_sheet_by_name('Sheet1')
last_row = worksheet.max_row

# 4. Find duplicated items between local and s3 File 
#    Validate that IoC are not in a AWS whitelist
ever_exist = False
white_list = False
print('\nProccesing Ioc in Local File:')
with open('src/ioc.txt', 'r') as f_ioc:
    for l_ioc, line_ioc in enumerate(f_ioc):
        my_ioc = line_ioc.strip()
        exist = False
        white_list = find_addr(my_ioc)
        if not white_list: # if not in whitelist then 
            with open('cloud/actual.txt', 'r') as f_actual:
                for l_actual, line_actual in enumerate(f_actual):
                    my_actual = line_actual.strip()
                    if my_ioc == my_actual:
                        print("{}\t already exist".format(
                            colored(my_ioc, 'red')
                        ))
                        exist = True
                        break
                if exist == False: 
                    WriteFile(my_ioc)
                    ever_exist = True
    f_actual.close()
f_ioc.close()
# final steps
if  ever_exist:
# 5. Delete a old s3 ioc file
    if not white_list:
        print('No AWS IP Whitelist was found, Updating IoCs...')
    print('\nDeleting old ioc-fw.txt from s3 bucket...')
    s3.Object(bucketname,'ioc-fw.txt').delete()
    print('ioc-fw.txt file has been deleted')
# 6. Uploading the new s3 ioc file
    print('\nUploading a new ioc-txt to s3 bucket...')
    s3.meta.client.upload_file('cloud/actual.txt',bucketname,'ioc-fw.txt')
    print('ioc-fw.txt file has been updated')
else:
    print('\nNo files has been updated')
