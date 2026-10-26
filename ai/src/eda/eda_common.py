"""Rutas, tablas y escritura del reporte compartidas por los EDA.

Los cálculos de cada pregunta viven en eda_p1.py … eda_p10.py. Cuando el
ejecutor los lanza en paralelo, cada proceso devuelve su sección en un archivo
temporal independiente; solo el ejecutor publica reporte_eda.md.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "docs/EDA"
REPORT = REPORT_DIR / "reporte_eda.md"
RESULTS = REPORT_DIR / "resultados"
MAP = ROOT / "data/external/cartografia/mun22gw/mun22gw.shp"
KEY = ["EDOCVE", "MPIOCVE"]
YEARS = [2009, 2012, 2015, 2018, 2021, 2024]
GROUPS = {
    "18_24": "18 a 24 años", "25_34": "25 a 34 años", "35_44": "35 a 44 años",
    "45_59": "45 a 59 años", "60_mas": "60 años o más", "mujeres": "Mujeres",
    "hombres": "Hombres", "urbana": "Secciones urbanas", "mixta": "Secciones mixtas",
    "rural": "Secciones rurales",
}

SUMMARIES = {
    1: ("La abstención municipal tiende a repetirse, pero el historial por sí solo tiene un error importante.",
        "El modelo debe superar la referencia de repetir la última elección del mismo tipo."),
    2: ("La abstención suele ser mayor en intermedias que en presidenciales; la diferencia varía por estado.",
        "Considerar el tipo de elección, el historial presidencial y un mapa de brecha."),
    3: ("El cambio nacional explica poco del error municipal y muchos municipios cambian de color.",
        "Evaluar un semáforo por orden y acompañar la predicción de un rango; decide la Fase 5."),
    4: ("Las personas de 25 a 34 años destacan por su abstención; los hombres superan a las mujeres.",
        "Priorizar el análisis por grupo sin asumir el efecto de una intervención."),
    5: ("Las características de la lista tienen relaciones débiles con la abstención; algunas aportan información repetida.",
        "Evaluar las variables entre elecciones y evitar duplicar información."),
    6: ("No aparece un mínimo de personas con dato que garantice estabilidad.",
        "Comparar distintos mínimos y medir cuántos municipios y personas se excluirían."),
    7: ("La información faltante varía entre municipios, estados y elecciones.",
        "Acompañar la abstención con su cobertura y evaluar distintos límites de NS."),
    8: ("Las secciones ausentes en 2012 afectan de forma desigual a los municipios.",
        "Identificar los municipios afectados y evaluar un historial alternativo sin 2012."),
    9: ("Los municipios con historial reconstruido presentan mayor error de referencia, pero son pocos casos.",
        "Evaluarlos por separado y excluir del entrenamiento las filas sin respuesta."),
    10: ("Los vecinos tienen tasas parecidas, incluso después de descontar el promedio estatal.",
         "Evaluar el modelo separando estados o bloques geográficos completos."),
}


def plotting():
    # Cada proceso usa un caché escribible. Las figuras tienen nombres distintos.
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "ine-eda-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    return plt


def save(df, name, out):
    df.to_csv(out / f"{name}.csv", index=False, float_format="%.8f")
    return df


def atomic_text(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sections_from_report(text):
    return {int(match.group(1)): match.group(0).strip()
            for match in re.finditer(r"^## Pregunta (\d+)\..*?(?=^## |\Z)", text, re.M | re.S)}


def write_report(sections, out=RESULTS):
    numbers = sorted(sections)
    state = "Respondidas las preguntas 1 a 10." if numbers == list(range(1, 11)) else "Respondidas: " + ", ".join(map(str, numbers)) + "."
    parts = ["# Reporte del análisis exploratorio (Fase 4)",
             "Aquí van las respuestas a las preguntas de la Fase 4 del plan. Cada una dice "
             "**qué encontramos**, **la cifra** y **qué decisión apoya**. Las decisiones son propuestas "
             "para la Fase 5. Este reporte se genera con `python scripts/ejecutar_eda.py`.",
             f"**Estado:** {state}",
             "**Cómo leerlo:** un punto es la diferencia entre dos porcentajes (de 40% a 45% son 5 puntos). "
             "Error es cuántos puntos se equivoca, en promedio, una predicción contra lo que de verdad pasó. "
             "Los porcentajes de abstención excluyen a quienes no tienen registro de si votaron.",
             "Salvo donde se indica un cálculo nacional por personas o una ponderación, cada municipio tiene el mismo peso."]
    summary = pd.DataFrame([
        {"#": number, "Respuesta en una línea": SUMMARIES[number][0], "Decisión que apoya": SUMMARIES[number][1]}
        for number in numbers
    ], columns=["#", "Respuesta en una línea", "Decisión que apoya"])
    parts.extend(["## Resumen", markdown(summary)])
    parts.extend(sections[n].strip() for n in numbers)
    display = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    parts.extend(["## Cómo repetirlo", "Desde la raíz del repositorio, con el entorno activado:",
                  "```bash\npython scripts/ejecutar_eda.py\n```",
                  "El ejecutor comprueba o descarga la cartografía y corre las diez preguntas en paralelo. "
                  "Solo publica este reporte si todos los procesos terminan correctamente. "
                  "Para ejecutar una pregunta individual y actualizar su sección:",
                  "```bash\npython ai/src/eda/eda_p4.py\npython ai/src/eda/eda_p10.py\n```",
                  f"Tablas, salidas de terminal y manifiestos de fuentes: `{display}/`. "
                  "Las figuras están en `docs/EDA/`. Cada sección indica el script que la genera. "
                  "La pregunta 4 requiere los seis archivos de la Fase 1 y la 8 requiere `data/interim/secciones.parquet`. "
                  "La cartografía se obtiene con `python scripts/descargar_cartografia_eda.py`. "
                  "No se modifican las tablas canónicas de `data/processed/`."])
    atomic_text(REPORT, "\n\n".join(parts) + "\n")


def record_sources(number, data, out, script, map_path):
    sources = [data / "municipio_eleccion.parquet", data / "tabla_municipios_entrenamiento.parquet",
               Path(script), Path(__file__)]
    if number == 4:
        sources += [ROOT / f"data/interim/ccpc/ccpc_{year}.parquet" for year in YEARS]
    if number in (6, 8):
        sources += [data / "catalogo_municipios.csv"]
    if number == 8:
        sources += [ROOT / "data/interim/secciones.parquet"]
    if number == 10:
        sources += [data / "tabla_municipios_2027.parquet"]
        sources += [map_path.with_suffix(ext) for ext in (".shp", ".shx", ".dbf", ".prj")]
        meta = map_path.parent / "fuente.json"
        if meta.exists():
            sources.append(meta)
    digests = {}
    for source in sources:
        with source.open("rb") as stream:
            key = str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source)
            digests[key] = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest = {"pregunta": number, "archivos": digests}
    if number == 10:
        manifest.update(semilla=20261025, permutaciones=999)
    atomic_text(out / f"fuentes_p{number}.json", json.dumps(manifest, indent=2) + "\n")


def run_question(number, analysis, script):
    parser = argparse.ArgumentParser(description=f"EDA: pregunta {number}.")
    parser.add_argument("datos", nargs="?", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--salida", type=Path, default=RESULTS, help="Carpeta de tablas y manifiestos")
    parser.add_argument("--fragmento", type=Path, help=argparse.SUPPRESS)
    if number == 10:
        parser.add_argument("--mapa", type=Path, default=MAP)
    args = parser.parse_args()
    data, out = args.datos.resolve(), args.salida.resolve()
    map_path = getattr(args, "mapa", MAP).resolve()
    out.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    # Se cargan en cada proceso para que ninguna pregunta dependa de otra.
    base = pd.read_parquet(data / "municipio_eleccion.parquet")
    train = pd.read_parquet(data / "tabla_municipios_entrenamiento.parquet")
    assert not base.duplicated([*KEY, "AELEC"]).any()
    assert not train.duplicated([*KEY, "eleccion_objetivo"]).any()
    extra = {"map_path": map_path} if number == 10 else {}
    # El catálogo de los análisis 6, 8 y 10 sigue la carpeta de datos seleccionada.
    if number in (6, 8, 10):
        extra["data_dir"] = data
    section = "\n\n".join(analysis(base, train, out, **extra))
    section += f"\n\nCódigo: `ai/src/eda/eda_p{number}.py`.\n"
    record_sources(number, data, out, script, map_path)
    if args.fragmento:
        atomic_text(args.fragmento, json.dumps({"pregunta": number, "seccion": section}, ensure_ascii=False) + "\n")
    else:
        sections = sections_from_report(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else {}
        sections[number] = section
        write_report(sections, out)
    print(section)
    print(f"\nPregunta {number} completada.", flush=True)


def markdown(df):
    df = df.rename(columns={
        "eleccion": "Elección", "AELEC": "Elección", "grupo": "Grupo", "periodo": "Periodo",
        "tamano": "Personas con dato", "municipios": "Municipios", "sin_respuesta": "Sin respuesta",
        "evaluables": "Comparables", "error_promedio_pp": "Error promedio (puntos)",
        "cambio_mediano_pp": "Cambio central (puntos)", "cambio_promedio_pp": "Cambio promedio (puntos)",
        "p90_pp": "90% cambia menos de (puntos)", "minimo": "Mínimo de personas",
        "municipios_excluidos": "Municipios excluidos", "personas_con_dato_excluidas": "Personas excluidas",
        "porcentaje_personas": "% de personas con dato", "sin_informacion_pct": "Sin información (%)",
        "abstencion_conocida_pct": "Abstención conocida (%)", "minimo_posible_pct": "Extremo menor (%)",
        "maximo_posible_pct": "Extremo mayor (%)", "nombre_estado": "Estado", "sin_dato": "Sin dato",
        "ns_mayor_10": "NS mayor de 10%", "ns_mayor_20": "NS mayor de 20%", "ns_mayor_50": "NS mayor de 50%",
        "conjunto": "Secciones consideradas", "secciones": "Secciones", "registrados": "Personas registradas",
        "abstencion_pct": "Abstención (%)", "hueco": "Parte ausente de 2012", "comparacion": "Comparación",
        "enlaces_dirigidos": "Contactos dirigidos", "relacion_con_promedio_vecinos": "Relación con vecinos",
        "indice_moran": "Índice de Moran", "probabilidad_permutacion": "Probabilidad al reordenar",
    })
    def fmt(x):
        if pd.isna(x):
            return "—"
        if isinstance(x, (float, np.floating)):
            if 0 < abs(x) < .01:
                return f"{x:.3f}"
            return f"{x:.2f}"
        return str(x).replace("|", "/")
    return "\n".join([
        "| " + " | ".join(map(str, df.columns)) + " |",
        "| " + " | ".join("---" for _ in df.columns) + " |",
        *("| " + " | ".join(map(fmt, row)) + " |" for row in df.itertuples(index=False, name=None)),
    ])
