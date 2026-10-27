"""Añade las features temporales a tablas existentes sin reconstruir los ECEG.

Uso: python scripts/features_eda_municipio.py
Requiere las salidas de Fases 2 y 3. Valida ambas copias antes de publicarlas.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "ai/src/data_prep"))
# Algunos entornos precargan un paquete externo homónimo. Usar el módulo local.
if "ccpc" in sys.modules and not hasattr(sys.modules["ccpc"], "ANIOS"):
    sys.modules.pop("ccpc")

import pandas as pd

from fase3 import (
    ENTRENAMIENTO, PREDICCION, COL_FOTO, LLAVE_MUNICIPIO, LLAVE_SECCION,
    SECCIONES, TIPO_ELECCION, leer_catalogo, cambios_por_clave,
    asignar_territorio, revisar_y_guardar_features, guardar,
)
from features_eda import COLUMNAS, calcular_features_temporales


def main():
    sumas = pd.read_parquet(SECCIONES,
                           columns=["AELEC", *LLAVE_MUNICIPIO, "SECCION", "SV", "NV"])
    sumas["primera"] = sumas.groupby(LLAVE_SECCION)["AELEC"].transform("min")
    totales = sumas.groupby("AELEC")[["SV", "NV"]].sum()
    nacional = totales["NV"] / (totales["SV"] + totales["NV"]).where(totales["SV"] + totales["NV"] > 0)
    cambios = cambios_por_clave(leer_catalogo())
    tablas = {}
    for destino in (ENTRENAMIENTO, PREDICCION):
        original = pd.read_parquet(destino.with_suffix(".parquet"))
        partes = []
        for objetivo, foto in original.groupby("eleccion_objetivo", sort=False):
            previas, _, _ = asignar_territorio(sumas, cambios, int(objetivo))
            asignadas = previas.loc[previas["MPIOCVE_T"].notna()].copy()
            asignadas["MPIOCVE"] = asignadas["MPIOCVE_T"].astype("int16")
            hist = asignadas.groupby(["AELEC", *LLAVE_MUNICIPIO], as_index=False)[["SV", "NV"]].sum()
            conocidos = hist["SV"] + hist["NV"]
            hist["abstencion"] = hist["NV"] / conocidos.where(conocidos > 0)
            hist["tipo"] = hist["AELEC"].map(TIPO_ELECCION)
            features = calcular_features_temporales(hist, int(objetivo), nacional)
            ampliada = foto.drop(columns=COLUMNAS, errors="ignore").join(features, on=LLAVE_MUNICIPIO)
            partes.append(ampliada)
        ampliada = pd.concat(partes).sort_index()[COL_FOTO]
        revisar_y_guardar_features(ampliada, destino)
        tablas[destino] = pd.read_parquet(destino.with_name(destino.name + "_features_eda").with_suffix(".parquet"))
    # Ambas tablas y sus copias ya han pasado las comprobaciones.
    for destino, tabla in tablas.items():
        guardar(tabla, destino.with_suffix(".parquet"))
        guardar(tabla, destino.with_suffix(".csv"))
        print(f"{destino.name}: {len(tabla):,} filas, {len(tabla.columns)} columnas; copias verificadas")


if __name__ == "__main__":
    main()
