"""Fase 1 del plan: carga y limpieza del CCPC.

Junta los 192 CSV de data/raw/ (32 estados × 6 elecciones) en una sola tabla, sin borrar filas
ni columnas. Las filas raras solo se marcan (columnas flag_*).

Uso, desde la raíz del repo y con el entorno activado:
    python ai/src/data_prep/fase1.py                    # las seis elecciones
    python ai/src/data_prep/fase1.py --anios 2021 2024  # solo algunas

Salida: data/interim/ccpc/ccpc_AAAA.parquet, un archivo por elección (no se versiona).
"""
import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from ccpc import ANIOS, COLUMNAS, CONTEOS, ETAPAS, INICIO_ETAPAS, RAIZ, RAW, TIPO_ELECCION, TIPOS, archivo_limpio

ARCHIVOS_POR_ANIO = 32

# 2009–2021 traen la fecha como día/mes/año; 2024, como mes/día/año
FORMATO_FECHA = {2009: "%d/%m/%Y", 2012: "%d/%m/%Y", 2015: "%d/%m/%Y",
                 2018: "%d/%m/%Y", 2021: "%d/%m/%Y", 2024: "%m/%d/%Y"}

EDAD_MIN, EDAD_MAX = 18, 100  # fuera de este rango la fila se marca; sus conteos se quedan
LLAVE_FILA = ["EDOCVE", "SECCION", "SEXO", "EDAD"]  # identifica una fila dentro de una elección
ORDEN = ["EDOCVE", "MPIOCVE", "SECCION", "SEXO", "EDAD"]
MARCAS = ["flag_regla_ln", "flag_negativo", "flag_duplicado", "flag_codigo", "flag_edad"]


def detener(mensaje: str):
    raise SystemExit(f"\nERROR: {mensaje}")


def contar_lineas(ruta: Path) -> int:
    """Líneas del archivo, contando la última aunque no termine en salto de línea."""
    lineas, ultimo = 0, b"\n"
    with open(ruta, "rb") as f:
        while bloque := f.read(1 << 24):
            lineas += bloque.count(b"\n")
            ultimo = bloque[-1:]
    return lineas + (ultimo != b"\n")


def leer_anio(anio: int) -> pd.DataFrame:
    """Lee los 32 CSV de una elección. Se detiene si falta, sobra o se pierde algo."""
    carpeta = RAW / f"ConteosCensales{anio}"
    archivos = sorted(carpeta.glob("*.csv"))
    if len(archivos) != ARCHIVOS_POR_ANIO:
        detener(f"en {carpeta} hay {len(archivos)} CSV y se esperaban {ARCHIVOS_POR_ANIO}. "
                "Corre scripts/download_raw_data.py")
    piezas = []
    for archivo in archivos:
        try:
            # keep_default_na=False: ningún texto se vuelve vacío por su cuenta; los vacíos se tratan a mano
            df = pd.read_csv(archivo, encoding="utf-8-sig", dtype=TIPOS, keep_default_na=False)
        except ValueError as error:
            detener(f"{archivo.name}: no se pudo leer con los tipos esperados ({error})")
        if list(df.columns) != COLUMNAS:
            detener(f"{archivo.name}: las columnas no son las 16 esperadas: {list(df.columns)}")
        filas_archivo = contar_lineas(archivo) - 1  # menos el encabezado
        if len(df) != filas_archivo:
            detener(f"{archivo.name}: se leyeron {len(df):,} filas y el archivo trae {filas_archivo:,}")
        if df["EDOCVE"].nunique() != 1:
            detener(f"{archivo.name}: trae más de un estado")
        if (df["AELEC"] != anio).any():
            detener(f"{archivo.name}: AELEC no es {anio} en todas las filas")
        piezas.append(df)
    df = pd.concat(piezas, ignore_index=True)
    if sorted(df["EDOCVE"].unique().tolist()) != list(range(1, 33)):
        detener(f"{anio}: los 32 archivos no traen los estados 1 a 32, uno en cada archivo")
    return df


def estandarizar(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    """Uniforma formatos y agrega las columnas nuevas. Las 16 columnas originales se quedan."""
    for col in ["FELECCION", "EDONOM", "MPIONOM"]:
        df[col] = df[col].str.strip()
    df["TIPOSEC"] = df["TIPOSEC"].str.strip().str.upper()

    # Distritos: el vacío llega como " " (2009 y 2012) o como celda vacía (DEL 2024) y queda nulo
    for col in ["DEF", "DEL"]:
        texto = df[col].str.strip()
        vacio = texto == ""
        numero = pd.to_numeric(texto.where(~vacio), errors="coerce")
        if (numero.isna() & ~vacio).any():
            detener(f"{anio}: {col} trae valores que no son número ni vacío")
        df[col] = numero.astype("Int16")

    df["fecha_eleccion"] = pd.to_datetime(df["FELECCION"], format=FORMATO_FECHA[anio])
    df["tipo_eleccion"] = TIPO_ELECCION[anio]
    # [18, 25) es "18 a 24", …, [60, ∞) es "60 o más". EDAD se queda igual.
    etapas = pd.cut(df["EDAD"], bins=[*INICIO_ETAPAS, np.inf], labels=ETAPAS, right=False)
    df["grupo_edad"] = etapas.astype("str")
    return df


def marcar(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    """Agrega las marcas de revisión (sí/no). Ninguna fila se borra."""
    df["flag_regla_ln"] = df["LN"] != df["SV"] + df["NV"] + df["NS"]
    df["flag_negativo"] = (df[CONTEOS] < 0).any(axis=1)
    df["flag_duplicado"] = df.duplicated(LLAVE_FILA, keep=False)
    sexos = [0, 1, 2] if anio >= 2024 else [0, 1]  # el código 2 (no binario) existe desde 2024
    df["flag_codigo"] = ~df["SEXO"].isin(sexos) | ~df["TIPOSEC"].isin(["U", "M", "R"])
    df["flag_edad"] = (df["EDAD"] < EDAD_MIN) | (df["EDAD"] > EDAD_MAX)
    df["flag_revision"] = df[MARCAS].any(axis=1)
    return df


def guardar(df: pd.DataFrame, anio: int) -> Path:
    """Escribe la elección en su Parquet. Primero a un temporal, para no dejar archivos a medias."""
    destino = archivo_limpio(anio)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    df.to_parquet(temporal, index=False, compression="zstd")
    temporal.replace(destino)
    return destino


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fase 1: junta y limpia los CSV del CCPC")
    parser.add_argument("--anios", nargs="+", type=int, choices=ANIOS, default=list(ANIOS),
                        help="elecciones a procesar (por defecto las seis)")
    args = parser.parse_args(argv)

    for anio in sorted(set(args.anios)):
        inicio = time.time()
        df = leer_anio(anio)
        df = estandarizar(df, anio)
        df = marcar(df, anio)
        df = df.sort_values(ORDEN, ignore_index=True)
        destino = guardar(df, anio)
        print(f"[{anio}] {len(df):,} filas | marcadas {int(df['flag_revision'].sum()):,} "
              f"-> {destino.relative_to(RAIZ)} ({time.time() - inicio:.0f} s)")
        del df  # libera la memoria antes de leer la siguiente elección
    return 0


if __name__ == "__main__":
    sys.exit(main())
