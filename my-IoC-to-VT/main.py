#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py – Orquestador del pipeline IoC → VT

Flujo:
  1. cw_query_to_ips.py  → consulta CloudWatch Logs Insights y genera ips.txt
  2. abuse_ip_block.py   → consulta AbuseIPDB por cada IP y genera abuseip_results.txt
  3. Imprime el contenido de abuseip_results.txt
"""

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "cw_query_to_ips.py",
    "abuse_ip_block.py",
]
RESULTS_FILE = Path("abuseip_results.txt")
WEEKLY_WAF_QUERY = "WAF/Weekly Top IP Report"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Pipeline IoC → AbuseIPDB. Por defecto usa el query de test-query.txt.")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--query-file", help="Archivo con el query (default: test-query.txt)")
    src.add_argument("--saved-query", metavar="NAME",
                     help="Saved query de CloudWatch, p. ej. 'WAF/Weekly Top IP Report'")
    src.add_argument("--weekly-waf", action="store_true",
                     help=f"Atajo para --saved-query '{WEEKLY_WAF_QUERY}'")
    p.add_argument("--window", help="Ventana hacia atrás (5m, 12h, 7d)")
    p.add_argument("--log-group", action="append", default=[],
                   help="Log group (repetible); reemplaza a los del query")
    p.add_argument("--ip-field", help="Columna del resultado con la IP (default: ClientIP)")
    return p.parse_args()


def build_cw_args(args: argparse.Namespace) -> list[str]:
    """Traduce los argumentos de main.py a los de cw_query_to_ips.py."""
    out: list[str] = []
    saved = WEEKLY_WAF_QUERY if args.weekly_waf else args.saved_query
    if saved:
        out += ["--saved-query", saved]
    elif args.query_file:
        out += ["--query-file", args.query_file]
    if args.window:
        out += ["--window", args.window]
    for lg in args.log_group:
        out += ["--log-group", lg]
    if args.ip_field:
        out += ["--ip-field", args.ip_field]
    return out


def run_script(script: str, extra_args: list[str] | None = None) -> None:
    """Ejecuta un script Python como subproceso y transmite su salida en tiempo real."""
    print(f"\n{'=' * 60}")
    print(f"  Ejecutando: {script} {' '.join(extra_args or [])}")
    print(f"{'=' * 60}\n")

    result = subprocess.run(
        [sys.executable, script, *(extra_args or [])],
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
    args = parse_args()
    cw_args = build_cw_args(args)

    for script in SCRIPTS:
        if not Path(script).exists():
            print(f"[ERROR] No se encontró el script '{script}'.")
            sys.exit(1)
        # Solo el primer script (consulta a CloudWatch) recibe los argumentos
        run_script(script, cw_args if script == "cw_query_to_ips.py" else None)

    print_results(RESULTS_FILE)


if __name__ == "__main__":
    main()
