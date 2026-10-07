"""Fase 1 del plan: carga, limpieza y reporte de calidad del CCPC.

Uso (desde la raíz del repo, con el entorno activo):

    python -m ai.src.data_prep.build_interim

Escribe la tabla única en `data/interim/ccpc_limpio/` (un Parquet por elección,
particionado como AELEC=<año>) y el reporte en `docs/reports/reporte_calidad.md`.
"""
import argparse
import sys
import time
from pathlib import Path

from . import clean, load, validate

RAIZ = Path(__file__).resolve().parents[3]
RAW_POR_DEFECTO = RAIZ / "data" / "raw"
INTERIM_POR_DEFECTO = RAIZ / "data" / "interim" / "ccpc_limpio"
REPORTE_POR_DEFECTO = RAIZ / "docs" / "reports" / "reporte_calidad.md"


def guardar(df, interim: Path, anio: int) -> Path:
    """Escribe un año en su propia partición AELEC=<año> (sin la columna dentro)."""
    carpeta = interim / f"AELEC={anio}"
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / "part-0.parquet"
    temporal = carpeta / "part-0.parquet.tmp"
    df.drop(columns="AELEC").to_parquet(temporal, index=False, compression="zstd")
    temporal.replace(destino)
    return destino


def procesar(raw: Path, interim: Path, anios: tuple[int, ...]):
    resumenes = []
    for anio in anios:
        inicio = time.time()
        df = load.leer_anio(raw, anio)
        df = clean.limpiar(df)
        df = validate.marcar(df)
        destino = guardar(df, interim, anio)
        resumen = validate.resumir(df)
        resumenes.append(resumen)
        print(
            f"[{anio}] {resumen['filas']:,} filas, {resumen['secciones']:,} secciones, "
            f"{resumen['marcadas']:,} marcadas -> {destino.relative_to(RAIZ)} "
            f"({time.time() - inicio:.0f}s)"
        )
    return resumenes


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fase 1: unifica y limpia los CSV del CCPC")
    parser.add_argument("--raw", type=Path, default=RAW_POR_DEFECTO, help="CSV crudos")
    parser.add_argument("--interim", type=Path, default=INTERIM_POR_DEFECTO,
                        help="destino de la tabla única (Parquet por elección)")
    parser.add_argument("--reporte", type=Path, default=REPORTE_POR_DEFECTO,
                        help="destino del reporte de calidad")
    parser.add_argument("--anios", nargs="+", type=int, default=list(load.ANIOS),
                        choices=list(load.ANIOS), help="elecciones a procesar")
    args = parser.parse_args(argv)

    anios = tuple(args.anios)
    resumenes = procesar(args.raw, args.interim, anios)
    reporte = validate.escribir_reporte(resumenes, args.reporte, anios)

    total_filas = sum(r["filas"] for r in resumenes)
    total_marcadas = sum(r["marcadas"] for r in resumenes)
    regla = sum(r["banderas"]["flag_regla_ln"] for r in resumenes)
    print(f"\nTabla única: {args.interim} ({total_filas:,} filas)")
    print(f"Reporte:     {reporte}")
    print(f"Filas marcadas: {total_marcadas:,} | fallan la regla LN: {regla:,}")
    if regla:
        print("ATENCIÓN: hay filas que no cuadran LN = SV + NV + NS; están en el reporte.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
