#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import time
import ipaddress
import urllib3

# Suprime warnings por verify=False (entorno con inspección SSL)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

INPUT_FILE = "ips.txt"
OUTPUT_FILE = "abuseip_results.txt"
API_URL = "https://api.abuseipdb.com/api/v2/check"
MAX_AGE_DAYS = 90
SLEEP_SECONDS = 1  # 20-150 IPs: 1s es suficiente para no golpear rate limit

API_KEY = os.getenv("ABUSE_APIKEY")

if not API_KEY:
    print("ERROR: La variable de entorno ABUSE_APIKEY no está definida")
    exit(1)


def is_valid_ip(ip: str) -> bool:
    """Valida IPv4/IPv6 usando ipaddress."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def calcular_riesgo(score: int, reports: int) -> int:
    """
    Riesgo ponderado propuesto:
    - Score pesa más (x5)
    - Reports cap a 20 para evitar inflar CDNs
    """
    return (score * 5) + min(reports, 20)


def clasificar_riesgo(riesgo: int) -> str:
    """Devuelve la etiqueta de clasificación basada en el riesgo."""
    if riesgo <= 10:
        return "BAJO"
    elif riesgo <= 25:
        return "OBSERVACIÓN"
    elif riesgo <= 50:
        return "SOSPECHOSO"
    else:
        return "ALTO"


def debe_bloquear(score: int, riesgo: int) -> bool:
    """
    Flag BLOCK:
    - Bloquea si Score >= 25 (señal fuerte de AbuseIPDB)
    - O si Riesgo >= 50 (acumulado alto)
    """
    return (score >= 25) or (riesgo >= 50)


headers = {
    "Key": API_KEY,
    "Accept": "application/json"
}

results = []

# Lee IPs (una por línea); ignora líneas vacías o con espacios
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    ips = [line.strip() for line in f if line.strip()]

counter = 1

for ip in ips:
    if not is_valid_ip(ip):
        print(f"{ip} - Invalid")
        continue

    params = {
        "ipAddress": ip,
        "maxAgeInDays": MAX_AGE_DAYS,
        "verbose": False
    }

    try:
        response = requests.get(
            API_URL,
            headers=headers,
            params=params,
            timeout=10,
            verify=False  # Entorno con inspección SSL
        )

        if response.status_code != 200:
            print(f"[{counter}] {ip} → Error HTTP {response.status_code}")
            continue

        data = response.json().get("data", {})
        score = int(data.get("abuseConfidenceScore", 0) or 0)
        total_reports = int(data.get("totalReports", 0) or 0)

        riesgo = calcular_riesgo(score, total_reports)
        clasificacion = clasificar_riesgo(riesgo)
        block = debe_bloquear(score, riesgo)

        # Print enriquecido y con resultrado true
        if block:
            print(
                f"[{counter}] {ip} → "
                f"Score: {score} | Reports: {total_reports} | "
                f"Riesgo: {riesgo} ({clasificacion}) | BLOCK: {block}"
            )

        results.append((counter, ip, score, total_reports, riesgo, clasificacion, block))
        counter += 1

        time.sleep(SLEEP_SECONDS)

    except requests.exceptions.RequestException as e:
        print(f"[{counter}] {ip} → Request Error: {e}")

# Salida tipo CSV en TXT
with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
    out.write("#,IP,Score\n")
    for r in results:
        if r[6]:  # Solo guarda IPs con BLOCK=True  
            out.write(f"{r[1]},{r[2]}\n")

print(f"\nResultados guardados en: {OUTPUT_FILE}")