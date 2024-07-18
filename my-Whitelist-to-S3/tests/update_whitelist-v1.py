import requests
import datetime
import ipaddress
import json
import boto3
import os

def read_api():
    url = os.environ.get('ELK_URL')
    auth_token = os.environ.get('ELK_APIKEY')
    headers = {
        'Content-Type': 'application/json', 
        'Authorization': 'Apikey '+auth_token
    }
    with open ("query.json","r") as f: json_data = json.load(f)
    payload = json.dumps(json_data)
    response = requests.request("GET", url, headers=headers, data=payload)
    print("API Response: ", response.status_code)
    if response.status_code == 200:
        return response.json()['aggregations']['ips']['buckets']
    else:
        return False

def update_json_timestamps(json_file, new_gte, new_lte):
    with open(json_file, "r") as f:
        json_data = json.load(f)
    json_data["query"]["bool"]["filter"][0]["range"]["@timestamp"]["gte"] = new_gte
    json_data["query"]["bool"]["filter"][0]["range"]["@timestamp"]["lte"] = new_lte
    with open(json_file, "w") as f:
        json.dump(json_data, f)

def contains_caracter(string):
    return ":" in string

def is_local_ip(string):
    if string.startswith(("0.")):
        return True
    else:
        return False

def write_related_ips(related_ip):
    count=1
    with open("IP_WhiteList.txt",'w') as f:
        for ip in related_ip:
            try:
                ipv6 = contains_caracter(ip['key'])
                ip_local = is_local_ip(ip['key'])
                if not ipv6 and not ip_local:
                    ip_address_obj = ipaddress.IPv4Address(ip['key'])
                    if ip_address_obj is not None: 
                        ip_address = ip['key']
                        f.write(ip_address+'\n')
                        count+=1
            except KeyError:
                continue
        print("IP Count: ", count)

def upload_file_s3():
    bucketname = os.environ.get('SEC_BUCKET')
    print("Updating S3 Bucket")
    s3 = boto3.resource('s3')
    s3.Object(bucketname,'Whitelist/IP_WhiteList.txt').delete()
    s3.meta.client.upload_file('IP_WhiteList.txt',bucketname,'Whitelist/IP_WhiteList.txt')

def main():
    now = datetime.datetime.now()
    now_range = now + datetime.timedelta(days = -5)
    gte_timestamp = now_range.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    lte_timestamp = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    print("Timestamp:  ", lte_timestamp)
    update_json_timestamps("query.json", gte_timestamp, lte_timestamp)

if __name__ == '__main__':
    main()
    results = read_api()
    print("Len response: ", len(results))
    if results:
        write_related_ips(results)
        upload_file_s3()
    else:
      print("Error de conexión")