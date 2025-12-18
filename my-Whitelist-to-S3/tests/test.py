import requests
import ipaddress

def api_conection():
   url = "https://"
   headers = {
    "Authorization": "ApiKey ",
    "Content-Type": "application/json"
    }
   data = '''
   {"query": {"bool": {"must": {"match_all": {}}, "filter": [{"range": {"@timestamp": {"gte": "2023-07-08T11:15:10.000Z", "lte": "2023-07-18T11:15:10.000Z"}}}]}}, "size": 0, "aggs": {"ips": {"terms": {"field": "related.ip", "size": 50000}}, "1": {"cardinality": {"field": "related.ip"}}}}
   '''
   print("Connecting API...")
   response = requests.get(url, headers=headers, data=data)
   return response
def contains_caracter(string):
   return ":" in string
def main(response):
  if response.status_code == 200:
      json_response = response.json()
      related_ip = json_response['aggregations']['ips']['buckets']
      print("Datos: ",len(related_ip),"\nType: ",type(related_ip))
      count = 0
      ip_list = []
      for ip in related_ip:
          ipv6 = contains_caracter(ip['key'])
          if not ipv6:
            ip_address_obj = ipaddress.IPv4Address(ip['key'])
            if ip_address_obj is not None:
              count+=1
              ip_list.append(ip['key'])
      return ip_list
  else:
      print(f"Error: {response.status_code} - {response.text}")

if __name__ == '__main__':
  response = api_conection()
  list_of_ip = main(response)
  new_list_of_ip = [item for item in list_of_ip if item not in list_of_ip[:item]]
  print (new_list_of_ip)

