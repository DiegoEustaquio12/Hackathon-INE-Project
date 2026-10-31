"""Genera el entregable "Mapa de escenarios con y sin intervención" y su base de datos.

Uso (desde la raíz del proyecto):
    python ai/src/geo/entregable_mapa.py

Salida en docs/deliverables/mapa_escenarios/:
  - mapa_escenarios.gpkg            capas del mapa 1 (sin) y mapa 2 (con, una por grupo), estados y tabla de detalle;
                                    trae los estilos del semáforo dentro, así QGIS lo abre ya coloreado
  - escenarios_municipios.geojson   una capa con todos los campos, para cualquier herramienta
  - comparacion_sin_con.pdf / _<grupo>.png   mapas 1 y 2 lado a lado
  - base_datos_escenarios.xlsx      Léeme, escenarios, detalle y diccionario
  - escenarios_municipios.csv, escenarios_detalle.csv, base_modelo_*.csv, diccionario_datos.csv
  - GUIA_DEL_ENTREGABLE.md y verificacion.txt (los números de ambos salen de este script)

No recalcula nada: empaqueta los resultados del equipo (web/escenarios_*.csv, ai/artifacts/predicciones_2027.csv)
y comprueba que coincidan con lo que muestra el visor (web/escenarios.json).
"""
import datetime
import json
import re
import shutil
import sqlite3
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyogrio  # noqa: E402
import shapely  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]
SALIDA = RAIZ / "docs/deliverables/mapa_escenarios"
FUENTES = {
    "municipio": RAIZ / "web/escenarios_municipio.csv",
    "detalle": RAIZ / "web/escenarios_detalle.csv",
    "predicciones": RAIZ / "ai/artifacts/predicciones_2027.csv",
    "equivalencias": RAIZ / "web/equivalencias_municipios.csv",
    "visor": RAIZ / "web/escenarios.json",
    "poligonos": RAIZ / "data/external/mun22gw_c/mun22cw.shp",
    "entrenamiento": RAIZ / "data/processed/tabla_municipios_entrenamiento.csv",
    "base_2027": RAIZ / "data/processed/tabla_municipios_2027.csv",
    "diccionario_equipo": RAIZ / "docs/reports/diccionario_datos.md",
}
GRUPOS = {"jovenes": "Jóvenes (18–34)", "hombres": "Hombres", "rural": "Zonas rurales"}
EFECTO_BASE = 10
# misma paleta que el visor (web/js/estado.js), probada contra daltonismo
COLOR = {"rojo": "#a51f2a", "amarillo": "#f2c230", "verde": "#6dbaa0", "sin_clasificar": "#cfcfcf"}
ORDEN_SEMAFORO = ["rojo", "amarillo", "verde", "sin_clasificar"]
# claves INE sin pareja en la tabla de equivalencias; se confirman con el nombre del polígono antes de usarlas
CORRECCIONES = {"20316": ("20318", "DTO. 22"), "20317": ("20319", "DTO. 26")}
SIN_POLIGONO_ESPERADO = {"25019": "Eldorado", "25020": "Juan José Ríos"}  # creados en 2021, cartografía de 2022
TOLERANCIA_M = 200  # simplificación de bordes en metros: invisible a escala estatal y deja el GPKG ~6 veces más ligero
SI_NO = {True: "sí", False: "no"}


class ErrorEntregable(SystemExit):
    pass


def comprobar(condicion, mensaje):
    if not condicion:
        raise ErrorEntregable(f"ERROR: {mensaje}")


def clave_ine(df):
    return df["EDOCVE"].astype(int).astype(str).str.zfill(2) + df["MPIOCVE"].astype(int).astype(str).str.zfill(3)


def leer_csv(ruta, **kw):
    return pd.read_csv(ruta, encoding="utf-8-sig", **kw)


# ---------------------------------------------------------------- datos
def cargar():
    for nombre, ruta in FUENTES.items():
        comprobar(ruta.exists(), f"falta {nombre}: {ruta.relative_to(RAIZ)}")
    m = leer_csv(FUENTES["municipio"])
    d = leer_csv(FUENTES["detalle"])
    p = leer_csv(FUENTES["predicciones"])
    e = pd.read_csv(FUENTES["equivalencias"], dtype=str)[["clave_ine", "clave_inegi"]]
    for df in (m, d, p):
        df["clave_ine"] = clave_ine(df)
    comprobar(not m["clave_ine"].duplicated().any(), "municipios repetidos en escenarios_municipio.csv")
    comprobar(not p["clave_ine"].duplicated().any(), "municipios repetidos en predicciones_2027.csv")
    poli = gpd.read_file(FUENTES["poligonos"])
    return m, d, p, e, poli


def equivalencias(e, m, poli):
    """Tabla INE -> INEGI con las correcciones confirmadas por el nombre del polígono."""
    e = e.copy()
    nombres_poli = poli.set_index("CVEGEO")["NOMGEO"]
    nombres_ine = m.set_index("clave_ine")["nombre_municipio"]
    corregidas = []
    for ine, (inegi, distrito) in CORRECCIONES.items():
        comprobar(distrito in str(nombres_poli.get(inegi, "")).upper(), f"el polígono {inegi} no es {distrito}")
        comprobar(distrito.split()[-1] in str(nombres_ine.get(ine, "")), f"la clave INE {ine} no es {distrito}")
        actual = e.loc[e["clave_ine"] == ine, "clave_inegi"]
        if actual.isna().all():
            comprobar(inegi not in set(e["clave_inegi"].dropna()), f"{inegi} ya está asignado a otro municipio")
            e.loc[e["clave_ine"] == ine, "clave_inegi"] = inegi
        else:
            comprobar((actual == inegi).all(), f"{ine} ya apunta a otra clave INEGI")
        corregidas.append(f"{ine} -> {inegi}")
    comprobar(not e["clave_inegi"].dropna().duplicated().any(), "claves INEGI repetidas en las equivalencias")
    return e, corregidas


def tabla_municipios(m, d, p, e, poli):
    """Una fila por municipio con el escenario sin intervención y los tres con intervención (efecto base)."""
    nombre_edo = poli.drop_duplicates("CVE_ENT").set_index("CVE_ENT")["NOM_ENT"]
    w = m.merge(e, on="clave_ine", how="left").merge(
        p[["clave_ine", "brecha_intermedia_presidencial", "razon_1", "razon_2", "razon_3", "sin_censo"]],
        on="clave_ine", how="left", validate="1:1")
    t = pd.DataFrame({
        "clave_ine": w["clave_ine"],
        "edocve": w["EDOCVE"].astype(int),
        "mpiocve": w["MPIOCVE"].astype(int),
        "clave_inegi": w["clave_inegi"],
        "estado": w["clave_ine"].str[:2].map(nombre_edo),
        "municipio": w["nombre_municipio"],
        "tiene_poligono": w["clave_inegi"].isin(set(poli["CVEGEO"])).map(SI_NO),
        "lista_nominal": w["ln_ultima"].round().astype("Int64"),
        "abst_sin_pct": (w["abstencion_pred"] * 100).round(2),
        "abst_sin_min_pct": (w["abstencion_min"] * 100).round(2),
        "abst_sin_max_pct": (w["abstencion_max"] * 100).round(2),
        "semaforo_sin": w["color_sin"],
    })
    base = d[d["efecto_pct"] == EFECTO_BASE].set_index(["clave_ine", "intervencion"])
    for g in GRUPOS:
        b = base.xs(g, level="intervencion").reindex(t["clave_ine"])
        comprobar(b.index.notna().all() and len(b) == len(t), f"faltan escenarios de {g}")
        b = b.reset_index(drop=True)
        t[f"abst_con_{g}_pct"] = (b["abstencion_con"] * 100).round(2)
        t[f"semaforo_con_{g}"] = b["color_con"]
        t[f"baja_{g}_pts"] = b["reduccion_pts"].round(2)
        t[f"personas_{g}"] = (b["reduccion_pts"] / 100 * w["ln_ultima"]).round().astype("Int64")
        t[f"cambia_color_{g}"] = b["cambio_color"].astype(bool).map(SI_NO)
        t[f"grupo_imputado_{g}"] = b["grupo_imputado"].astype(bool).map(SI_NO)
    t["brecha_interm_pres_pts"] = (w["brecha_intermedia_presidencial"] * 100).round(2)
    for r in ("razon_1", "razon_2", "razon_3"):
        t[r] = w[r]
    t["pocos_casos"] = w["pocos_casos"].fillna(False).astype(bool).map(SI_NO)
    t["ns_alto"] = w["ns_alto"].fillna(False).astype(bool).map(SI_NO)
    t["sin_censo"] = w["sin_censo"].fillna(False).astype(bool).map(SI_NO)
    t["efecto_supuesto_pct"] = EFECTO_BASE
    t["escenario_hipotetico"] = "sí"
    return t.sort_values("clave_ine").reset_index(drop=True)


def tabla_detalle(d, t):
    """Los 9 escenarios (3 grupos x 3 efectos) por municipio."""
    ln = t.set_index("clave_ine")["lista_nominal"].astype(float)
    x = d.merge(t[["clave_ine", "clave_inegi", "estado", "municipio"]], on="clave_ine", how="left")
    det = pd.DataFrame({
        "clave_ine": x["clave_ine"],
        "clave_inegi": x["clave_inegi"],
        "estado": x["estado"],
        "municipio": x["municipio"],
        "intervencion": x["intervencion"],
        "efecto_supuesto_pct": x["efecto_pct"].astype(int),
        "aplica": x["aplica"].astype(bool).map(SI_NO),
        "grupo_pct_lista": x["grupo_pct_lista"].round(2),
        "abst_grupo_pct": x["abst_grupo"].round(2),
        "grupo_imputado": x["grupo_imputado"].astype(bool).map(SI_NO),
        "abst_sin_pct": (x["abstencion_sin"] * 100).round(2),
        "abst_con_pct": (x["abstencion_con"] * 100).round(2),
        "baja_pts": x["reduccion_pts"].round(2),
        "personas": (x["reduccion_pts"] / 100 * x["clave_ine"].map(ln)).round().astype("Int64"),
        "semaforo_sin": x["color_sin"],
        "semaforo_con": x["color_con"],
        "cambia_color": x["cambio_color"].astype(bool).map(SI_NO),
    })
    orden = {g: i for i, g in enumerate(GRUPOS)}
    return det.sort_values(["clave_ine", "intervencion", "efecto_supuesto_pct"],
                           key=lambda s: s.map(orden) if s.name == "intervencion" else s).reset_index(drop=True)


# ---------------------------------------------------------------- geometría
def geometrias(poli):
    """Simplifica respetando los bordes compartidos y pasa a latitud/longitud (EPSG:4326)."""
    poli = poli[["CVEGEO", "CVE_ENT", "geometry"]].copy()
    poli["geometry"] = shapely.make_valid(poli.geometry.values)
    try:
        simple = shapely.coverage_simplify(poli.geometry.values, TOLERANCIA_M)
    except Exception:  # cobertura con traslapes: simplificación por polígono
        simple = shapely.simplify(poli.geometry.values, TOLERANCIA_M, preserve_topology=True)
    poli["geometry"] = shapely.make_valid(simple)
    estados = poli.dissolve(by="CVE_ENT", as_index=False)[["CVE_ENT", "geometry"]]
    salida = []
    for g in (poli, estados):
        g = g.to_crs(4326)
        g["geometry"] = shapely.make_valid(shapely.set_precision(g.geometry.values, 1e-5))
        salida.append(g)
    return salida


# ---------------------------------------------------------------- estilos QGIS
def _simbolo(n, relleno, borde, ancho, sin_relleno=False):
    opt = lambda k, v: f'<Option name="{k}" type="QString" value="{v}"/>'  # noqa: E731
    rgb = lambda h: ",".join(str(int(h[i:i + 2], 16)) for i in (1, 3, 5)) + ",255"  # noqa: E731
    return (f'<symbol type="fill" name="{n}" alpha="1" clip_to_extent="1" force_rhr="0">'
            f'<layer class="SimpleFill" enabled="1" pass="0" locked="0"><Option type="Map">'
            f'{opt("color", rgb(relleno))}{opt("style", "no" if sin_relleno else "solid")}'
            f'{opt("outline_color", rgb(borde))}{opt("outline_style", "solid")}'
            f'{opt("outline_width", ancho)}{opt("outline_width_unit", "MM")}{opt("joinstyle", "round")}'
            f'</Option></layer></symbol>')


def qml_semaforo(campo, etiquetas, campo_cambio=None):
    reglas, simbolos = [], []
    for i, valor in enumerate(ORDEN_SEMAFORO):
        filtro = f"&quot;{campo}&quot; = '{valor}'"
        reglas.append(f'<rule key="r{i}" filter="{filtro}" symbol="{i}" label="{etiquetas[valor]}"/>')
        simbolos.append(_simbolo(i, COLOR[valor], "#ffffff", "0.06"))
    if campo_cambio:
        i = len(ORDEN_SEMAFORO)
        reglas.append(f'<rule key="r{i}" filter="&quot;{campo_cambio}&quot; = \'sí\'" symbol="{i}" '
                      f'label="Cambia de color con la intervención"/>')
        simbolos.append(_simbolo(i, "#ffffff", "#0b1220", "0.35", sin_relleno=True))
    return ("<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
            '<qgis version="3.34.0" styleCategories="Symbology">'
            '<renderer-v2 type="RuleRenderer" symbollevels="0" enableorderby="0" forceraster="0">'
            f'<rules key="raiz">{"".join(reglas)}</rules><symbols>{"".join(simbolos)}</symbols>'
            '</renderer-v2></qgis>')


def qml_estados():
    return ("<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>"
            '<qgis version="3.34.0" styleCategories="Symbology">'
            '<renderer-v2 type="singleSymbol" symbollevels="0" enableorderby="0" forceraster="0">'
            f'<symbols>{_simbolo(0, "#ffffff", "#334155", "0.3", sin_relleno=True)}</symbols>'
            '</renderer-v2></qgis>')


def guardar_estilos(gpkg, estilos):
    """Tabla layer_styles: QGIS aplica el estilo marcado useAsDefault al abrir cada capa."""
    con = sqlite3.connect(gpkg)
    con.execute("""CREATE TABLE IF NOT EXISTS layer_styles (
        id INTEGER PRIMARY KEY AUTOINCREMENT, f_table_catalog TEXT(256), f_table_schema TEXT(256),
        f_table_name TEXT(256), f_geometry_column TEXT(256), styleName TEXT(30), styleQML TEXT,
        styleSLD TEXT, useAsDefault BOOLEAN, description TEXT, owner TEXT(30), ui TEXT(30), update_time DATETIME)""")
    con.execute("DELETE FROM layer_styles")
    for capa, (nombre, qml) in estilos.items():
        con.execute("INSERT INTO layer_styles (f_table_catalog, f_table_schema, f_table_name, f_geometry_column, "
                    "styleName, styleQML, styleSLD, useAsDefault, description, owner, ui, update_time) "
                    "VALUES ('', '', ?, 'geom', ?, ?, '', 1, ?, '', '', '2026-10-31T00:00:00Z')",
                    (capa, nombre, qml, nombre))
    con.execute("INSERT OR IGNORE INTO gpkg_contents (table_name, data_type, identifier, description, last_change) "
                "VALUES ('layer_styles', 'attributes', 'layer_styles', 'Estilos de QGIS', '2026-10-31T00:00:00Z')")
    con.commit()
    con.close()


# ---------------------------------------------------------------- figuras
def etiquetas_semaforo(cortes):
    am, ro = cortes
    return {"rojo": f"Alta: {ro:.0f}% o más", "amarillo": f"Media: {am:.0f}% a {ro:.0f}%",
            "verde": f"Baja: menos de {am:.0f}%", "sin_clasificar": "Sin dato"}


def figura(mapa_lcc, estados_lcc, campo_con, g, cortes, fecha):
    fig, ejes = plt.subplots(1, 2, figsize=(16, 7.6))
    fig.patch.set_facecolor("white")
    etiq = etiquetas_semaforo(cortes)
    for ax, campo, titulo in ((ejes[0], "semaforo_sin", "Mapa 1 · Sin intervención"),
                              (ejes[1], campo_con, f"Mapa 2 · Con intervención: {GRUPOS[g]}")):
        mapa_lcc.plot(ax=ax, color=mapa_lcc[campo].map(COLOR), edgecolor="white", linewidth=0.05, rasterized=True)
        estados_lcc.boundary.plot(ax=ax, color="#334155", linewidth=0.35)
        if campo == campo_con:
            cambia = mapa_lcc[mapa_lcc[f"cambia_color_{g}"] == "sí"]
            cambia.boundary.plot(ax=ax, color="#0b1220", linewidth=0.6)
        ax.set_title(titulo, fontsize=15, fontweight="bold", loc="left")
        ax.set_axis_off()
        cuenta = mapa_lcc[campo].value_counts()
        ax.legend(handles=[Patch(facecolor=COLOR[v], edgecolor="#94a3b8",
                                 label=f"{etiq[v]} ({cuenta.get(v, 0):,})") for v in ORDEN_SEMAFORO]
                  + ([Patch(facecolor="white", edgecolor="#0b1220", linewidth=1.2,
                            label="Cambia de color con la intervención")] if campo == campo_con else []),
                  loc="lower left", fontsize=10, frameon=True, title="Abstención prevista 2027 (municipios)", title_fontsize=11)
    fig.suptitle("Abstención 2027 por municipio: sin y con intervención", fontsize=20, fontweight="bold", x=0.02,
                 ha="left", y=0.975)
    fig.text(0.02, 0.895, f"Porcentaje de la lista nominal que no votaría en 2027. Intervención hipotética: "
             f"{GRUPOS[g]}, efecto supuesto de {EFECTO_BASE}% en los municipios en rojo. Mismos cortes en ambos mapas.",
             fontsize=11.5, color="#475569")
    fig.text(0.02, 0.03, f"Datos: CCPC INE 2009–2024 · Polígonos: INEGI 2022 (CONABIO) · Predicción del equipo · "
             f"{fecha}. La intervención es un supuesto, no una medición. Eldorado y Juan José Ríos (Sinaloa, creados en 2021) "
             "no tienen polígono propio.", fontsize=9.5, color="#475569")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.84, bottom=0.08, wspace=0.03)
    return fig


# ---------------------------------------------------------------- diccionario
def diccionario(t, det):
    D = {
        "clave_ine": ("Clave del municipio según el INE: estado (2 dígitos) + municipio (3 dígitos)", "", "CCPC INE"),
        "edocve": ("Número del estado según el INE (1 a 32)", "", "CCPC INE"),
        "mpiocve": ("Número del municipio dentro de su estado según el INE (no es la clave del INEGI)", "", "CCPC INE"),
        "clave_inegi": ("Clave del municipio según el INEGI (CVEGEO), la que usan los polígonos", "", "INEGI 2022"),
        "estado": ("Nombre del estado", "", "INEGI 2022"),
        "municipio": ("Nombre del municipio", "", "CCPC INE"),
        "tiene_poligono": ("Si el municipio tiene contorno en el mapa (Eldorado y Juan José Ríos no: se crearon "
                           "en 2021)", "sí/no", "Equipo"),
        "lista_nominal": ("Personas en la lista nominal en la última elección (2024)", "personas", "CCPC INE"),
        "abst_sin_pct": ("Abstención prevista para 2027 si nada cambia", "% de la lista nominal", "Modelo del equipo"),
        "abst_sin_min_pct": ("Límite inferior del rango probable de la abstención prevista", "%", "Modelo del equipo"),
        "abst_sin_max_pct": ("Límite superior del rango probable de la abstención prevista", "%", "Modelo del equipo"),
        "semaforo_sin": ("Color del semáforo sin intervención (terciles del país)", "rojo/amarillo/verde/sin_clasificar",
                         "Equipo"),
        "brecha_interm_pres_pts": ("Cuántos puntos más se abstiene en elecciones intermedias que en presidenciales",
                                   "puntos", "CCPC INE"),
        "razon_1": ("Principal razón del modelo para su predicción (con su efecto en puntos)", "", "Modelo del equipo"),
        "razon_2": ("Segunda razón del modelo", "", "Modelo del equipo"),
        "razon_3": ("Tercera razón del modelo", "", "Modelo del equipo"),
        "pocos_casos": ("Dato poco confiable: hay pocas personas con dato de si votaron o no", "sí/no", "Equipo"),
        "ns_alto": ("Dato poco confiable: de muchas personas no se sabe si votaron", "sí/no", "Equipo"),
        "sin_censo": ("No hay datos del censo del INEGI para el municipio", "sí/no", "Equipo"),
        "efecto_supuesto_pct": ("Efecto supuesto de la intervención: % de quienes no votan en el grupo que sí votaría",
                                "%", "Supuesto del equipo"),
        "escenario_hipotetico": ("Recordatorio: el escenario con intervención es un supuesto, no una medición",
                                 "sí", "Equipo"),
    }
    for g, nombre in GRUPOS.items():
        D[f"abst_con_{g}_pct"] = (f"Abstención prevista con la intervención en {nombre}", "%", "Escenario del equipo")
        D[f"semaforo_con_{g}"] = (f"Color del semáforo con la intervención en {nombre} (mismos cortes)",
                                  "rojo/amarillo/verde/sin_clasificar", "Escenario del equipo")
        D[f"baja_{g}_pts"] = (f"Cuánto baja la abstención con la intervención en {nombre}", "puntos",
                              "Escenario del equipo")
        D[f"personas_{g}"] = (f"Personas más que votarían con la intervención en {nombre} (aprox.)", "personas",
                              "Escenario del equipo")
        D[f"cambia_color_{g}"] = (f"Si el municipio cambia de color con la intervención en {nombre}", "sí/no",
                                  "Escenario del equipo")
        D[f"grupo_imputado_{g}"] = (f"El tamaño del grupo {nombre} se estimó porque faltaba el dato", "sí/no",
                                    "Equipo")
    Ddet = {
        "intervencion": ("Grupo al que se dirige la intervención: jovenes, hombres o rural", "", "Escenario del equipo"),
        "aplica": ("Si la intervención se aplica (solo municipios en rojo)", "sí/no", "Escenario del equipo"),
        "grupo_pct_lista": ("Parte de la lista nominal que pertenece al grupo", "%", "CCPC INE"),
        "abst_grupo_pct": ("Abstención del grupo en la última elección comparable", "%", "CCPC INE"),
        "grupo_imputado": ("El tamaño del grupo se estimó porque faltaba el dato", "sí/no", "Equipo"),
        "abst_con_pct": ("Abstención prevista con la intervención", "%", "Escenario del equipo"),
        "baja_pts": ("Cuánto baja la abstención con la intervención", "puntos", "Escenario del equipo"),
        "personas": ("Personas más que votarían (aprox.)", "personas", "Escenario del equipo"),
        "semaforo_con": ("Color del semáforo con la intervención", "rojo/amarillo/verde/sin_clasificar",
                         "Escenario del equipo"),
        "cambia_color": ("Si cambia de color con la intervención", "sí/no", "Escenario del equipo"),
    }
    filas = [("escenarios_municipios", c, *D[c]) for c in t.columns]
    filas += [("escenarios_detalle", c, *(Ddet.get(c) or D[c])) for c in det.columns]
    # columnas de la base del modelo: se toman del diccionario del equipo (docs/reports/diccionario_datos.md)
    texto = FUENTES["diccionario_equipo"].read_text(encoding="utf-8")
    desc_equipo = {}
    for col, desc in re.findall(r"^\| `([^`]+)` \| ([^|]+) \|", texto, flags=re.M):
        desc_equipo.setdefault(col, desc.strip())
    for archivo, ruta in (("base_modelo_entrenamiento", FUENTES["entrenamiento"]), ("base_modelo_2027", FUENTES["base_2027"])):
        for c in pd.read_csv(ruta, nrows=0).columns:
            filas.append((archivo, c, desc_equipo.get(c, "Ver docs/reports/diccionario_datos.md"), "", "Equipo (Fase 3)"))
    return pd.DataFrame(filas, columns=["archivo", "columna", "descripcion", "unidad", "fuente"])


# ---------------------------------------------------------------- textos
def leeme(v, cortes, fecha):
    am, ro = cortes
    return f"""# Mapa de escenarios con y sin intervención

Reto 2, Hackathon INE. Generado por `ai/src/geo/entregable_mapa.py` el {fecha}.

## Qué hay en esta carpeta

| Archivo | Qué es |
|---|---|
| `mapa_escenarios.gpkg` | **El mapa.** Capas `mapa_1_sin_intervencion`, `mapa_2_con_jovenes`, `mapa_2_con_hombres`, `mapa_2_con_rural`, `estados` y la tabla `escenarios_detalle`. Trae los colores del semáforo incluidos |
| `escenarios_municipios.geojson` | Los mismos datos en una sola capa, para cualquier programa (geojson.io, Power BI, Python) |
| `comparacion_sin_con.pdf` | Los mapas 1 y 2 lado a lado, una página por intervención |
| `comparacion_sin_con_<grupo>.png` | Lo mismo en imagen, una por intervención |
| `base_datos_escenarios.xlsx` | Resultados, detalle y diccionario en Excel |
| `escenarios_municipios.csv` | Una fila por municipio: sin intervención y las tres intervenciones con efecto de {EFECTO_BASE}% |
| `escenarios_detalle.csv` | Los 9 escenarios por municipio (3 grupos × efecto de 5, 10 y 15%) |
| `base_modelo_entrenamiento.csv`, `base_modelo_2027.csv` | Las tablas municipales con las que se entrenó el modelo y se predijo 2027 |
| `diccionario_datos.csv` | Qué significa cada columna de cada archivo |
| `verificacion.txt` | Las comprobaciones que hizo el script |

## Cómo abrir el mapa en QGIS (3 pasos)

1. Arrastra `mapa_escenarios.gpkg` a QGIS (o *Capa → Añadir capa → Vectorial*).
2. Elige las capas `mapa_1_sin_intervencion` y una `mapa_2_con_...`. Aparecen ya coloreadas.
3. Enciende y apaga las capas para comparar. La capa `estados` ayuda a ubicarse.

En ArcGIS o en otros programas el color se arma con el campo `semaforo_sin` o `semaforo_con_<grupo>`.

## Cómo leerlo

- **Qué se predice:** el porcentaje de la lista nominal que no votaría en la elección intermedia de 2027.
- **Semáforo:** terciles del escenario sin intervención. Rojo (alta): {ro:.2f}% o más. Amarillo (media): {am:.2f}% a {ro:.2f}%. Verde (baja): menos de {am:.2f}%. Los mismos cortes se usan con intervención, para que los colores se puedan comparar.
- **Intervención:** hipotética. Se aplica solo en municipios en rojo y supone que una parte ({EFECTO_BASE}% en el caso base) de quienes no votan en el grupo elegido sí vota. **Su efecto es un supuesto, no una medición.**
- **Puntos:** diferencia entre dos porcentajes. 1 punto = 1 de cada 100 personas de la lista nominal.

## Cobertura

- Municipios con datos: {v['municipios']:,}. Con polígono: {v['con_poligono']:,}.
- Sin polígono: {', '.join(v['sin_poligono'])}. Se crearon en 2021 y la cartografía es de 2022; su territorio aparece dentro de los municipios de los que salieron. Sus datos están en los CSV y en el Excel.
- Se corrigió la pareja de claves de San Pedro Mixtepec (Oaxaca): {', '.join(v['correcciones'])} (INE → INEGI), confirmada con el nombre del polígono (-DTO. 22- y -DTO. 26-).

## Datos anonimizados

Todo está agregado por municipio: conteos y porcentajes. No hay datos de personas ni de secciones electorales.

## Fuentes

- Conteos Censales de Participación Ciudadana (CCPC) del INE, 2009–2024.
- Censo de Población y Vivienda (ECEG) del INEGI, 2010 y 2020, como variables del modelo.
- Polígonos: división política municipal 2022 del INEGI, publicada por CONABIO (acceso libre), simplificados a {TOLERANCIA_M} m sin abrir huecos entre municipios. Coordenadas en EPSG:4326.
"""


# ---------------------------------------------------------------- principal
def main():
    SALIDA.mkdir(parents=True, exist_ok=True)
    fecha = datetime.date.today().strftime("%d/%m/%Y")
    m, d, p, e, poli = cargar()
    e, correcciones = equivalencias(e, m, poli)
    t = tabla_municipios(m, d, p, e, poli)
    det = tabla_detalle(d, t)
    cortes = (round(float(m["corte_amarillo_pct"].dropna().iloc[0]), 2), round(float(m["corte_rojo_pct"].dropna().iloc[0]), 2))

    # --- comprobaciones de datos
    v = {"municipios": len(t), "correcciones": correcciones}
    comprobar(len(t) == 2477 and not t["clave_ine"].duplicated().any(), f"se esperaban 2,477 municipios únicos, hay {len(t)}")
    comprobar(t["estado"].notna().all(), "municipios sin nombre de estado")
    sin_pol = t[t["tiene_poligono"] == "no"]
    comprobar(dict(zip(sin_pol["clave_ine"], sin_pol["municipio"])) == SIN_POLIGONO_ESPERADO,
              f"municipios sin polígono inesperados: {dict(zip(sin_pol['clave_ine'], sin_pol['municipio']))}")
    v["sin_poligono"] = [f"{n} (Sinaloa)" for n in SIN_POLIGONO_ESPERADO.values()]
    comprobar((t["semaforo_sin"].value_counts() == m["color_sin"].value_counts()).all(), "conteos del semáforo distintos")
    visor = json.loads(FUENTES["visor"].read_text(encoding="utf-8"))["meta"]["totales"]
    ln = m.set_index("clave_ine")["ln_ultima"]
    totales = {}
    for g in GRUPOS:
        q = d[(d["intervencion"] == g) & (d["efecto_pct"] == EFECTO_BASE)]
        personas = float((q["reduccion_pts"] / 100 * q["clave_ine"].map(ln)).sum())
        comprobar(abs(round(personas) - visor[g][str(EFECTO_BASE)]["personas"]) <= 1, f"total nacional de {g} distinto al visor")
        totales[g] = round(personas)

    # --- geometría y capas
    mun, edos = geometrias(poli)
    comprobar(len(mun) == 2475 and set(mun["CVEGEO"]) <= set(t["clave_inegi"].dropna()), "polígonos sin datos")
    comprobar(shapely.is_valid(mun.geometry.values).all() and shapely.is_valid(edos.geometry.values).all(),
              "geometrías inválidas")
    mapa = mun[["CVEGEO", "geometry"]].merge(t[t["clave_inegi"].notna()], left_on="CVEGEO", right_on="clave_inegi",
                                              validate="1:1").drop(columns="CVEGEO")
    mapa = gpd.GeoDataFrame(mapa, geometry="geometry", crs=4326).sort_values("clave_ine").reset_index(drop=True)
    mapa = mapa[[*t.columns, "geometry"]]
    v["con_poligono"] = len(mapa)

    gpkg = SALIDA / "mapa_escenarios.gpkg"
    gpkg.unlink(missing_ok=True)
    capas = {"mapa_1_sin_intervencion": "semaforo_sin", **{f"mapa_2_con_{g}": f"semaforo_con_{g}" for g in GRUPOS}}
    for capa in capas:
        pyogrio.write_dataframe(mapa, gpkg, layer=capa, driver="GPKG", geometry_type="MultiPolygon", promote_to_multi=True)
    edos_capa = edos.rename(columns={"CVE_ENT": "clave_estado"})
    edos_capa["estado"] = edos_capa["clave_estado"].map(poli.drop_duplicates("CVE_ENT").set_index("CVE_ENT")["NOM_ENT"])
    pyogrio.write_dataframe(edos_capa, gpkg, layer="estados", driver="GPKG", geometry_type="MultiPolygon", promote_to_multi=True)
    pyogrio.write_dataframe(det, gpkg, layer="escenarios_detalle", driver="GPKG")
    etiq = etiquetas_semaforo(cortes)
    estilos = {"mapa_1_sin_intervencion": ("Semáforo sin intervención", qml_semaforo("semaforo_sin", etiq))}
    for g, nombre in GRUPOS.items():
        estilos[f"mapa_2_con_{g}"] = (f"Semáforo con intervención: {nombre}",
                                      qml_semaforo(f"semaforo_con_{g}", etiq, f"cambia_color_{g}"))
    estilos["estados"] = ("Límites estatales", qml_estados())
    guardar_estilos(gpkg, estilos)

    geojson = SALIDA / "escenarios_municipios.geojson"
    geojson.unlink(missing_ok=True)
    pyogrio.write_dataframe(mapa, geojson, driver="GeoJSON", layer_options={"COORDINATE_PRECISION": 5, "RFC7946": "YES"})

    # --- tablas
    t.to_csv(SALIDA / "escenarios_municipios.csv", index=False, encoding="utf-8-sig")
    det.to_csv(SALIDA / "escenarios_detalle.csv", index=False, encoding="utf-8-sig")
    shutil.copyfile(FUENTES["entrenamiento"], SALIDA / "base_modelo_entrenamiento.csv")
    shutil.copyfile(FUENTES["base_2027"], SALIDA / "base_modelo_2027.csv")
    dic = diccionario(t, det)
    dic.to_csv(SALIDA / "diccionario_datos.csv", index=False, encoding="utf-8-sig")
    texto_leeme = leeme(v, cortes, fecha)
    (SALIDA / "GUIA_DEL_ENTREGABLE.md").write_text(texto_leeme, encoding="utf-8")
    with pd.ExcelWriter(SALIDA / "base_datos_escenarios.xlsx", engine="openpyxl") as xw:
        lineas = [l.replace("**", "").replace("`", "") for l in texto_leeme.splitlines()]
        pd.DataFrame({"Léeme": lineas}).to_excel(xw, sheet_name="Léeme", index=False)
        t.to_excel(xw, sheet_name="escenarios_municipios", index=False)
        det.to_excel(xw, sheet_name="escenarios_detalle", index=False)
        dic.to_excel(xw, sheet_name="diccionario", index=False)
        for nombre, hoja in xw.sheets.items():
            hoja.freeze_panes = "A2"
            for col in hoja.columns:
                largo = max(len(str(c.value or "")) for c in col[:200])
                hoja.column_dimensions[col[0].column_letter].width = min(90 if nombre == "Léeme" else 45, max(10, largo + 2))

    # --- figuras (en la proyección oficial EPSG:6372 se ven sin deformar)
    mapa_lcc, edos_lcc = mapa.to_crs(6372), edos.to_crs(6372)
    with PdfPages(SALIDA / "comparacion_sin_con.pdf") as pdf:
        for g in GRUPOS:
            fig = figura(mapa_lcc, edos_lcc, f"semaforo_con_{g}", g, cortes, fecha)
            fig.savefig(SALIDA / f"comparacion_sin_con_{g}.png", dpi=150)
            pdf.savefig(fig, dpi=200)  # los municipios van como imagen; textos y leyenda quedan en vector
            plt.close(fig)

    # --- relectura: lo escrito es igual a lo calculado
    rng = np.random.default_rng(0)
    capas_gpkg = {c for c, _ in pyogrio.list_layers(gpkg)}
    comprobar(capas_gpkg == {*capas, "estados", "escenarios_detalle", "layer_styles"}, f"capas inesperadas: {capas_gpkg}")
    cols = ["abst_sin_pct", "semaforo_sin", "abst_con_jovenes_pct", "personas_rural", "cambia_color_hombres"]
    for nombre, leido in (("GPKG", pyogrio.read_dataframe(gpkg, layer="mapa_1_sin_intervencion")),
                          ("GeoJSON", pyogrio.read_dataframe(geojson)),
                          ("XLSX", pd.read_excel(SALIDA / "base_datos_escenarios.xlsx", sheet_name="escenarios_municipios",
                                                 dtype={"clave_ine": str, "clave_inegi": str}))):
        esperado = t if nombre == "XLSX" else mapa
        comprobar(len(leido) == len(esperado), f"{nombre}: {len(leido)} filas, se esperaban {len(esperado)}")
        leido = leido.set_index("clave_ine")
        for clave in rng.choice(esperado["clave_ine"].to_numpy(), 20, replace=False):
            fila = esperado.set_index("clave_ine").loc[clave]
            for c in cols:
                a, b = fila[c], leido.loc[clave, c]
                igual = (abs(float(a) - float(b)) < 1e-6) if isinstance(a, (int, float, np.number)) else str(a) == str(b)
                comprobar(igual, f"{nombre}: {clave}.{c} = {b}, se esperaba {a}")
    con = sqlite3.connect(gpkg)
    n_estilos = con.execute("SELECT COUNT(*) FROM layer_styles WHERE useAsDefault = 1").fetchone()[0]
    con.close()
    comprobar(n_estilos == len(estilos), "faltan estilos en el GPKG")
    comprobar(pyogrio.read_info(gpkg, layer="mapa_1_sin_intervencion")["crs"] == "EPSG:4326", "CRS distinto de EPSG:4326")

    # --- reporte
    cuenta = t["semaforo_sin"].value_counts()
    tam = {f.name: f.stat().st_size for f in sorted(SALIDA.iterdir()) if f.is_file()}
    rep = [
        f"Verificación del entregable · {fecha}",
        f"Municipios con datos: {len(t):,} | con polígono: {len(mapa):,} | sin polígono: {', '.join(v['sin_poligono'])}",
        f"San Pedro Mixtepec, claves confirmadas con el polígono (INE -> INEGI): {', '.join(correcciones)}",
        "Semáforo sin intervención: " + ", ".join(f"{k} {cuenta.get(k, 0):,}" for k in ORDEN_SEMAFORO),
        f"Cortes: amarillo {cortes[0]}% | rojo {cortes[1]}% (terciles del escenario sin intervención)",
    ]
    for g in GRUPOS:
        cc = t[f"semaforo_con_{g}"].value_counts()
        rep.append(f"Con intervención {GRUPOS[g]} ({EFECTO_BASE}%): " + ", ".join(f"{k} {cc.get(k, 0):,}" for k in ORDEN_SEMAFORO)
                   + f" | cambian de color {int((t[f'cambia_color_{g}'] == 'sí').sum()):,} | ≈ {totales[g]:,} personas más votarían"
                   " (igual al visor)")
    rep += [f"Capas del GPKG: {', '.join(sorted(capas_gpkg))} | estilos: {n_estilos} | CRS EPSG:4326 | geometrías válidas",
            "Relectura GPKG, GeoJSON y XLSX: filas y 20 municipios al azar × 5 campos coinciden",
            "Archivos:"] + [f"  {n}: {b / 1e6:.1f} MB" for n, b in tam.items() if n != "verificacion.txt"]
    (SALIDA / "verificacion.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep))


if __name__ == "__main__":
    main()
