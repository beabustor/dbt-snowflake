"""Ejecuta dos lotes de ventas con dbt y verifica el resultado de un reintento."""

import argparse
import csv
import os
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb


PROYECTO = Path(__file__).resolve().parents[1]
COLUMNAS = ("fecha_pedido", "pedidos_pagados", "importe_pagado_eur")
VENTAS_LOTE_1 = [
    (date(2025, 3, 10), 2, Decimal("165.50")),
    (date(2025, 3, 11), 1, Decimal("59.00")),
]
VENTAS_LOTE_2 = [
    (date(2025, 3, 10), 2, Decimal("145.00")),
    (date(2025, 3, 11), 3, Decimal("184.00")),
]


def ejecutar_lote(lote, entorno, *, cargar_seed=False):
    print(f"\nProcesando lote {lote}", flush=True)
    comando = [
        "dbt", "build",
        "--profiles-dir", ".",
        "--target", "local",
        "--vars", f"{{lote_hasta: {lote}}}",
    ]
    if not cargar_seed:
        comando.extend(["--select", "stg_eventos_pedidos+"])
    subprocess.run(comando, cwd=PROYECTO, env=entorno, check=True)


def leer_estado(base):
    with duckdb.connect(str(base), read_only=True) as conexion:
        ventas = conexion.execute(
            """
            select fecha_pedido, pedidos_pagados, importe_pagado_eur
            from analytics.ventas_diarias
            order by fecha_pedido
            """
        ).fetchall()
        pedidos = conexion.execute(
            "select * from analytics.fct_pedidos order by pedido_id"
        ).fetchall()
    return ventas, pedidos


def guardar_resultado(ruta, ventas):
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        salida = csv.writer(archivo)
        salida.writerow(COLUMNAS)
        salida.writerows(ventas)
    print(f"\n{ruta}")
    for fecha, pedidos, importe in ventas:
        print(f"  {fecha} | {pedidos} pedidos pagados | {importe:.2f} EUR")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--salida", type=Path, default=PROYECTO / "resultados",
        help="Directorio donde guardar los tres informes CSV (por defecto, resultados/).",
    )
    args = parser.parse_args()

    with TemporaryDirectory(prefix="ventas-dbt-") as temporal:
        carpeta = Path(temporal)
        base = carpeta / "ventas.duckdb"
        entorno = {
            **os.environ,
            "VENTAS_DUCKDB_PATH": str(base),
            "DBT_TARGET_PATH": str(carpeta / "target"),
            "DBT_LOG_PATH": str(carpeta / "logs"),
        }

        ejecutar_lote(1, entorno, cargar_seed=True)
        ventas_1, pedidos_1 = leer_estado(base)
        if ventas_1 != VENTAS_LOTE_1 or len(pedidos_1) != 4:
            raise SystemExit(f"El lote 1 no coincide con el escenario previsto: {ventas_1!r}")

        ejecutar_lote(2, entorno)
        ventas_2, pedidos_2 = leer_estado(base)
        if ventas_2 != VENTAS_LOTE_2 or len(pedidos_2) != 6:
            raise SystemExit(f"El lote 2 no coincide con el escenario previsto: {ventas_2!r}")

        print("\nReintentando el último lote para comprobar la idempotencia", flush=True)
        ejecutar_lote(2, entorno)
        ventas_reintento, pedidos_reintento = leer_estado(base)
        if (ventas_reintento, pedidos_reintento) != (ventas_2, pedidos_2):
            raise SystemExit("El reintento modificó los pedidos o el informe diario.")

    args.salida.mkdir(parents=True, exist_ok=True)
    guardar_resultado(args.salida / "lote_1.csv", ventas_1)
    guardar_resultado(args.salida / "lote_2.csv", ventas_2)
    guardar_resultado(args.salida / "lote_2_reintento.csv", ventas_reintento)
    print("\nVerificación completa. El reintento dejó intactos los pedidos y el informe.")


if __name__ == "__main__":
    main()
