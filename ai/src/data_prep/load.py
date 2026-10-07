"""Lectura de los CSV del CCPC y armado de la tabla única (Fase 1 del plan).

Cada elección trae 32 CSV (uno por estado) con las mismas 16 columnas.
Los archivos de 2024 traen un BOM al inicio, por eso se leen con utf-8-sig.
"""
from pathlib import Path

import pandas as pd

COLUMNAS = [
    "AELEC", "FELECCION", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM",
    "SECCION", "TIPOSEC", "DEF", "DEL", "SEXO", "EDAD", "LN", "SV", "NV", "NS",
]

DTYPES = {
    "AELEC": "int16",
    "FELECCION": "string",
    "EDOCVE": "int8",
    "EDONOM": "string",
    "MPIOCVE": "int16",
    "MPIONOM": "string",
    "SECCION": "int32",
    "TIPOSEC": "string",
    "DEF": "string",
    "DEL": "string",
    "SEXO": "int8",
    "EDAD": "int16",
    "LN": "int32",
    "SV": "int32",
    "NV": "int32",
    "NS": "int32",
}

ANIOS = (2009, 2012, 2015, 2018, 2021, 2024)
ARCHIVOS_POR_ANIO = 32


def carpeta_anio(raw: Path, anio: int) -> Path:
    return Path(raw) / f"ConteosCensales{anio}"


def archivos_de(raw: Path, anio: int) -> list[Path]:
    carpeta = carpeta_anio(raw, anio)
    archivos = sorted(carpeta.glob("*.csv"))
    if len(archivos) != ARCHIVOS_POR_ANIO:
        raise FileNotFoundError(
            f"{anio}: se esperaban {ARCHIVOS_POR_ANIO} CSV en {carpeta} y hay {len(archivos)}. "
            "Falta algún estado; corre scripts/download_raw_data.py."
        )
    return archivos


def leer_anio(raw: Path, anio: int) -> pd.DataFrame:
    """Lee los 32 CSV de un año y devuelve una sola tabla con su origen."""
    piezas = []
    for archivo in archivos_de(raw, anio):
        df = pd.read_csv(archivo, encoding="utf-8-sig", dtype=DTYPES)
        if list(df.columns) != COLUMNAS:
            raise ValueError(
                f"{archivo.name}: columnas inesperadas.\n"
                f"  esperadas: {COLUMNAS}\n  encontradas: {list(df.columns)}"
            )
        df["archivo_origen"] = archivo.name
        piezas.append(df)
    return pd.concat(piezas, ignore_index=True)


def iterar_anios(raw: Path, anios: tuple[int, ...] = ANIOS):
    """Yield (anio, tabla) uno por uno, para no cargar los seis años a la vez."""
    for anio in anios:
        yield anio, leer_anio(raw, anio)
