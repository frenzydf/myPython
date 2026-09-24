#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py – Orquestador del pipeline IoC → VT

Flujo:
  1. cw_query_to_ips.py  → consulta CloudWatch Logs Insights y genera ips.txt
  2. abuse_ip_block.py   → consulta AbuseIPDB por cada IP y genera abuseip_results.txt
  3. Imprime el contenido de abuseip_results.txt
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "cw_query_to_ips.py",
    "abuse_ip_block.py",
]
RESULTS_FILE = Path("abuseip_results.txt")


def run_script(script: str) -> None:
    """Ejecuta un script Python como subproceso y transmite su salida en tiempo real."""
    print(f"\n{'=' * 60}")
    print(f"  Ejecutando: {script}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(
        [sys.executable, script],
        # Hereda el entorno actual (incluye ABUSE_APIKEY y credenciales AWS)
        env=None,
    )

    if result.returncode != 0:
        print(f"\n[ERROR] '{script}' terminó con código {result.returncode}. Abortando pipeline.")
        sys.exit(result.returncode)


def print_results(path: Path) -> None:
    """Imprime el contenido del archivo de resultados."""
    print(f"\n{'=' * 60}")
    print(f"  Resultados: {path}")
    print(f"{'=' * 60}\n")

    if not path.exists():
        print(f"[ADVERTENCIA] El archivo '{path}' no existe.")
        return

    content = path.read_text(encoding="utf-8")
    if content.strip():
        print(content)
    else:
        print("(El archivo está vacío)")


def main() -> None:
    for script in SCRIPTS:
        if not Path(script).exists():
            print(f"[ERROR] No se encontró el script '{script}'.")
            sys.exit(1)
        run_script(script)

    print_results(RESULTS_FILE)


if __name__ == "__main__":
    main()
