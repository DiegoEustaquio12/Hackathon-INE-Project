"""Extracción de características (feature engineering) a nivel municipal.

Por cada archivo de la tabla limpia de la Fase 1 (un Parquet por elección en
data/interim/ccpc/), hace un groupby por municipio (EDOCVE + MPIOCVE) y extrae la
distribución (media, desviación estándar, máximo y mínimo) de las variables
relevantes, más el total de secciones del municipio.

Reglas de agregación:
- Identificadores (AELEC, EDOCVE, EDONOM, MPIOCVE, MPIONOM): estáticos, nunca se resumen.
- SECCION: solo sirve para contar secciones del municipio (TOTAL_SECCIONES); no se
  promedia ni se le calculan estadísticas.
- DEF y DEL (distritos): se descartan por completo; no se leen ni aparecen en la salida.
- SEXO, EDAD, LN, SV, NV, NS: sus estadísticas son la salida.
- Los NaN de las columnas _std (municipios con una sola sección) se rellenan con 0;
  los demás NaN no se tocan.

Se usa el Parquet de la Fase 1 en lugar de los 32 CSV estatales porque ya está limpio,
con tipos correctos y validado (docs/reports/reporte_calidad.md).

Uso, desde la raíz del repo con el entorno activado:
    python scripts/features_por_municipio.py                       # las seis elecciones
    python scripts/features_por_municipio.py --anios 2021 2024     # solo algunas
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "ai" / "src" / "data_prep"))

from ccpc import ANIOS, leer_tabla  # noqa: E402

SALIDA = RAIZ / "data" / "interim" / "features_municipio"

LLAVE_MUNICIPIO = ["EDOCVE", "MPIOCVE"]
# Códigos y nombres que identifican al estado y al municipio: estáticos
COLUMNAS_IDENTIFICADORAS = ["AELEC", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM"]
# Lista blanca de variables relevantes: sus estadísticas son la salida
COLUMNAS_FEATURES = ["SEXO", "EDAD", "LN", "SV", "NV", "NS"]
# Secciones: solo para contarlas por municipio, nunca se resume su número
COLUMNA_SECCION = "SECCION"
# Se descartan al leer: ni entran a memoria
COLUMNAS_DESCARTADAS = ["DEF", "DEL"]

ESTADISTICAS = ["mean", "std", "max", "min"]


def extraer_features_municipio(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por municipio: estadísticas de las variables relevantes y # de secciones."""
    nombres = df.groupby(LLAVE_MUNICIPIO)[["EDONOM", "MPIONOM"]].first()
    conteo_secciones = (
        df.groupby(LLAVE_MUNICIPIO)[COLUMNA_SECCION].nunique().rename("TOTAL_SECCIONES")
    )
    stats = df.groupby(LLAVE_MUNICIPIO)[COLUMNAS_FEATURES].agg(ESTADISTICAS)
    stats.columns = [f"{columna}_{metrica}" for columna, metrica in stats.columns]
    # Solo las desviaciones estándar se rellenan: NaN cuando el municipio tiene 1 sección
    columnas_std = [c for c in stats.columns if c.endswith("_std")]
    stats[columnas_std] = stats[columnas_std].fillna(0)

    salida = pd.concat([nombres, conteo_secciones, stats], axis=1).reset_index()
    salida.insert(0, "AELEC", df["AELEC"].iloc[0])  # misma elección en todo el archivo

    if salida.duplicated(LLAVE_MUNICIPIO).any():
        raise SystemExit("ERROR: la salida tiene municipios repetidos")
    fuga = [c for c in salida.columns
            if c.startswith(tuple(COLUMNAS_DESCARTADAS)) or c.startswith("SECCION_")]
    if fuga:
        raise SystemExit(f"ERROR: la salida conserva columnas descartadas: {fuga}")
    return salida


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Features de distribución por municipio")
    parser.add_argument("--anios", nargs="+", type=int, choices=ANIOS, default=list(ANIOS),
                        help="elecciones a procesar (por defecto las seis)")
    args = parser.parse_args(argv)

    SALIDA.mkdir(parents=True, exist_ok=True)
    columnas = list(dict.fromkeys(COLUMNAS_IDENTIFICADORAS + [COLUMNA_SECCION] + COLUMNAS_FEATURES))

    for anio in sorted(set(args.anios)):
        df = leer_tabla(anios=[anio], columnas=columnas)
        salida = extraer_features_municipio(df)
        destino = SALIDA / f"features_{anio}.parquet"
        salida.to_parquet(destino, index=False)
        print(f"[{anio}] {len(salida):,} municipios | {len(salida.columns)} columnas "
              f"-> {destino.relative_to(RAIZ)}")
        del df  # libera la memoria antes de la siguiente elección
    return 0


if __name__ == "__main__":
    sys.exit(main())
