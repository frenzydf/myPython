# Updating Indicator of Compromise to a s3 txt file 
# files should be 'src/ioc.txt' for a local file with new IoCs 
# and 'cloud/actual.txt' to download actual IoCs in S3
# anyway you can edit folder and names as you wish

import os
import boto3

# 1. Download the IoC file from AWS S3 using boto3
bucketname = os.environ.get('IOC_BUCKET')
print('Downloading AWS S3 File...')
s3 = boto3.resource('s3')
bucket = s3.Bucket(bucketname)
s3.meta.client.download_file(bucketname,'ioc-fw.txt','cloud/actual.txt')
print('ioc-fw.txt File Downloaded')

# 2. Find duplicated items between local and s3 File 
exist = False
ip_to_delete = input("Enter IP to delete from IoC List: ")
print('\nProccesing Ioc in Local File:')
with open('cloud/actual.txt', 'r') as f_ioc:
    lines = f_ioc.readlines()
with open('cloud/actual.txt', 'w') as f_ioc:
    for line in lines:
        if line.strip("\n") != ip_to_delete:
            f_ioc.write(line)
        else:
            print("Element ", ip_to_delete," deleted")
            exist = True     
f_ioc.close()

if  exist:
    # 3. Delete a old s3 ioc file
    print('\nDeleting old ioc-fw.txt from s3 bucket...')
    s3.Object(bucketname,'ioc-fw.txt').delete()
    print('ioc-fw.txt file has been deleted')
    # 4. Uploading the new s3 ioc file
    print('\nUploading a new ioc-txt to s3 bucket...')
    s3.meta.client.upload_file('cloud/actual.txt',bucketname,'ioc-fw.txt')
    print('ioc-fw.txt file has been updated')
else:
    print('\nNo files has been updated')
