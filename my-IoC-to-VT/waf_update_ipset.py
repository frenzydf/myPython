#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
waf_update_ipset.py – Agrega las IPs de abuseip_results.txt al IPSet de WAFv2.

Requiere:
  - Perfil AWS 'vpc1' con permisos wafv2:GetIPSet y wafv2:UpdateIPSet
  - Variable de entorno IPSET_ARN|
"""

import os
import sys
import boto3
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────────────────────
AWS_PROFILE  = "vpc1"
AWS_REGION   = "us-east-1"
INPUT_FILE   = Path("abuseip_results.txt")
IPSET_ARN    = os.getenv("IPSET_ARN", "").strip()

if not IPSET_ARN:
    print("[ERROR] La variable de entorno IPSET_ARN no está definida.")
    sys.exit(1)

# Extraer nombre e ID desde el ARN  (formato: .../nombre/id)
_arn_parts   = IPSET_ARN.split("/")
if len(_arn_parts) < 2:
    print(f"[ERROR] ARN de IPSet inválido: '{IPSET_ARN}'")
    sys.exit(1)

IPSET_NAME   = _arn_parts[-2]
IPSET_ID     = _arn_parts[-1]
IPSET_SCOPE  = "REGIONAL"


def load_new_ips(path: Path) -> list[str]:
    """Lee el archivo de resultados e ignora la línea de cabecera."""
    if not path.exists():
        print(f"[ERROR] No se encontró el archivo '{path}'.")
        sys.exit(1)

    ips = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Saltar línea vacía o cabecera
            if not line or line.startswith("#"):
                continue
            # Normalizar: agregar /32 si no tiene prefijo CIDR
            if "/" not in line:
                line = f"{line}/32"
            ips.append(line)

    return ips


def main() -> None:
    new_ips = load_new_ips(INPUT_FILE)

    if not new_ips:
        print("[ADVERTENCIA] No hay IPs en el archivo de resultados. Nada que agregar.")
        sys.exit(0)

    print(f"[*] IPs a agregar al IPSet:")
    for ip in new_ips:
        print(f"    {ip}")

    # ── Cliente WAFv2 ─────────────────────────────────────────────────────────
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    waf     = session.client("wafv2")

    # ── Obtener estado actual del IPSet ───────────────────────────────────────
    print(f"\n[*] Consultando IPSet '{IPSET_NAME}' ({IPSET_ID})...")
    response = waf.get_ip_set(
        Name=IPSET_NAME,
        Scope=IPSET_SCOPE,
        Id=IPSET_ID,
    )

    lock_token     = response["LockToken"]
    existing_ips   = response["IPSet"]["Addresses"]

    print(f"    IPs existentes en el IPSet: {len(existing_ips)}")

    # ── Merge: unión sin duplicados, preservando orden ────────────────────────
    existing_set = set(existing_ips)
    added        = [ip for ip in new_ips if ip not in existing_set]
    skipped      = [ip for ip in new_ips if ip in existing_set]

    if skipped:
        print(f"\n[~] Ya presentes (se omiten):")
        for ip in skipped:
            print(f"    {ip}")

    if not added:
        print("\n[OK] Todas las IPs ya estaban en el IPSet. No se realizaron cambios.")
        sys.exit(0)

    merged_ips = existing_ips + added

    # ── Actualizar IPSet ──────────────────────────────────────────────────────
    print(f"\n[*] Actualizando IPSet con {len(added)} IP(s) nueva(s)...")
    waf.update_ip_set(
        Name=IPSET_NAME,
        Scope=IPSET_SCOPE,
        Id=IPSET_ID,
        LockToken=lock_token,
        Addresses=merged_ips,
    )

    print(f"[OK] IPSet actualizado exitosamente.")
    print(f"     Total de IPs ahora en el IPSet: {len(merged_ips)}")
    print(f"\n[+] IPs agregadas:")
    for ip in added:
        print(f"    {ip}")


if __name__ == "__main__":
    main()
