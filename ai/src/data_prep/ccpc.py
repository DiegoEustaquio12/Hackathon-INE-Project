"""Lo que todas las fases necesitan saber del CCPC: rutas, años, columnas y cómo leer la tabla limpia.

La tabla limpia la produce la Fase 1 (fase1.py) en data/interim/ccpc/, un Parquet por elección.
Desde un script de esta carpeta:

    from ccpc import leer_tabla
    df = leer_tabla(anios=[2018, 2021], columnas=["EDOCVE", "MPIOCVE", "SV", "NV"])

Desde un notebook de ai/notebooks/, antes del import: sys.path.append("../src/data_prep")
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
RAW = RAIZ / "data" / "raw"
INTERIM = RAIZ / "data" / "interim" / "ccpc"
REPORTES = RAIZ / "docs" / "reports"

ANIOS = (2009, 2012, 2015, 2018, 2021, 2024)
TIPO_ELECCION = {
    2009: "intermedia",
    2012: "presidencial",
    2015: "intermedia",
    2018: "presidencial",
    2021: "intermedia",
    2024: "presidencial",
}

# Las 16 columnas de los CSV, en su orden original
COLUMNAS = [
    "AELEC", "FELECCION", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM", "SECCION", "TIPOSEC",
    "DEF", "DEL", "SEXO", "EDAD", "LN", "SV", "NV", "NS",
]

# Tipos con los que se leen los CSV. DEF y DEL van como texto porque sus vacíos
# vienen escritos como " " o como celda vacía; la Fase 1 los convierte a número.
TIPOS = {
    "AELEC": "int16",
    "FELECCION": "str",
    "EDOCVE": "int8",
    "EDONOM": "str",
    "MPIOCVE": "int16",
    "MPIONOM": "str",
    "SECCION": "int16",
    "TIPOSEC": "str",
    "DEF": "str",
    "DEL": "str",
    "SEXO": "int8",
    "EDAD": "int16",
    "LN": "int32",
    "SV": "int32",
    "NV": "int32",
    "NS": "int32",
}

CONTEOS = ["LN", "SV", "NV", "NS"]

# Etapas de vida del INE y la edad en la que empieza cada una. Las edades muy altas caen en "60 o más".
ETAPAS = ["18 a 24", "25 a 34", "35 a 44", "45 a 59", "60 o más"]
INICIO_ETAPAS = [18, 25, 35, 45, 60]


def archivo_limpio(anio: int) -> Path:
    return INTERIM / f"ccpc_{anio}.parquet"


def leer_tabla(anios=None, columnas=None) -> pd.DataFrame:
    """Lee la tabla limpia de la Fase 1.

    Pide solo las columnas que vayas a usar: la tabla completa de las seis elecciones
    tiene unos 55 millones de filas y ocupa varios GB en memoria.
    """
    if anios is None:
        anios = ANIOS
    elif isinstance(anios, int):
        anios = [anios]
    faltan = [a for a in anios if not archivo_limpio(a).exists()]
    if faltan:
        raise FileNotFoundError(f"Falta la tabla limpia de {faltan}. Corre: python ai/src/data_prep/fase1.py")
    piezas = [pd.read_parquet(archivo_limpio(a), columns=columnas) for a in anios]
    return pd.concat(piezas, ignore_index=True)
