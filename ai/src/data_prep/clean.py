"""Estandarización de la tabla del CCPC (Fase 1 del plan).

No se borra ninguna fila: aquí solo se ordenan tipos, códigos y grupos de edad.
Las filas raras las marca validate.py.
"""
import numpy as np
import pandas as pd

TIPO_ELECCION = {
    2009: "intermedia",
    2012: "presidencial",
    2015: "intermedia",
    2018: "presidencial",
    2021: "intermedia",
    2024: "presidencial",
}

SEXOS_ESPERADOS = (0, 1, 2)
TIPOS_SECCION_ESPERADOS = ("U", "M", "R")

GRUPOS_EDAD = ["18 a 24", "25 a 34", "35 a 44", "45 a 59", "60 o más"]
BORDES_EDAD = [17, 24, 34, 44, 59, np.inf]


def _a_entero_nullable(s: pd.Series) -> pd.Series:
    texto = s.astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA})
    return pd.to_numeric(texto, errors="coerce").astype("Int16")


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Devuelve la tabla con tipos uniformes, distritos saneados y etapa de vida."""
    df = df.copy()

    for col in ("EDONOM", "MPIONOM", "FELECCION"):
        df[col] = df[col].astype("string").str.strip()

    df["DEF"] = _a_entero_nullable(df["DEF"])
    df["DEL"] = _a_entero_nullable(df["DEL"])

    df["TIPOSEC"] = df["TIPOSEC"].astype("string").str.strip().str.upper()
    df["TIPOSEC"] = pd.Categorical(df["TIPOSEC"], categories=list(TIPOS_SECCION_ESPERADOS))
    df["SEXO"] = df["SEXO"].astype("int8")

    df["tipo_eleccion"] = pd.Categorical(
        df["AELEC"].map(TIPO_ELECCION),
        categories=["intermedia", "presidencial"],
    )

    df["grupo_edad"] = pd.cut(
        df["EDAD"].astype("float64"),
        bins=BORDES_EDAD,
        labels=GRUPOS_EDAD,
        right=True,
    )

    return df
