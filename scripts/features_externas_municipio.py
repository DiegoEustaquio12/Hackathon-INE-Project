"""Agrega las features sociodemográficas externas y actualiza las tablas canónicas.

Fuente: ECEG (Entorno para la Construcción de Escenarios Geoelectorales) del INEGI,
Censos de Población y Vivienda 2010 y 2020. Los datos vienen por sección; se agregan
a municipio y se unen a:

    data/processed/tabla_municipios_entrenamiento.csv / .parquet
    data/processed/tabla_municipios_2027.csv / .parquet

La lógica de lectura, agregación y unión vive en `ai/src/data_prep/externos.py`.
Este script es el paso reproducible que construye el caché
`data/interim/externos/*.parquet`, actualiza las dos tablas canónicas en su lugar y
escribe `docs/reports/reporte_externos.md`.

`fase3.py` hace la misma unión cuando se corre completo. Este script sirve para
actualizar las tablas existentes sin volver a correr las Fases 1 y 2.

Regla de vintage: cada fila usa el censo más reciente ANTERIOR a su elección
objetivo. 2015 y 2018 usan ECEG 2010; 2021, 2024 y 2027 usan ECEG 2020.

Uso, desde la raíz del repo con el entorno activado:
    python scripts/features_externas_municipio.py
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "ai" / "src" / "data_prep"))

from externos import (  # noqa: E402
    COLUMNAS_EXTERNAS, DICCIONARIO_EXTERNOS, LLAVE, PROCESADOS, RAIZ as RAIZ_REPO,
    SALIDA_EXTERNOS, cargar_o_construir_agregados, unir_externos, validar_externos,
)

REPORTE = RAIZ_REPO / "docs" / "reports" / "reporte_externos.md"
RESPUESTA = ["conocidos_objetivo", "abstencion_objetivo"]
TABLAS = {
    "entrenamiento": PROCESADOS / "tabla_municipios_entrenamiento",
    "2027": PROCESADOS / "tabla_municipios_2027",
}


def guardar(df: pd.DataFrame, destino: Path) -> None:
    """Escribe primero a un temporal y luego lo renombra, para no dejar archivos a medias."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    if destino.suffix == ".parquet":
        df.to_parquet(temporal, index=False, compression="zstd")
    else:
        df.to_csv(temporal, index=False, encoding="utf-8-sig")
    temporal.replace(destino)


def ordenar(salida: pd.DataFrame, columnas_originales: list[str]) -> pd.DataFrame:
    """Deja las features externas antes de las dos columnas de respuesta."""
    base = [c for c in columnas_originales if c not in RESPUESTA]
    return salida[[*base, *COLUMNAS_EXTERNAS, *RESPUESTA]]


def cobertura(nombre: str, salida: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Resumen de cobertura por tabla y año, y municipios sin dato de la fuente elegida."""
    filas = []
    sin_dato = {}
    for eleccion, grupo in salida.groupby("eleccion_objetivo", sort=True):
        fuente = int(grupo["censo_fuente"].iloc[0])
        columna = f"tiene_eceg_{fuente}"
        faltan = grupo.loc[grupo[columna] == 0, LLAVE].drop_duplicates()
        sin_dato[int(eleccion)] = [
            f"{int(e):02d}{int(m):03d}" for e, m in faltan.itertuples(index=False, name=None)
        ]
        filas.append({
            "tabla": nombre,
            "eleccion": int(eleccion),
            "filas": len(grupo),
            "municipios": grupo[LLAVE].drop_duplicates().shape[0],
            "censo_fuente": fuente,
            "con_dato_2010": int(grupo["tiene_eceg_2010"].sum()),
            "con_dato_2020": int(grupo["tiene_eceg_2020"].sum()),
            "con_dato_fuente": int(grupo[columna].sum()),
            "sin_dato_fuente": int((grupo[columna] == 0).sum()),
        })
    return pd.DataFrame(filas), sin_dato


def escribir_reporte(resumen: pd.DataFrame, sin_dato: dict, avisos: list[str]) -> None:
    lineas = [
        "# Reporte de fuentes externas sociodemográficas",
        "",
        "Fuente: **ECEG (Entorno para la Construcción de Escenarios Geoelectorales)** del INEGI,",
        "Censos de Población y Vivienda 2010 y 2020. Los datos originales están por sección;",
        "aquí se agregan a municipio y se incorporan a las tablas canónicas de la Fase 3.",
        "",
        "## Regla de vintage",
        "",
        "Cada fila usa el censo más reciente **anterior** a su elección objetivo:",
        "",
        "- 2015 y 2018: ECEG 2010.",
        "- 2021, 2024 y 2027: ECEG 2020.",
        "",
        "Así no se usa información posterior a la elección que se quiere predecir. La columna",
        "`censo_fuente` indica qué censo se usó en cada fila.",
        "",
        "## Agregación",
        "",
        "- Los conteos se suman por municipio.",
        "- Las tasas se calculan como `suma(numerador) / suma(denominador)`.",
        "- Los promedios se ponderan: `GRAPROES` por `P_15YMAS` y `PROM_OCUP` por `VIVPAR_HAB`.",
        "- Las tasas de vivienda usan `VIVPAR_HAB` en 2010 y `VIVPARH_CV` en 2020, el universo",
        "  de las variables `VPH_*` (viviendas con características captadas).",
        "- Los valores negativos (el centinela `-6` de 6 secciones de 2020) se tratan como faltantes.",
        "- En el ECEG 2010 de Chiapas (07), `GRAPROES` viene escalado por 100; se divide entre 100.",
        "- Los valores de `GRAPROES` mayores a 30 años se tratan como faltantes.",
        "- Un denominador en cero produce `NaN`, no cero.",
        "",
        "## Features",
        "",
        "| Variable | Definición | Fórmula |",
        "|---|---|---|",
    ]
    for nombre, definicion, formula in DICCIONARIO_EXTERNOS:
        lineas.append(f"| `ext_{nombre}` | {definicion} | `{formula}` |")

    lineas += [
        "",
        "\\* En 2020 el denominador es `VIVPARH_CV` (viviendas con características captadas).",
        "",
        "## Cobertura",
        "",
        "| Tabla | Elección | Filas | Municipios | Censo | Con dato del censo | Sin dato |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for fila in resumen.itertuples(index=False):
        lineas.append(
            f"| {fila.tabla} | {fila.eleccion} | {fila.filas:,} | {fila.municipios:,} | "
            f"{fila.censo_fuente} | {fila.con_dato_fuente:,} | {fila.sin_dato_fuente:,} |"
        )

    lineas += ["", "### Municipios sin dato del censo elegido", ""]
    for eleccion, claves_faltantes in sin_dato.items():
        if claves_faltantes:
            muestra = ", ".join(f"`{k}`" for k in claves_faltantes[:15])
            sufijo = "" if len(claves_faltantes) <= 15 else f" … (+{len(claves_faltantes) - 15})"
            lineas.append(f"- **{eleccion}:** {len(claves_faltantes)} municipios: {muestra}{sufijo}")
        else:
            lineas.append(f"- **{eleccion}:** sin faltantes.")

    lineas += [
        "",
        "Los municipios sin dato son, en su mayoría, municipios creados después del censo.",
        "Se conservan con `NaN` y `tiene_eceg_2010 = 0` o `tiene_eceg_2020 = 0`; no se imputan",
        "en este paso. La decisión de imputar o mapear a un municipio padre corresponde al modelo.",
        "",
        "## Validaciones",
        "",
        "- Se conservaron todas las filas y el orden de las tablas canónicas.",
        "- Las columnas originales y las dos columnas de respuesta (`conocidos_objetivo` y",
        "  `abstencion_objetivo`) no cambiaron. En 2027 la respuesta sigue vacía.",
        "- La llave `EDOCVE + MPIOCVE` de las fuentes externas es única.",
        "- Ningún `censo_fuente` es posterior a `eleccion_objetivo`.",
        "- Los valores negativos de la fuente se trataron como faltantes y no se sumaron.",
        "- Se corrigió la escala de `GRAPROES` en Chiapas y se descartaron valores mayores a 30 años.",
    ]
    if avisos:
        lineas += ["", "Avisos de rango (revisar antes de modelar):", ""]
        lineas += [f"- {aviso}" for aviso in avisos]
    else:
        lineas += ["- Todas las tasas y porcentajes quedaron en [0, 1]."]

    lineas += [
        "",
        "## Censos Económicos",
        "",
        "No se usan. Los conjuntos de datos abiertos descargados (2024, 2014 y 2000) son solo",
        "nacionales: no traen desagregación municipal y no permiten el cruce por `EDOCVE + MPIOCVE`.",
        "",
        "## Archivos generados",
        "",
        f"- `{SALIDA_EXTERNOS.joinpath('eceg_2010_municipio.parquet').relative_to(RAIZ_REPO)}`",
        f"- `{SALIDA_EXTERNOS.joinpath('eceg_2020_municipio.parquet').relative_to(RAIZ_REPO)}`",
        f"- `{PROCESADOS.joinpath('tabla_municipios_entrenamiento.parquet').relative_to(RAIZ_REPO)}` y `.csv`",
        f"- `{PROCESADOS.joinpath('tabla_municipios_2027.parquet').relative_to(RAIZ_REPO)}` y `.csv`",
        "",
        "## Reproducir",
        "",
        "```bash",
        "python scripts/features_externas_municipio.py",
        "```",
        "",
        "`fase3.py` integra estas mismas features cuando se corre el pipeline completo. Este",
        "script es idempotente: si las tablas ya tienen las columnas `ext_*`, las reemplaza.",
        "",
    ]
    REPORTE.parent.mkdir(parents=True, exist_ok=True)
    REPORTE.write_text("\n".join(lineas), encoding="utf-8")


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()

    print("Cargando agregados externos...")
    ext2010, ext2020 = cargar_o_construir_agregados()
    print(f"  2010: {len(ext2010):,} municipios | 2020: {len(ext2020):,} municipios")

    resumenes, sin_dato, avisos = [], {}, []
    for nombre, ruta in TABLAS.items():
        print(f"Actualizando {ruta.name}...")
        original = pd.read_parquet(ruta.with_suffix(".parquet"))
        base = original.drop(columns=[c for c in COLUMNAS_EXTERNAS if c in original.columns])
        salida = unir_externos(base, ext2010, ext2020)
        avisos += [f"{nombre}: {aviso}" for aviso in validar_externos(base, salida)]
        salida = ordenar(salida, list(base.columns))
        flotantes = salida.select_dtypes("float").columns
        salida[flotantes] = salida[flotantes].round(6)

        guardar(salida, ruta.with_suffix(".parquet"))
        guardar(salida, ruta.with_suffix(".csv"))
        resumen, faltantes = cobertura(nombre, salida)
        resumenes.append(resumen)
        sin_dato.update(faltantes)
        print(f"  {len(salida):,} filas x {len(salida.columns)} columnas -> {ruta.name}.parquet y .csv")

    escribir_reporte(pd.concat(resumenes, ignore_index=True), sin_dato, avisos)
    print(f"Reporte: {REPORTE.relative_to(RAIZ_REPO)}")

    if avisos:
        print("\nAvisos de rango:")
        for aviso in avisos:
            print(f"  - {aviso}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
