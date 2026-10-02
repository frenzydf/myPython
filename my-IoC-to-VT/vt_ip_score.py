#!/usr/bin/env python3

import requests
import time
import os
from datetime import datetime

# ==========================
# CONFIGURACION
# ==========================
VT_API_KEY = os.getenv("VT_APIKEY")
ABUSEIPDB_API_KEY = os.getenv("ABUSE_APIKEY")

IPS_FILE = "ips.txt"
OUTPUT_FILE = "resultados-ip.txt"
VT_FREE_SLEEP_SECONDS = 15

# ==========================
# VIRUSTOTAL
# ==========================
def consultar_virustotal(ip):
    try:
        url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"

        headers = {
            "x-apikey": VT_API_KEY
        }

        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"[VT] Error consultando {ip}: {response.status_code}")
            return {
                "malicious": 0,
                "suspicious": 0
            }

        data = response.json()

        stats = data["data"]["attributes"]["last_analysis_stats"]

        return {
            "malicious": stats.get("malicious", 0),
            "suspicious": stats.get("suspicious", 0)
        }

    except Exception as e:
        print(f"[VT] Excepcion para {ip}: {e}")
        return {
            "malicious": 0,
            "suspicious": 0
        }


# ==========================
# ABUSEIPDB
# ==========================
def consultar_abuseipdb(ip):
    try:
        url = "https://api.abuseipdb.com/api/v2/check"

        headers = {
            "Accept": "application/json",
            "Key": ABUSEIPDB_API_KEY
        }

        params = {
            "ipAddress": ip,
            "maxAgeInDays": 90,
            "verbose": True
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            print(f"[ABUSEIPDB] Error consultando {ip}: {response.status_code}")
            return {
                "abuse_score": 0,
                "total_reports": 0
            }

        data = response.json()["data"]

        return {
            "abuse_score": data.get("abuseConfidenceScore", 0),
            "total_reports": data.get("totalReports", 0)
        }

    except Exception as e:
        print(f"[ABUSEIPDB] Excepcion para {ip}: {e}")
        return {
            "abuse_score": 0,
            "total_reports": 0
        }


# ==========================
# MAIN
# ==========================
def main():

    with open(IPS_FILE, "r") as f:
        ips = [line.strip() for line in f if line.strip()]

    resultados_positivos = []

    print(f"\nProcesando {len(ips)} IP(s)\n")

    for ip in ips:

        # Primero consultar AbuseIPDB. Si el score es 0, entonces se hace
        # una segunda verificación con VirusTotal para evitar usar la API
        # gratuita de VT en todas las IPs.
        abuse = consultar_abuseipdb(ip)
        vt = {"malicious": 0, "suspicious": 0}

        if abuse["abuse_score"] == 0:
            print(f"[INFO] AbuseIPDB score 0 para {ip}; consultando VirusTotal como segunda opinión...")
            time.sleep(VT_FREE_SLEEP_SECONDS)  # espera requerida por la cuenta gratuita de VT
            vt = consultar_virustotal(ip)

        # Score combinado
        score = (
            vt["malicious"] +
            vt["suspicious"] +
            abuse["abuse_score"]
        )

        resultado = (
            f"{ip} | "
            f"VT_Malicious={vt['malicious']} | "
            f"VT_Suspicious={vt['suspicious']} | "
            f"AbuseScore={abuse['abuse_score']} | "
            f"Reports={abuse['total_reports']} | "
            f"TotalScore={score}"
        )

        print(resultado)

        if score > 0:
            ip_con_mascara = f"{ip}/32"
            resultados_positivos.append(ip_con_mascara)

        # Evitar rate limiting general
        time.sleep(1)

    with open(OUTPUT_FILE, "w") as f:
        f.write(
            f"# Generado: {datetime.now()}\n\n"
        )

        for linea in resultados_positivos:
            f.write(linea + "\n")

    print("\nArchivo generado:", OUTPUT_FILE)
    print("IPs con score > 0:", len(resultados_positivos))
    print("\nIPs positivas:")
    for ip in resultados_positivos:
        print(ip)


if __name__ == "__main__":
    main()