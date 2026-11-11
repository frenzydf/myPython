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
RESULTS_FILE = Path("abuseip_results.txt")   # para waf_update_ipset.py
RANKING_FILE = Path("abuseip_ranking.csv")   # ranking CSV, score 0-10
WEEKLY_WAF_QUERY = "WAF/Weekly Top IP Report"


HELP_DESCRIPTION = """\
Pipeline IoC -> AbuseIPDB.

Flujo:
  1. cw_query_to_ips.py  Ejecuta un query de CloudWatch Logs Insights (archivo local
                         o saved query) y escribe las IPs en ips.txt.
  2. abuse_ip_block.py   Consulta AbuseIPDB por cada IP y genera, para las IPs
                         que cumplen BLOCK (score >= 25 o riesgo >= 50):
                           abuseip_results.txt  IP/32, listo para waf_update_ipset.py
                           abuseip_ranking.csv  #,IP,Score (0-10), de mayor a menor
  3. Imprime abuseip_results.txt (y abuseip_ranking.csv si se usa --ranking).

Este script NO modifica el WAF. Revise el resultado y luego ejecute
waf_update_ipset.py para agregarlas al IPSet.
"""

HELP_EPILOG = f"""\
ejemplos:
  python main.py                                   usa test-query.txt
  python main.py -qf test-query-sb-prd.txt
  python main.py -ww                               saved query '{WEEKLY_WAF_QUERY}'
  python main.py -ww -wn 3d                        mismos datos, ultimos 3 dias
  python main.py -ww -r                            ademas imprime el ranking CSV
  python main.py -sq "WAF/Otro query" -if ClientIP
  python main.py -qf q.txt -lg mi-log-group

ventana de tiempo:
  Formato <numero><unidad> con unidad s, m, h, d o w (5m, 12h, 7d, 1w).
  Sin --window (-wn) se usa la del encabezado START= del query; si no la trae,
  5m para archivos y 7d para saved queries.

archivos:
  entrada  test-query.txt (por defecto)
  salida   ips.txt, abuseip_results.txt, abuseip_ranking.csv
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="main.py",
        description=HELP_DESCRIPTION,
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = p.add_mutually_exclusive_group()
    src.add_argument("-qf", "--query-file", metavar="ARCHIVO",
                     help="archivo con el query de Logs Insights (default: test-query.txt). "
                          "Excluyente con --saved-query y --weekly-waf")
    src.add_argument("-sq", "--saved-query", metavar="NOMBRE",
                     help="nombre completo de un saved query de CloudWatch, incluida la carpeta "
                          "(ej. 'WAF/Weekly Top IP Report')")
    src.add_argument("-ww", "--weekly-waf", action="store_true",
                     help=f"atajo para --saved-query '{WEEKLY_WAF_QUERY}'")
    opts = p.add_argument_group("ajustes opcionales")
    opts.add_argument("-wn", "--window", metavar="VENTANA",
                      help="ventana hacia atras desde ahora (5m, 12h, 7d, 1w); "
                           "reemplaza la del query")
    opts.add_argument("-lg", "--log-group", metavar="NOMBRE", action="append", default=[],
                      help="log group a consultar; repetible. Reemplaza los del query")
    opts.add_argument("-r", "--ranking", action="store_true",
                      help="imprime en consola el ranking (abuseip_ranking.csv); "
                           "el archivo se genera siempre")
    opts.add_argument("-if", "--ip-field", metavar="CAMPO",
                      help="columna del resultado que contiene la IP (default: ClientIP)")
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
        [sys.executable, "-u", script, *(extra_args or [])],
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
    if args.ranking:
        print_results(RANKING_FILE)


if __name__ == "__main__":
    main()
