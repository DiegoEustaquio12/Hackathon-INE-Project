"""Fase 3 del plan: tabla de análisis.

Genera una fila por (elección, estado, sección) en data/processed/tabla_analisis.parquet
y el desglose por edad/sexo en tabla_analisis_desglose.parquet.
También escribe docs/reports/diccionario_datos.md.
"""
from pathlib import Path
import sys

import pandas as pd
import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
INTERIM = RAIZ / "data" / "interim" / "ccpc_limpio"
HISTORIAL = RAIZ / "data" / "interim" / "historial_secciones.parquet"
PROC = RAIZ / "data" / "processed"
TAB_ANALISIS = PROC / "tabla_analisis.parquet"
TAB_DESGLOSE = PROC / "tabla_analisis_desglose.parquet"
DICCIONARIO = RAIZ / "docs" / "reports" / "diccionario_datos.md"

ANIOS = (2009, 2012, 2015, 2018, 2021, 2024)

def leer_un_anio(a: int) -> pd.DataFrame:
    ruta = INTERIM / f"AELEC={a}" / "part-0.parquet"
    return pd.read_parquet(ruta)


def construir_seccion(a: int, df: pd.DataFrame) -> pd.DataFrame:
    # sección nivel
    grp = df.groupby(["EDOCVE", "SECCION"], as_index=False)
    sec = grp.agg(
        EDONOM=("EDONOM", "first"),
        MPIOCVE=("MPIOCVE", "first"),
        MPIONOM=("MPIONOM", "first"),
        TIPOSEC=("TIPOSEC", "first"),
        DEF=("DEF", "first"),
        DEL=("DEL", "first"),
        LN=("LN", "sum"),
        SV=("SV", "sum"),
        NV=("NV", "sum"),
        NS=("NS", "sum"),
        filas_marcadas=("flag_revision", "sum"),
        tipo_eleccion=("tipo_eleccion", "first"),
    )
    sec["anio_eleccion"] = a

    # participación
    denom_part = sec["SV"] + sec["NV"]
    sec["participacion"] = sec["SV"] / denom_part.where(denom_part > 0)
    sec["abstencion"] = sec["NV"] / denom_part.where(denom_part > 0)

    sec["tasa_ns"] = sec["NS"] / sec["LN"].where(sec["LN"] > 0)
    sec["sin_dato"] = denom_part == 0

    # marcas (umbrales provisionales, documentados)
    sec["seccion_pequena"] = sec["LN"] < 100
    sec["ns_alto"] = sec["tasa_ns"] > 0.10

    return sec


def construir_desglose(a: int, df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby(["EDOCVE", "SECCION", "grupo_edad", "SEXO"], as_index=False)
    d = grp.agg(
        LN=("LN", "sum"),
        SV=("SV", "sum"),
        NV=("NV", "sum"),
        NS=("NS", "sum"),
    )
    d["anio_eleccion"] = a
    return d

def _n(x: int) -> str:
    return f"{x:,}"


def escribir_diccionario() -> Path:
    texto = f"""# Diccionario de datos — Fase 3

Generado por `python -m ai.src.data_prep.build_analisis`.

## 1. `data/processed/tabla_analisis.parquet`
Una fila por `(anio_eleccion, EDOCVE, SECCION)`. Agregación a nivel de sección electoral (años 2009–2024).

| Columna | Definición | Fuente | Año | Transformación |
|---|---|---|---|---|
| `anio_eleccion` | Año de la elección | `AELEC` | 2009–2024 | Copiado |
| `tipo_eleccion` | `intermedia` o `presidencial` | `AELEC` | 2009–2024 | Mapeo (2009/15/21 intermedia, 12/18/24 presidencial) |
| `EDOCVE`, `entidad`/`EDONOM` | Estado (clave y nombre) | `EDOCVE`, `EDONOM` | 2009–2024 | Primera ocurrencia por sección/año |
| `MPIOCVE`, `MPIONOM`, `municipio` | Municipio | `MPIOCVE`, `MPIONOM` | 2009–2024 | Primera ocurrencia por sección/año |
| `SECCION` | Sección electoral | `SECCION` | 2009–2024 | Llave |
| `TIPOSEC` | Tipo U/M/R | `TIPOSEC` | 2009–2024 | Primera ocurrencia por sección/año (mayúsculas) |
| `DEF`, `DEL` | Distritos federal/local | `DEF`, `DEL` | 2009–2024 | Primera ocurrencia; pueden ser nulos (especialmente 2009/2012/2024) — **no se rellenan** |
| `LN` | Lista nominal | `LN` | 2009–2024 | Suma por (estado,sección) |
| `SV`, `NV`, `NS` | Sí votaron, No votaron, No especificado | `SV`,`NV`,`NS` | 2009–2024 | Suma por (estado,sección) |
| `participacion` | `SV/(SV+NV)` | Calculada | 2009–2024 | Se deja **NULL** si `SV+NV==0` (sección sin dato). Nunca promedio de porcentajes |
| `abstencion` | `NV/(SV+NV)` | Calculada | 2009–2024 | Igual regla (NULL si sin dato) |
| `tasa_ns` | `NS/LN` | Calculada | 2009–2024 | NULL si `LN==0` |
| `sin_dato` | `SV+NV==0` | Calculada | 2009–2024 | Marca |
| `filas_marcadas` | Nº de filas con alguna bandera | `flag_revision` | 2009–2024 | Suma por (estado,sección) |
| `seccion_pequena` | `LN < 100` | Calculada | 2009–2024 | **Umbral provisional** (pendiente Fase 5) |
| `ns_alto` | `tasa_ns > 0.10` | Calculada | 2009–2024 | **Umbral provisional** (pendiente Fase 5) |
| `clasificacion` | Historial | Fase 2 | 2009–2024 | `historial_completo`, `nueva`, `con_huecos`, `desaparecida` |
| `primera_eleccion`, `ultima_eleccion`, `n_anios_presente`, `presente_YYYY`, `es_nueva_2024` | Presencias | Fase 2 | 2009–2024 | Derivados |
| `cambio_municipio/tipo/distrito_federal/local`, `anio_cambio_*` | Cambios de territorio | Fase 2 | 2009–2024 | Entre años consecutivos donde existen ambas; distrito puede no ser comparable si es nulo |

## 2. `data/processed/tabla_analisis_desglose.parquet`
Una fila por `(anio_eleccion, EDOCVE, SECCION, grupo_edad, SEXO)`. Desglose de LN/SV/NV/NS por grupo de edad y sexo.

| Columna | Definición | Fuente | Año | Transformación |
|---|---|---|---|---|
| `anio_eleccion` | Año | `AELEC` | 2009–2024 | Copiado |
| `EDOCVE`, `SECCION` | Claves | Original | 2009–2024 | — |
| `grupo_edad` | Grupo INE: `18 a 24, 25 a 34, 35 a 44, 45 a 59, 60 o más` | `EDAD` | 2009–2024 | `pd.cut` con etiquetas (Fase 1) |
| `SEXO` | 0=Hombre, 1=Mujer, 2=No binario (solo 2024) | `SEXO` | 2009–2024 | Entero |
| `LN`, `SV`, `NV`, `NS` | Conteos | Original | 2009–2024 | Suma por clave |

**Notas de anonimización:** Los datos ya son agregados a nivel de sección/grupo; no contienen información individual. `data/processed/` se considera lista para entrega (como indica README).

**Notas metodológicas:** Participación/abstención se calculan **sumando primero** (total de SV/NV por sección/año), nunca promediando porcentajes de subgrupos. Los umbrales `seccion_pequena` y `ns_alto` son provisionales y se revisan en Fase 5.
"""
    DICCIONARIO.parent.mkdir(parents=True, exist_ok=True)
    DICCIONARIO.write_text(texto, encoding="utf-8")
    return DICCIONARIO

def procesar():
    PROC.mkdir(parents=True, exist_ok=True)

    sec_all = []
    des_all = []
    for a in ANIOS:
        df = leer_un_anio(a)
        sec = construir_seccion(a, df)
        des = construir_desglose(a, df)
        sec_all.append(sec)
        des_all.append(des)

    sec_all = pd.concat(sec_all, ignore_index=True)
    des_all = pd.concat(des_all, ignore_index=True)

    hist = pd.read_parquet(HISTORIAL)
    sec_all = sec_all.merge(
        hist,
        on=["EDOCVE", "SECCION"],
        how="left",
        suffixes=("", "_hist"),
    )

    TAB_ANALISIS.parent.mkdir(parents=True, exist_ok=True)
    TAB_DESGLOSE.parent.mkdir(parents=True, exist_ok=True)
    sec_all.to_parquet(TAB_ANALISIS, index=False, compression="zstd")
    des_all.to_parquet(TAB_DESGLOSE, index=False, compression="zstd")

    escribir_diccionario()

    return sec_all, des_all


def main(argv=None):
    sec_all, des_all = procesar()
    print(f"Tabla análisis: {TAB_ANALISIS} ({len(sec_all):,} filas)")
    print(f"Desglose:       {TAB_DESGLOSE} ({len(des_all):,} filas)")
    print(f"Diccionario:    {DICCIONARIO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
