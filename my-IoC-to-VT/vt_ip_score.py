import requests
import time
import os

API_KEY = os.environ.get('API_KEY_VT')  # ← tu API Key
INPUT_FILE = 'ips.txt'
OUTPUT_FILE = 'resultados.txt'
VT_URL = 'https://www.virustotal.com/api/v3/ip_addresses/'

HEADERS = {
    'x-apikey': API_KEY
}

def get_ip_score(ip):
    response = requests.get(VT_URL + ip, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        score = data['data']['attributes']['last_analysis_stats']['malicious']
        return score
    else:
        print(f"[!] Error al consultar {ip} - Código {response.status_code}")
        return "Error"

def main():
    with open(INPUT_FILE, 'r') as f:
        ips = [line.strip() for line in f if line.strip()]
    
    with open(OUTPUT_FILE, 'w') as out:
        out.write("IP,Score\n")
        for ip in ips:
            score = get_ip_score(ip)
            out.write(f"{ip},{score}\n")
            print(f"[+] {ip} → Score: {score}")
            time.sleep(15)  # Para evitar límite de rate (4 peticiones/min en plan gratuito)

if __name__ == "__main__":
    main()
