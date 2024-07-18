import requests

url = "https://192.168.200.1:4443/api/v2/cmdb/system.dhcp/server/7?vdom=root"

payload = "[{\r\n    \"id\": 7,\r\n    \"reserved-address\": [\r\n        {\r\n        \"id\": 0,\r\n        \"type\": \"mac\",\r\n        \"action\": \"reserved\",\r\n        \"ip\": \"192.168.100.25\",\r\n        \"mac\": \"9c:b6:54:53:92:be\"\r\n        }\r\n    ]\r\n}]\r\n"
headers = {
  'Authorization': 'Bearer js3dN8q8wGhHgh56tp3c58t8pxnw5Q',
  'Content-Type': 'text/plain'
}

response = requests.request("PUT", url, headers=headers, data=payload)

print(response.text)
