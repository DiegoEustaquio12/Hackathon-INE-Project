"""Fase 3 del plan: tablas de municipios.

Arma tres tablas a partir de la tabla limpia de la Fase 1 y del catálogo de la Fase 2:

- municipio_eleccion: una fila por municipio y elección, con todo lo que pasó, tal como viene.
- tabla_municipios_entrenamiento: una fila por municipio y "foto" (2015, 2018, 2021 y 2024). Cada
  fila trae solo lo que se sabía antes de esa elección y su abstención real.
- tabla_municipios_2027: la misma tabla con todo hasta 2024 y la abstención de 2027 vacía. Es la
  que llena el modelo y la que va a los mapas.

Las dos tablas de municipios incluyen las features sociodemográficas externas del ECEG 2010/2020
(`ext_*`), unidas por municipio con la regla de vintage de `externos.py`. No se tocan las columnas
vacías que llena el modelo (`conocidos_objetivo`, `abstencion_objetivo`).

El historial se calcula sobre el territorio que el municipio tiene en la elección que se predice:
si un municipio ganó o perdió secciones, su pasado se rearma con esas secciones. También escribe
el diccionario de datos (idea tomada de build_analisis.py, rama proposals-Max).

Uso, desde la raíz del repo y con el entorno activado (necesita las salidas de las Fases 1 y 2):
    python ai/src/data_prep/fase3.py

Salidas:
    data/processed/municipio_eleccion.parquet y .csv
    data/processed/tabla_municipios_entrenamiento.parquet y .csv
    data/processed/tabla_municipios_2027.parquet y .csv
    docs/reports/diccionario_datos.md
"""
import argparse
import sys
import time

import numpy as np
import pandas as pd

from ccpc import ANIOS, CONTEOS, ETAPAS, PROCESSED, RAIZ, REPORTES, TIPO_ELECCION, leer_tabla
from externos import (
    DICCIONARIO_EXTERNOS, cargar_o_construir_agregados, columnas_externas, unir_externos,
    validar_externos,
)
from fase1 import detener
from features_eda import COLUMNAS as FEATURES_EDA, DESCRIPCIONES as DESC_FEATURES_EDA, calcular_features_temporales
from fase2 import CAMBIOS_TERRITORIO, CATALOGO, SECCIONES, guardar, miles, tabla

BASE = PROCESSED / "municipio_eleccion"
ENTRENAMIENTO = PROCESSED / "tabla_municipios_entrenamiento"
PREDICCION = PROCESSED / "tabla_municipios_2027"
DICCIONARIO = REPORTES / "diccionario_datos.md"

LLAVE = ["AELEC", "EDOCVE", "MPIOCVE"]  # un municipio en una elección
LLAVE_MUNICIPIO = ["EDOCVE", "MPIOCVE"]
LLAVE_SECCION = ["EDOCVE", "SECCION"]
FOTOS = (2015, 2018, 2021, 2024)  # elecciones con respuesta conocida: sirven para entrenar y probar
PREDECIR = 2027
TERRITORIO_FINAL = ANIOS[-1]  # para 2027 se supone el territorio de 2024
TIPO_OBJETIVO = {**TIPO_ELECCION, PREDECIR: "intermedia"}

GRUPOS = dict(zip(ETAPAS, ["18_24", "25_34", "35_44", "45_59", "60_mas"]))
SEXOS = {0: "hombres", 1: "mujeres", 2: "no_binario"}
TIPOS = {"U": "urbana", "M": "mixta", "R": "rural"}
GRUPOS_ABST = [*GRUPOS.values(), "mujeres", "hombres", *TIPOS.values()]  # abstención por grupo
COMPOSICION = [*(f"pct_{g}" for g in GRUPOS.values()), "pct_mujeres", "pct_urbana", "pct_mixta", "pct_rural",
               "edad_promedio"]
# Todo lo que se suma por sección; tasas y porcentajes se calculan después a partir de estas sumas
SUMAS = [*CONTEOS, "LN_x_EDAD", "LN_edad_marcada", "LN_sin_dato", "LN_sin_def", "LN_nuevas",
         *(f"{c}_{g}" for g in [*GRUPOS.values(), *SEXOS.values(), *TIPOS.values()] for c in ("LN", "SV", "NV"))]

# Cifras de los docs (reto_y_datos.md) contra las que se revisa la tabla base
ABSTENCION_DOCS = {2009: 55.9, 2012: 37.9, 2015: 52.9, 2018: 37.6, 2021: 48.2, 2024: 40.3}
AGUASCALIENTES_DOCS = {2021: (1_017_420, 489_469, 499_413, 28_538), 2024: (1_097_171, 626_084, 441_222, 29_865)}

COL_BASE = [
    "EDOCVE", "MPIOCVE", "AELEC", "tipo_eleccion", "nombre_estado", "nombre_municipio", "situacion",
    *CONTEOS, "conocidos", "abstencion", "participacion", "pct_ns",
    "secciones", "secciones_sin_dato", "pct_ln_sin_dato", "pct_ln_secciones_nuevas", "ln_edad_marcada",
    *(f"pct_{g}" for g in GRUPOS.values()), "pct_mujeres", "pct_no_binario", "pct_urbana", "pct_mixta",
    "pct_rural", "edad_promedio",
    *(f"abst_{g}" for g in GRUPOS_ABST),
    "n_def", "n_del", "def_principal", "pct_ln_def_principal", "pct_ln_sin_def",
]
COL_FOTO_BASE = [
    "EDOCVE", "MPIOCVE", "nombre_estado", "nombre_municipio", "eleccion_objetivo", "tipo_objetivo",
    "abst_ultima_intermedia", "abst_prom_intermedias", "cambio_intermedias", "abst_ultima_intermedia_vs_pais",
    "abst_ultima_presidencial", "abst_prom_presidenciales", "abst_ultima_presidencial_vs_pais",
    "brecha_intermedia_presidencial",
    *(f"abst_{g}_ui" for g in GRUPOS_ABST),
    "ln_ultima", "secciones_ultima", *COMPOSICION,
    "n_intermedias_previas", "n_presidenciales_previas", "pct_ns_ultima", "pct_ns_prom", "conocidos_ultima",
    "pct_hueco_2012", "historial_rearmado", "historial_incompleto",
    "def_principal", "n_def", "n_del",
    "conocidos_objetivo", "abstencion_objetivo",
]
COL_EXTERNOS = columnas_externas()
# Conservar el orden original y añadir las nuevas features después de las respuestas.
COL_FOTO = [*COL_FOTO_BASE[:-2], *COL_EXTERNOS, *COL_FOTO_BASE[-2:], *FEATURES_EDA]


def tasa(numerador: pd.Series, denominador: pd.Series) -> pd.Series:
    """Divide; queda vacío donde el denominador es 0."""
    return numerador / denominador.where(denominador > 0)


def leer_catalogo() -> pd.DataFrame:
    return pd.read_csv(CATALOGO, encoding="utf-8-sig", dtype={"EDOCVE": "int8", "MPIOCVE": "int16"},
                       keep_default_na=False, na_values={"pct_hueco_2012": [""]})


def sumas_por_seccion() -> pd.DataFrame:
    """Una fila por sección y elección con todas las sumas que se usan después.

    Tasas y porcentajes se calculan siempre a partir de estas sumas: así se suma primero y se
    divide después, en cualquier agrupación (municipio tal como viene o territorio rearmado).
    """
    columnas = ["AELEC", "EDOCVE", "MPIOCVE", "SECCION", "TIPOSEC", "DEF", "DEL", "SEXO", "EDAD",
                "grupo_edad", *CONTEOS, "flag_edad"]
    llave = ["AELEC", *LLAVE_SECCION]
    piezas = []
    for anio in ANIOS:
        df = leer_tabla(anios=[anio], columnas=columnas)
        df["LN_x_EDAD"] = df["LN"].astype("int64") * df["EDAD"]
        df["LN_edad_marcada"] = df["LN"].where(df["flag_edad"], 0)
        s = df.groupby(llave).agg(
            MPIOCVE=("MPIOCVE", "first"), TIPOSEC=("TIPOSEC", "first"), DEF=("DEF", "first"),
            DEL=("DEL", "first"), **{c: (c, "sum") for c in [*CONTEOS, "LN_x_EDAD", "LN_edad_marcada"]})
        for col, nombres in (("grupo_edad", GRUPOS), ("SEXO", SEXOS)):
            p = df.groupby([*llave, col])[["LN", "SV", "NV"]].sum().unstack(col, fill_value=0)
            p.columns = [f"{conteo}_{nombres[valor]}" for conteo, valor in p.columns]
            s = s.join(p)
        piezas.append(s.reset_index())
        del df  # libera la memoria antes de leer la siguiente elección
    sumas = pd.concat(piezas, ignore_index=True)

    # El código 2 (no binario) solo existe en 2024: en las demás elecciones su suma es 0
    por_grupo = [f"{c}_{g}" for g in [*GRUPOS.values(), *SEXOS.values()] for c in ("LN", "SV", "NV")]
    for col in por_grupo:
        if col not in sumas:
            sumas[col] = 0
    sumas[por_grupo] = sumas[por_grupo].fillna(0).astype("int64")
    for letra, nombre in TIPOS.items():
        es = (sumas["TIPOSEC"] == letra).to_numpy()
        for c in ("LN", "SV", "NV"):
            sumas[f"{c}_{nombre}"] = np.where(es, sumas[c], 0)
    sumas["sin_dato"] = (sumas["SV"] + sumas["NV"]) == 0
    sumas["LN_sin_dato"] = np.where(sumas["sin_dato"], sumas["LN"], 0)
    sumas["LN_sin_def"] = np.where(sumas["DEF"].isna(), sumas["LN"], 0)

    # Sección nueva: no había aparecido en ninguna elección anterior (Fase 2). En 2009 ninguna cuenta.
    previas = pd.read_parquet(SECCIONES, columns=[*llave, "MPIOCVE", "eleccion_antes"])
    sumas = sumas.merge(previas, on=llave, how="outer", suffixes=("", "_fase2"), indicator=True,
                        validate="one_to_one")
    if (sumas["_merge"] != "both").any() or (sumas["MPIOCVE"] != sumas["MPIOCVE_fase2"]).any():
        detener("las secciones no coinciden con las de la Fase 2 (secciones.parquet)")
    nueva = sumas["eleccion_antes"].isna().to_numpy() & (sumas["AELEC"] > ANIOS[0]).to_numpy()
    sumas["LN_nuevas"] = np.where(nueva, sumas["LN"], 0)
    sumas["primera"] = sumas.groupby(LLAVE_SECCION)["AELEC"].transform("min")  # primera elección de la sección
    return sumas.drop(columns=["_merge", "MPIOCVE_fase2"])


def agregar(sumas: pd.DataFrame, llave: list[str]) -> pd.DataFrame:
    """Conteos, tasas, composición, abstención por grupo y distritos para cualquier agrupación."""
    g = sumas.groupby(llave)
    t = g[SUMAS].sum().astype("int64")  # int64: con int32, multiplicar los totales nacionales se desborda
    t["secciones"] = g.size()
    t["secciones_sin_dato"] = g["sin_dato"].sum()
    t["n_def"] = g["DEF"].nunique()
    t["n_del"] = g["DEL"].nunique()
    # Distrito federal principal: el que tiene más lista; si empatan, el de número menor
    por_def = (sumas.dropna(subset=["DEF"]).groupby([*llave, "DEF"])["LN"].sum().reset_index()
               .sort_values([*llave, "LN", "DEF"], ascending=[True] * len(llave) + [False, True])
               .drop_duplicates(llave).set_index(llave))
    t["def_principal"] = por_def["DEF"].astype("Int16")
    t["pct_ln_def_principal"] = tasa(por_def["LN"], t["LN"] - t["LN_sin_def"])

    t["conocidos"] = t["SV"] + t["NV"]
    t["abstencion"] = tasa(t["NV"], t["conocidos"])
    t["participacion"] = tasa(t["SV"], t["conocidos"])
    t["pct_ns"] = tasa(t["NS"], t["LN"])
    t["pct_ln_sin_dato"] = tasa(t["LN_sin_dato"], t["LN"])
    t["pct_ln_secciones_nuevas"] = tasa(t["LN_nuevas"], t["LN"])
    t["pct_ln_sin_def"] = tasa(t["LN_sin_def"], t["LN"])
    t["ln_edad_marcada"] = t["LN_edad_marcada"]
    for grupo in [*GRUPOS.values(), "mujeres", "no_binario", *TIPOS.values()]:
        t[f"pct_{grupo}"] = tasa(t[f"LN_{grupo}"], t["LN"])
    t["edad_promedio"] = tasa(t["LN_x_EDAD"], t["LN"])
    for grupo in GRUPOS_ABST:
        t[f"abst_{grupo}"] = tasa(t[f"NV_{grupo}"], t[f"SV_{grupo}"] + t[f"NV_{grupo}"])
    return t.reset_index()


def armar_base(sumas: pd.DataFrame, cat: pd.DataFrame) -> pd.DataFrame:
    """Una fila por municipio y elección, tal como vienen los datos, con nombre y situación del catálogo."""
    base = agregar(sumas, LLAVE)
    base["tipo_eleccion"] = base["AELEC"].map(TIPO_ELECCION)
    base = base.merge(cat[[*LLAVE_MUNICIPIO, "nombre_estado", "nombre_municipio"]], on=LLAVE_MUNICIPIO, how="left")
    situacion = (cat.melt(id_vars=LLAVE_MUNICIPIO, value_vars=[f"situacion_{a}" for a in ANIOS],
                          var_name="AELEC", value_name="situacion")
                 .assign(AELEC=lambda d: d["AELEC"].str[-4:].astype("int16")))
    base = base.merge(situacion, on=LLAVE, how="left")
    return base.sort_values(LLAVE, ignore_index=True)


def revisar_base(base: pd.DataFrame, cat: pd.DataFrame) -> None:
    """Se detiene si la tabla base no cuadra con la Fase 2, con los docs o consigo misma."""
    fase2 = (pd.read_parquet(SECCIONES, columns=["AELEC", "EDOCVE", *CONTEOS])
             .groupby(["AELEC", "EDOCVE"])[CONTEOS].sum().astype("int64"))
    if not fase2.equals(base.groupby(["AELEC", "EDOCVE"])[CONTEOS].sum().astype("int64")):
        detener("los totales por estado y elección no son iguales a los de la Fase 2")
    con_registro = (cat[[f"situacion_{a}" for a in ANIOS]] != "sin_registro").to_numpy().sum()
    if con_registro != len(base) or base["situacion"].isna().any() or (base["situacion"] == "sin_registro").any():
        detener("los municipios de la tabla base no coinciden con los del catálogo")
    nacional = base.groupby("AELEC")[["SV", "NV"]].sum()
    abst = (100 * nacional["NV"] / (nacional["SV"] + nacional["NV"])).round(1)
    if {int(a): float(v) for a, v in abst.items()} != ABSTENCION_DOCS:
        detener(f"la abstención nacional no es la de los docs: {abst.to_dict()}")
    for anio, cifras in AGUASCALIENTES_DOCS.items():
        ags = tuple(int(x) for x in base.loc[(base["AELEC"] == anio) & (base["EDOCVE"] == 1), CONTEOS].sum())
        if ags != cifras:
            detener(f"Aguascalientes {anio} no coincide con los docs: {ags}")
    for partes in (GRUPOS.values(), SEXOS.values(), TIPOS.values()):
        if not (base[[f"LN_{p}" for p in partes]].sum(axis=1) == base["LN"]).all():
            detener(f"la lista por {list(partes)} no suma la lista nominal")
    tasas = [c for c in base if c.startswith(("pct_", "abst_")) or c in ("abstencion", "participacion")]
    if ((base[tasas] < 0) | (base[tasas] > 1)).to_numpy().any():
        detener("hay tasas fuera de 0 a 1")
    if not (base["abstencion"].isna() == (base["conocidos"] == 0)).all():
        detener("la abstención está vacía donde sí hay casos conocidos, o al revés")


def cambios_por_clave(cat: pd.DataFrame) -> dict:
    """Para cada clave, las elecciones en que cambió de territorio y cómo (según el catálogo)."""
    sit = cat.set_index(LLAVE_MUNICIPIO)[[f"situacion_{a}" for a in ANIOS]]
    cambios = {}
    for clave, fila in sit.iterrows():
        lista = [(a, fila[f"situacion_{a}"]) for a in ANIOS if fila[f"situacion_{a}"] in CAMBIOS_TERRITORIO]
        if lista:
            cambios[(int(clave[0]), int(clave[1]))] = lista
    return cambios


def asignar_territorio(sumas: pd.DataFrame, cambios: dict, objetivo: int) -> tuple[pd.DataFrame, set, set]:
    """Manda cada sección de las elecciones anteriores al objetivo al municipio que la tiene en el
    territorio del objetivo (para 2027, el de 2024). Deja vacío MPIOCVE_T si no se puede.

    Reglas, en orden:
    1. Si la sección existe en el territorio del objetivo, va a su municipio de ahí.
    2. Si ya no existe y su clave no cambió de territorio desde entonces, va a esa misma clave.
    3. Si su clave cambió, va al heredero: el único municipio que recibió secciones de esa clave
       y que tiene secciones creadas después.
    4. Si la clave fue reasignada o hay más de un heredero posible, queda sin asignar.
    """
    territorio = min(objetivo, TERRITORIO_FINAL)
    actual = sumas[sumas["AELEC"] == territorio]
    destino = actual.set_index(LLAVE_SECCION)["MPIOCVE"]
    claves = set(zip(actual["EDOCVE"].astype(int), actual["MPIOCVE"].astype(int)))
    mas_nueva = actual.groupby(LLAVE_MUNICIPIO)["primera"].max()  # la sección más reciente de cada municipio

    previas = sumas[sumas["AELEC"] < objetivo].copy()
    previas["MPIOCVE_T"] = destino.reindex(pd.MultiIndex.from_frame(previas[LLAVE_SECCION])).to_numpy()
    faltan = previas["MPIOCVE_T"].isna().to_numpy()
    asignacion, incompletos = {}, set()
    for (anio, edo, clave), _ in previas[faltan].groupby(["AELEC", "EDOCVE", "MPIOCVE"]):
        anio, edo, clave = int(anio), int(edo), int(clave)
        despues = [s for a, s in cambios.get((edo, clave), []) if anio < a <= territorio]
        if not despues:  # regla 2
            asignacion[(anio, edo, clave)] = clave if (edo, clave) in claves else np.nan
            continue
        if "clave_reasignada" in despues:  # regla 4: la clave pasó a otro territorio
            asignacion[(anio, edo, clave)] = np.nan
            # no se sabe a cuál de los municipios nuevos o reasignados de ese estado le tocaba
            incompletos |= {k for k, lista in cambios.items() if k[0] == edo and k in claves
                            and any(anio < a <= territorio and s in ("nuevo", "clave_reasignada") for a, s in lista)}
            continue
        vivas = previas[(previas["AELEC"] == anio) & (previas["EDOCVE"] == edo) & (previas["MPIOCVE"] == clave)
                        & previas["MPIOCVE_T"].notna()]
        herederos = sorted(set(vivas["MPIOCVE_T"].astype(int)))
        if len(herederos) == 1:  # regla 3
            elegido = herederos[0]
        else:
            con_nuevas = [h for h in herederos if mas_nueva.get((edo, h), 0) > anio]
            elegido = con_nuevas[0] if len(con_nuevas) == 1 else np.nan
        if pd.isna(elegido):  # regla 4
            incompletos |= {(edo, h) for h in herederos}
        asignacion[(anio, edo, clave)] = elegido
    llaves = zip(previas.loc[faltan, "AELEC"].astype(int), previas.loc[faltan, "EDOCVE"].astype(int),
                 previas.loc[faltan, "MPIOCVE"].astype(int))
    previas.loc[faltan, "MPIOCVE_T"] = [asignacion[k] for k in llaves]

    # Rearmado: recibió secciones que estaban en otra clave, o le quitaron secciones de su pasado
    movidas = previas[previas["MPIOCVE_T"].notna() & (previas["MPIOCVE_T"] != previas["MPIOCVE"])]
    rearmados = (set(zip(movidas["EDOCVE"].astype(int), movidas["MPIOCVE_T"].astype(int)))
                 | (set(zip(movidas["EDOCVE"].astype(int), movidas["MPIOCVE"].astype(int))) & claves))
    return previas, rearmados, incompletos


def armar_foto(objetivo, sumas, cambios, base, nacional, cat) -> tuple[pd.DataFrame, dict]:
    """Una fila por municipio con lo que se sabía antes del objetivo y su abstención."""
    territorio = min(objetivo, TERRITORIO_FINAL)
    previas, rearmados, incompletos = asignar_territorio(sumas, cambios, objetivo)
    asignadas = previas[previas["MPIOCVE_T"].notna()].copy()
    asignadas["MPIOCVE"] = asignadas["MPIOCVE_T"].astype("int16")
    hist = agregar(asignadas, LLAVE)

    # Sin información del futuro: solo elecciones anteriores al objetivo
    if hist["AELEC"].max() >= objetivo:
        detener(f"la foto de {objetivo} usa una elección igual o posterior")
    # Lo asignado más lo que quedó sin asignar da el total nacional de cada elección
    sin_asignar = previas.loc[previas["MPIOCVE_T"].isna()].groupby("AELEC")["LN"].sum()
    total = hist.groupby("AELEC")["LN"].sum().add(sin_asignar, fill_value=0)
    if not total.astype("int64").equals(base[base["AELEC"] < objetivo].groupby("AELEC")["LN"].sum().astype("int64")):
        detener(f"la foto de {objetivo} pierde o duplica lista nominal al rearmar territorios")
    # En los municipios sin cambios de territorio, el historial rearmado es idéntico al original
    sin_cambio = np.array([(int(e), int(m)) not in cambios for e, m in zip(hist["EDOCVE"], hist["MPIOCVE"])])
    ref = base[(base["AELEC"] < objetivo).to_numpy()
               & np.array([(int(e), int(m)) not in cambios for e, m in zip(base["EDOCVE"], base["MPIOCVE"])])]
    comparar = ref[[*LLAVE, *CONTEOS]].merge(hist.loc[sin_cambio, [*LLAVE, *CONTEOS]], on=LLAVE, how="outer",
                                            suffixes=("", "_rearmado"), indicator=True)
    if (comparar["_merge"] != "both").any() or any((comparar[c] != comparar[f"{c}_rearmado"]).any() for c in CONTEOS):
        detener(f"en la foto de {objetivo}, el historial de municipios sin cambios no es igual al original")

    hist["tipo"] = hist["AELEC"].map(TIPO_ELECCION)
    hist = hist.sort_values([*LLAVE_MUNICIPIO, "AELEC"], ignore_index=True)
    con_dato = hist[hist["abstencion"].notna()]
    foto = base.loc[base["AELEC"] == territorio, LLAVE_MUNICIPIO].set_index(LLAVE_MUNICIPIO)

    def historial(tipo):
        """Última elección con dato de ese tipo (y la anterior) y el promedio de todas."""
        h = con_dato[con_dato["tipo"] == tipo].copy()
        h["anterior"] = h.groupby(LLAVE_MUNICIPIO)["abstencion"].shift()
        g = h.groupby(LLAVE_MUNICIPIO)
        return g.tail(1).set_index(LLAVE_MUNICIPIO), g["abstencion"].mean(), g.size()

    ui, prom_i, n_i = historial("intermedia")
    up, prom_p, n_p = historial("presidencial")
    foto["abst_ultima_intermedia"] = ui["abstencion"]
    foto["abst_prom_intermedias"] = prom_i
    foto["cambio_intermedias"] = ui["abstencion"] - ui["anterior"]
    foto["abst_ultima_intermedia_vs_pais"] = ui["abstencion"] - ui["AELEC"].map(nacional)
    foto["abst_ultima_presidencial"] = up["abstencion"]
    foto["abst_prom_presidenciales"] = prom_p
    foto["abst_ultima_presidencial_vs_pais"] = up["abstencion"] - up["AELEC"].map(nacional)
    foto["brecha_intermedia_presidencial"] = prom_i - prom_p
    foto = foto.join(calcular_features_temporales(hist, objetivo, nacional))
    for grupo in GRUPOS_ABST:
        foto[f"abst_{grupo}_ui"] = ui[f"abst_{grupo}"]

    ultima = hist.groupby(LLAVE_MUNICIPIO).tail(1).set_index(LLAVE_MUNICIPIO)  # última elección, con o sin dato
    foto["ln_ultima"] = ultima["LN"]
    foto["secciones_ultima"] = ultima["secciones"]
    for col in COMPOSICION:
        foto[col] = ultima[col]
    foto["n_intermedias_previas"] = n_i.reindex(foto.index).fillna(0).astype("int64")
    foto["n_presidenciales_previas"] = n_p.reindex(foto.index).fillna(0).astype("int64")
    foto["pct_ns_ultima"] = ultima["pct_ns"]
    foto["pct_ns_prom"] = hist.groupby(LLAVE_MUNICIPIO)["pct_ns"].mean()
    foto["conocidos_ultima"] = ultima["conocidos"]
    foto["pct_hueco_2012"] = cat.set_index(LLAVE_MUNICIPIO)["pct_hueco_2012"] / 100  # el catálogo lo trae en %
    claves = [(int(e), int(m)) for e, m in foto.index]
    foto["historial_rearmado"] = [k in rearmados for k in claves]
    foto["historial_incompleto"] = [k in incompletos for k in claves]
    for col in ("def_principal", "n_def", "n_del"):
        foto[col] = ultima[col]

    if objetivo in ANIOS:
        real = base[base["AELEC"] == objetivo].set_index(LLAVE_MUNICIPIO)
        foto["conocidos_objetivo"] = real["conocidos"]
        foto["abstencion_objetivo"] = real["abstencion"]
    else:
        foto["conocidos_objetivo"] = np.nan
        foto["abstencion_objetivo"] = np.nan
    foto["eleccion_objetivo"] = objetivo
    foto["tipo_objetivo"] = TIPO_OBJETIVO[objetivo]
    foto = foto.join(cat.set_index(LLAVE_MUNICIPIO)[["nombre_estado", "nombre_municipio"]]).reset_index()
    # Conteos como enteros; quedan vacíos en los municipios sin historial
    enteros = ["ln_ultima", "secciones_ultima", "conocidos_ultima", "def_principal", "n_def", "n_del",
               "conocidos_objetivo"]
    foto[enteros] = foto[enteros].astype("Int64")

    resumen = {
        "objetivo": objetivo, "filas": len(foto),
        "objetivo_vacio": int(foto["abstencion_objetivo"].isna().sum()),
        "sin_intermedia": int((foto["n_intermedias_previas"] == 0).sum()),
        "sin_presidencial": int((foto["n_presidenciales_previas"] == 0).sum()),
        "rearmados": int(foto["historial_rearmado"].sum()),
        "incompletos": int(foto["historial_incompleto"].sum()),
        "sin_asignar": {int(a): int(v) for a, v in sin_asignar.items() if v > 0},
    }
    return foto[[*COL_FOTO_BASE, *FEATURES_EDA]], resumen


def redondear(df: pd.DataFrame) -> pd.DataFrame:
    """Redondea los números con decimales a 6 cifras, para que el CSV sea legible."""
    flotantes = df.select_dtypes("float").columns
    return df.assign(**{c: df[c].round(6) for c in flotantes})


# Diccionario: columnas agrupadas por bloque. Cada columna: (nombre, qué significa, ¿sirve para predecir?)
# En municipio_eleccion, "No" quiere decir que es resultado de esa misma elección: en el modelo solo
# puede entrar como historial de elecciones anteriores.
DESC_BASE = [
    ("Quién es", [
        ("EDOCVE", "Número del estado (1 a 32)", "Sí"),
        ("MPIOCVE", "Número del municipio dentro de su estado, según el INE. Ojo: no es la clave del INEGI", "Sí"),
        ("AELEC", "Año de la elección", "Sí"),
        ("tipo_eleccion", "`intermedia` o `presidencial`", "Sí"),
        ("nombre_estado", "Nombre del estado", "Sí"),
        ("nombre_municipio", "Nombre del municipio (el de 2024, con las erratas corregidas)", "Sí"),
        ("situacion", "Si su territorio cambió en esa elección: `sin_cambio`, `cambio_limites` (ganó o perdió "
         "secciones), `nuevo` (primera vez que aparece) o `clave_reasignada` (su número pasó a otro territorio)", "Sí"),
    ]),
    ("Votos", [
        ("LN", "Lista nominal: personas registradas para votar", "Sí"),
        ("SV", "Personas que sí votaron", "No"),
        ("NV", "Personas que no votaron", "No"),
        ("NS", "Personas de las que no se sabe si votaron", "No"),
        ("conocidos", "Personas de las que sí se sabe si votaron (SV + NV)", "No"),
        ("abstencion", "NV ÷ (SV + NV): de las personas con dato, cuántas no votaron. Es lo que se predice", "No"),
        ("participacion", "SV ÷ (SV + NV). Es 1 menos la abstención", "No"),
        ("pct_ns", "NS ÷ LN: parte de la lista de la que no se sabe si votó", "No"),
    ]),
    ("Calidad del dato", [
        ("secciones", "Secciones que tiene el municipio", "Sí"),
        ("secciones_sin_dato", "Secciones donde no se sabe de nadie si votó", "No"),
        ("pct_ln_sin_dato", "Parte de la lista que vive en esas secciones sin dato", "No"),
        ("pct_ln_secciones_nuevas", "Parte de la lista en secciones que aparecen por primera vez (el INE las creó "
         "dividiendo otras). En 2009 siempre es 0", "Sí"),
        ("ln_edad_marcada", "Personas registradas con más de 100 años (posible error del registro). Sí cuentan en "
         "«60 o más»", "Sí"),
    ]),
    ("Cómo es su lista nominal", [
        *[(f"pct_{g}", f"Parte de la lista de {e} años", "Sí") for e, g in GRUPOS.items()],
        ("pct_mujeres", "Parte de la lista que son mujeres", "Sí"),
        ("pct_no_binario", "Parte de la lista registrada como no binaria (solo existe en 2024)", "Sí"),
        ("pct_urbana", "Parte de la lista en secciones urbanas", "Sí"),
        ("pct_mixta", "Parte de la lista en secciones mixtas", "Sí"),
        ("pct_rural", "Parte de la lista en secciones rurales", "Sí"),
        ("edad_promedio", "Edad promedio de la lista", "Sí"),
    ]),
    ("Abstención por grupo", [
        *[(f"abst_{g}", f"Abstención de las personas de {e} años", "No") for e, g in GRUPOS.items()],
        ("abst_mujeres", "Abstención de las mujeres", "No"),
        ("abst_hombres", "Abstención de los hombres", "No"),
        ("abst_urbana", "Abstención en las secciones urbanas", "No"),
        ("abst_mixta", "Abstención en las secciones mixtas", "No"),
        ("abst_rural", "Abstención en las secciones rurales", "No"),
    ]),
    ("Distritos", [
        ("n_def", "Cuántos distritos federales toca el municipio", "Sí"),
        ("n_del", "Cuántos distritos locales toca el municipio", "Sí"),
        ("def_principal", "El distrito federal donde vive la mayor parte de su lista", "Sí"),
        ("pct_ln_def_principal", "Parte de la lista que vive en ese distrito principal", "Sí"),
        ("pct_ln_sin_def", "Parte de la lista sin distrito federal (pasa en 2009 y 2012)", "Sí"),
    ]),
]
DESC_EXTERNOS = [
    ("Cobertura del censo externo (ECEG)", [
        ("censo_fuente", "Censo usado en esta fila: 2010 para 2015/2018 y 2020 para 2021/2024/2027"),
        ("tiene_eceg_2010", "1 si el municipio existe en el ECEG 2010; 0 si no (no se imputa)"),
        ("tiene_eceg_2020", "1 si el municipio existe en el ECEG 2020; 0 si no (no se imputa)"),
    ]),
    ("Características sociodemográficas del municipio (ECEG)", [
        (f"ext_{nombre}", f"{definicion}. Fórmula: `{formula}`")
        for nombre, definicion, formula in DICCIONARIO_EXTERNOS
    ]),
]
DESC_FOTO = [
    ("Quién es y qué se predice", [
        ("EDOCVE", "Número del estado (1 a 32)"),
        ("MPIOCVE", "Número INE del municipio en la elección que se predice (para 2027, el de 2024)"),
        ("nombre_estado", "Nombre del estado"),
        ("nombre_municipio", "Nombre del municipio"),
        ("eleccion_objetivo", "La elección que se predice: 2015, 2018, 2021, 2024 o 2027"),
        ("tipo_objetivo", "Si esa elección es `intermedia` o `presidencial`"),
    ]),
    ("Historial de intermedias", [
        ("abst_ultima_intermedia", "Abstención de la última intermedia antes de la elección que se predice"),
        ("abst_prom_intermedias", "Promedio de la abstención de todas las intermedias anteriores"),
        ("cambio_intermedias", "Cuánto cambió entre las dos últimas intermedias (positivo = subió). Vacío si solo "
         "hay una"),
        ("abst_ultima_intermedia_vs_pais", "La última intermedia menos la del país en esa elección (positivo = se "
         "abstiene más que el país)"),
    ]),
    ("Historial de presidenciales", [
        ("abst_ultima_presidencial", "Abstención de la última presidencial antes de la elección que se predice"),
        ("abst_prom_presidenciales", "Promedio de la abstención de todas las presidenciales anteriores"),
        ("abst_ultima_presidencial_vs_pais", "La última presidencial menos la del país en esa elección"),
        ("brecha_intermedia_presidencial", "Cuánto más se abstiene en intermedias que en presidenciales (promedio "
         "de intermedias menos promedio de presidenciales)"),
    ]),
    ("Abstención por grupo en la última intermedia", [
        *[(f"abst_{g}_ui", f"Abstención de las personas de {e} años") for e, g in GRUPOS.items()],
        ("abst_mujeres_ui", "Abstención de las mujeres"),
        ("abst_hombres_ui", "Abstención de los hombres"),
        ("abst_urbana_ui", "Abstención en las secciones urbanas"),
        ("abst_mixta_ui", "Abstención en las secciones mixtas"),
        ("abst_rural_ui", "Abstención en las secciones rurales"),
    ]),
    ("Cómo es su lista nominal (en la última elección antes de la que se predice)", [
        ("ln_ultima", "Personas registradas para votar"),
        ("secciones_ultima", "Secciones que tiene"),
        *[(f"pct_{g}", f"Parte de la lista de {e} años") for e, g in GRUPOS.items()],
        ("pct_mujeres", "Parte de la lista que son mujeres"),
        ("pct_urbana", "Parte de la lista en secciones urbanas"),
        ("pct_mixta", "Parte de la lista en secciones mixtas"),
        ("pct_rural", "Parte de la lista en secciones rurales"),
        ("edad_promedio", "Edad promedio de la lista"),
    ]),
    ("Calidad del dato", [
        ("n_intermedias_previas", "Cuántas intermedias anteriores tienen dato"),
        ("n_presidenciales_previas", "Cuántas presidenciales anteriores tienen dato"),
        ("pct_ns_ultima", "Parte de la lista sin saber si votó, en la última elección"),
        ("pct_ns_prom", "Lo mismo, en promedio de todas las elecciones anteriores"),
        ("conocidos_ultima", "Personas con dato (SV + NV) en la última elección"),
        ("pct_hueco_2012", "Parte de su lista de 2009 en secciones que faltan en 2012"),
        ("historial_rearmado", "`True` si su historial se recalculó porque ganó o perdió secciones"),
        ("historial_incompleto", "`True` si alguna sección de su pasado no se pudo asignar"),
    ]),
    ("Distritos (en la última elección)", [
        ("def_principal", "El distrito federal donde vive la mayor parte de su lista"),
        ("n_def", "Cuántos distritos federales toca"),
        ("n_del", "Cuántos distritos locales toca"),
    ]),
    *DESC_EXTERNOS,
    ("La respuesta", [
        ("conocidos_objetivo", "Personas con dato en la elección que se predice; sirve para dar más peso a los "
         "municipios grandes. Vacío en 2027"),
        ("abstencion_objetivo", "**La abstención de la elección que se predice.** En entrenamiento es la real; en "
         "2027 está vacía y la llena el modelo"),
    ]),
    ("Features temporales candidatas del EDA (al final; mejora pendiente de evaluar en Fase 7)", DESC_FEATURES_EDA),
]
EN_PUNTOS = {"cambio_presidenciales", "cambio_intermedias", "abst_ultima_intermedia_vs_pais", "abst_ultima_presidencial_vs_pais",
             "brecha_intermedia_presidencial", "brecha_intermedia_presidencial_sin_2012",
             "cambio_intermedias_vs_pais", "cambio_presidenciales_vs_pais"}
SIN_COMAS = {"EDOCVE", "MPIOCVE", "AELEC", "eleccion_objetivo", "def_principal",
             "censo_fuente", "tiene_eceg_2010", "tiene_eceg_2020"}


def mostrar(col: str, valor) -> str:
    """Un valor de ejemplo como lo leería una persona: 25.3%, +4.1 puntos, 1,372,589, Sí."""
    if pd.isna(valor):
        return "vacío"
    if isinstance(valor, (bool, np.bool_)):
        return "True" if valor else "False"
    if col in EN_PUNTOS:
        return f"{100 * valor:+.1f} puntos"
    if col.startswith(("pct_", "abst_", "ext_pct_", "ext_tasa_")) or col in (
            "abstencion", "participacion", "abstencion_objetivo"):
        return f"{100 * valor:.1f}%"
    if col in ("edad_promedio", "ext_escolaridad_promedio"):
        return f"{valor:.1f} años"
    if col.startswith("ext_"):
        return f"{valor:.3f}"
    if col in SIN_COMAS:
        return str(int(valor))
    if isinstance(valor, (int, np.integer, float, np.floating)):
        return miles(valor)
    return str(valor)


def tablas_columnas(bloques, ejemplo: pd.Series, con_uso: bool) -> list[str]:
    """Una tabla por bloque: columna, qué significa, el valor de ejemplo y (si aplica) si sirve para predecir."""
    lineas = []
    for titulo, columnas in bloques:
        encabezados = ["Columna", "Qué significa", "Ejemplo"] + (["¿Sirve para predecir?"] if con_uso else [])
        filas = [(f"`{c}`", q, mostrar(c, ejemplo[c]), *(uso if con_uso else ())) for c, q, *uso in columnas]
        lineas += [f"**{titulo}**", "", tabla(encabezados, filas), ""]
    return lineas


def escribir_diccionario(base: pd.DataFrame, entrenamiento: pd.DataFrame, prediccion: pd.DataFrame,
                         resumenes: list[dict], nacional: pd.Series) -> str:
    """Arma diccionario_datos.md. Todas las cifras salen de lo que calculó este script."""
    if ([c for _, cols in DESC_BASE for c, *_ in cols] != COL_BASE
            or [c for _, cols in DESC_FOTO for c, *_ in cols] != COL_FOTO):
        detener("el diccionario no describe exactamente las columnas de las tablas")

    def pct(x) -> str:
        return f"{100 * x:.1f}%"

    sin_dato = base[base["conocidos"] == 0].groupby("AELEC").size().reindex(ANIOS, fill_value=0)
    por_mpio = base.pivot_table(index=LLAVE_MUNICIPIO, columns="AELEC", values=["pct_18_24", "pct_rural"])
    ln_nacional = base.groupby("AELEC")["LN"].sum()
    final = resumenes[-1]
    max_sin_asignar = max((v / ln_nacional[a] for a, v in final["sin_asignar"].items()), default=0)
    puebla_base = base[(base["EDOCVE"] == 21) & (base["MPIOCVE"] == 115) & (base["AELEC"] == 2021)].iloc[0]
    puebla = entrenamiento[(entrenamiento["EDOCVE"] == 21) & (entrenamiento["MPIOCVE"] == 115)
                           & (entrenamiento["eleccion_objetivo"] == 2021)].iloc[0]
    mujeres = base["pct_mujeres"].quantile([0.01, 0.99])
    rural = base["pct_rural"].quantile([0.01, 0.99])

    filas_fotos = []
    for objetivo in (*FOTOS, PREDECIR):
        antes = [a for a in ANIOS if a < objetivo]
        ui = max(a for a in antes if TIPO_ELECCION[a] == "intermedia")
        up = max(a for a in antes if TIPO_ELECCION[a] == "presidencial")
        filas_fotos.append((objetivo, f"{antes[0]} a {antes[-1]}", ui, up, antes[-1],
                            "la real" if objetivo in ANIOS else "vacía: la calcula el modelo"))

    cobertura_ext = []
    for objetivo in (*FOTOS, PREDECIR):
        tabla_foto = entrenamiento if objetivo in FOTOS else prediccion
        grupo = tabla_foto[tabla_foto["eleccion_objetivo"] == objetivo]
        fuente = 2010 if objetivo <= 2018 else 2020
        columna = f"tiene_eceg_{fuente}"
        cobertura_ext.append((objetivo, fuente, len(grupo), int(grupo[columna].sum()),
                              int((grupo[columna] == 0).sum())))

    r = [
        "# Diccionario de datos: tablas de municipios (Fase 3)",
        "",
        "Este documento explica qué trae cada tabla y qué significa cada columna. Lo escribe "
        "`python ai/src/data_prep/fase3.py`; no se edita a mano.",
        "",
        "## Las tres tablas",
        "",
        "En las tres, **cada fila es un municipio**. Están en `data/processed/`.",
        "",
        tabla(["Tabla", "Qué trae", "Para qué sirve", "Filas"], [
            ("`municipio_eleccion`", "Lo que pasó en cada municipio en cada elección, tal como viene", "Revisar los "
             "datos y hacer el análisis exploratorio (Fase 4)", miles(len(base))),
            ("`tabla_municipios_entrenamiento`", "Una fila por municipio y por foto (2015, 2018, 2021 y 2024): lo que "
             "se sabía antes de esa elección y la abstención que hubo", "Que el modelo aprenda (Fase 7)",
             miles(len(entrenamiento))),
            ("`tabla_municipios_2027`", "Una fila por municipio: lo que se sabe hasta 2024 y la "
             "abstención de 2027 vacía", "Que el modelo la llene; va a los mapas", miles(len(prediccion))),
        ]),
        "",
        "Las dos tablas de municipios tienen **las mismas columnas**: las 49 históricas más 31 sociodemográficas "
        "del ECEG 2010/2020 (`censo_fuente`, `tiene_eceg_*` y 28 `ext_*`). Cada tabla viene en dos archivos con el "
        "mismo contenido: `.csv` (se abre en Excel) y `.parquet` (para el código, con `pd.read_parquet`).",
        "",
        "## Cómo leer los números",
        "",
        "- Las columnas que empiezan con `pct_` o `abst_` son **proporciones de 0 a 1**: `0.25` quiere decir 25%.",
        "- Las features `ext_pct_*` y `ext_tasa_*` también son **proporciones de 0 a 1**. Las demás `ext_*` son "
        "promedios o razones (por ejemplo, `ext_escolaridad_promedio` está en años).",
        "- Las que terminan en `_vs_pais` y las de cambio o brecha son **diferencias**: `0.05` quiere decir "
        "5 puntos más.",
        "- **Vacío no es cero.** Una celda vacía quiere decir que no hay dato (por ejemplo, nadie con dato en el "
        "municipio), no que la abstención fue 0.",
        "- Todos los porcentajes se calculan **sumando primero las personas y dividiendo después**, nunca "
        "promediando porcentajes de secciones.",
        "",
        "## Qué es una foto",
        "",
        "Para aprender, el modelo necesita ejemplos con la respuesta conocida. Una **foto** es la tabla de municipios "
        "armada como si estuviéramos justo antes de una elección: solo trae lo que se sabía hasta ese momento y, al "
        "final, la abstención que hubo.",
        "",
        tabla(["Foto", "Usa elecciones", "Última intermedia", "Última presidencial", "Lista nominal de",
               "Abstención objetivo"], filas_fotos),
        "",
        "Ejemplo real: **Puebla en la foto de 2021**.",
        "",
        tabla(["Lo que se sabía antes de 2021", "Valor"], [
            ("Abstención en la última intermedia (2015)", pct(puebla["abst_ultima_intermedia"])),
            ("Promedio de intermedias (2009 y 2015)", pct(puebla["abst_prom_intermedias"])),
            ("Abstención en la última presidencial (2018)", pct(puebla["abst_ultima_presidencial"])),
            ("Lista nominal (2018)", miles(puebla["ln_ultima"])),
            ("**Abstención que hubo en 2021 (la respuesta)**", f"**{pct(puebla['abstencion_objetivo'])}**"),
        ]),
        "",
        "El modelo practica con estas fotos («con lo que se sabía, ¿cuánto fue la abstención?») y luego llena la "
        "columna vacía de 2027.",
        "",
        "## Features externas (ECEG)",
        "",
        "Además del historial electoral, cada fila trae características sociodemográficas del municipio tomadas "
        "del ECEG del INEGI. Se usa **el censo más reciente anterior a la elección que se predice**: 2010 para "
        "2015 y 2018, y 2020 para 2021, 2024 y 2027. Así no se usa información posterior a la elección objetivo.",
        "",
        tabla(["Foto", "Censo usado", "Filas", "Con dato del censo", "Sin dato"], [
            (objetivo, fuente, miles(filas), miles(con_dato), miles(faltan))
            for objetivo, fuente, filas, con_dato, faltan in cobertura_ext
        ]),
        "",
        "Los municipios sin dato son, en su mayoría, municipios creados después del censo. Se conservan con "
        "`NaN` y `tiene_eceg_2010 = 0` o `tiene_eceg_2020 = 0`; no se imputan en la Fase 3. Las reglas de "
        "agregación y el detalle de la cobertura están en `reporte_externos.md`.",
        "",
        "## Municipios que cambiaron de territorio",
        "",
        "Algunos municipios ganaron o perdieron secciones; por ejemplo, San Quintín se formó en 2024 con secciones "
        "que eran de Ensenada. Para que cada fila compare siempre el mismo territorio, **el pasado se calcula con "
        "las secciones que el municipio tiene en la elección que se predice**. San Quintín tiene historial con sus "
        "secciones de antes, y a Ensenada se le quitan de su pasado. Eso es un historial rearmado.",
        "",
        tabla(["Foto", "Municipios", "Sin respuesta", "Con historial rearmado", "Con historial incompleto"],
              [(s["objetivo"], miles(s["filas"]),
                "todos (es 2027)" if s["objetivo"] == PREDECIR else miles(s["objetivo_vacio"]),
                miles(s["rearmados"]), miles(s["incompletos"])) for s in resumenes]),
        "",
        "- **Sin respuesta:** municipios donde nadie tuvo dato en esa elección. Esas filas no sirven para entrenar.",
        f"- **Historial incompleto:** a unas pocas secciones de su pasado no se les pudo encontrar dueño. En la foto "
        f"de 2027 son como máximo {miles(max(final['sin_asignar'].values(), default=0))} personas por elección, "
        f"a lo mucho el {100 * max_sin_asignar:.2f}% de la lista del país.",
        "",
        "## Cuidados al usar los datos",
        "",
        f"- **Municipios sin dato:** en {miles(sin_dato.sum())} filas no se sabe de nadie si votó (" +
        ", ".join(f"{n} en {a}" for a, n in sin_dato.items()) + "). Su abstención queda vacía.",
        f"- **Municipios muy chicos:** {miles((base['conocidos'] < 500).sum())} filas tienen menos de 500 personas "
        "con dato. Ahí el porcentaje brinca mucho de una elección a otra. El mínimo para tomarlos en cuenta se "
        "decide después del análisis exploratorio.",
        f"- **Mucho NS:** en {miles((base['pct_ns'] > 0.5).sum())} filas no se sabe si votó más de la mitad de la "
        "lista. Ahí la abstención es menos confiable.",
        "- **2012 está incompleto:** le faltan secciones que sí están en 2009 y 2015. La columna `pct_hueco_2012` "
        "dice cuánto le afecta a cada municipio (ver `reporte_consistencia.md`, sección 6).",
        f"- **Edad promedio y % de 60 o más dicen casi lo mismo** (correlación de "
        f"{base['edad_promedio'].corr(base['pct_60_mas']):.2f}, donde 1 sería que suben y bajan exactamente "
        "juntas): en el modelo conviene usar solo una.",
        f"- **El % de mujeres casi no cambia entre municipios** (casi todos están entre {pct(mujeres.iloc[0])} y "
        f"{pct(mujeres.iloc[1])}), así que aporta poco. El % rural sí cambia mucho (de {pct(rural.iloc[0])} a "
        f"{pct(rural.iloc[1])}).",
        f"- **La lista nominal cambia poco entre elecciones** (el % rural de 2021 y el de 2024 casi coinciden: "
        f"correlación de {por_mpio['pct_rural'][2021].corr(por_mpio['pct_rural'][2024]):.3f}, de un máximo de 1). "
        "Por eso cada foto "
        "usa la lista de la última elección anterior.",
        "- **La abstención por grupo es ruidosa en municipios chicos:** con pocas personas en el grupo puede salir "
        "0% o 100%.",
        "- **Distritos:** de 2009 a 2021 vienen en el mapa de distritos de 2021, no en el que se usó en cada "
        "elección. Casi todos los municipios están en un solo distrito federal.",
        "",
        "## Columnas de `municipio_eleccion`",
        "",
        "El ejemplo es **Puebla en 2021**. La última columna dice si el dato **sirve para predecir esa misma "
        "elección**: «No» quiere decir que es parte del resultado y solo puede usarse como historial para "
        "elecciones posteriores.",
        "",
        *tablas_columnas(DESC_BASE, puebla_base, con_uso=True),
        "## Columnas de `tabla_municipios_entrenamiento` y `tabla_municipios_2027`",
        "",
        "El ejemplo es **Puebla en la foto de 2021**. Todo, menos `conocidos_objetivo` y `abstencion_objetivo`, se calcula solo con "
        "información anterior a la elección que se predice (historial electoral y censo), así que todo sirve para "
        "predecir. «Última» quiere decir la más reciente con dato.",
        "",
        *tablas_columnas(DESC_FOTO, puebla, con_uso=False),
        "Las nueve features temporales candidatas se añaden al final de ambas tablas. "
        "La variante sin 2012 conserva el historial original y deja vacías las tasas sin antecedentes. "
        "Su conteo es cero sin presidenciales conocidas fuera de 2012 y vacío si no hay historial asignado. "
        "Los cambios respecto al país restan el cambio nacional al municipal entre los dos últimos "
        "antecedentes conocidos de cada tipo; sin dos antecedentes quedan vacíos. La tasa nacional es "
        "suma(NV) / suma(SV + NV) antes de reconstruir territorios. Todas las diferencias están en "
        "proporciones (0.01 = 1 punto porcentual). No usan datos de la elección objetivo. "
        "Su mejora predictiva se evaluará en Fase 7. Para actualizar las tablas existentes: "
        "`python scripts/features_eda_municipio.py`; primero se validan copias `*_features_eda`.",
        "",
        "## Revisiones que hace el script",
        "",
        "Si alguna falla, el script se detiene y no guarda nada.",
        "",
        "- ✅ Los totales por estado y elección son los mismos que en la Fase 2.",
        "- ✅ La abstención nacional es la de los docs: " + ", ".join(f"{pct(v)} en {a}" for a, v in nacional.items())
        + ".",
        "- ✅ Aguascalientes 2021 y 2024 coincide con el tablero del INE.",
        "- ✅ Los grupos de edad, de sexo y de tipo de sección suman exactamente la lista nominal.",
        "- ✅ En los municipios que no cambiaron de territorio, el historial rearmado es idéntico al original.",
        "- ✅ La unión externa conserva las filas, las columnas originales y las dos columnas de respuesta.",
        "- ✅ Ninguna foto usa datos de la elección que predice ni de las posteriores; el censo externo tampoco "
        "es posterior a la elección objetivo.",
        "- ✅ Todas las tasas y porcentajes externos quedan en [0, 1].",
        "",
        "## Cómo se usan después",
        "",
        "1. **Análisis exploratorio (Fase 4):** con `municipio_eleccion` y `tabla_municipios_entrenamiento`. Las "
        "features externas ya vienen en las dos tablas de municipios; las columnas nuevas que salgan del EDA se "
        "agregan a copias de esas tablas.",
        "2. **Modelo (Fase 7):** aprende con `tabla_municipios_entrenamiento` (la prueba clave es la foto de 2021) y "
        "llena `abstencion_objetivo` en `tabla_municipios_2027`.",
        "3. **Escenarios (Fase 8):** se hace una copia de `tabla_municipios_2027` con la intervención supuesta. Es el "
        "mismo modelo y los mismos cortes del semáforo.",
        "",
        "## Palabras que usamos",
        "",
        "- **Foto:** la tabla de municipios armada como si estuviéramos justo antes de una elección.",
        "- **Elección que se predice (objetivo):** la elección de la foto; su abstención se guarda en `abstencion_objetivo`.",
        "- **Intermedia / presidencial:** elección federal sin o con presidente en juego (intermedias: 2009, 2015, "
        "2021 y 2027).",
        "- **Lista nominal:** personas registradas para votar.",
        "- **Con dato / conocidos:** personas de las que se sabe si votaron o no (SV + NV).",
        "- **NS:** personas de la lista de las que no se sabe si votaron.",
        "- **Sección:** la zona más pequeña en que el INE divide el país; un municipio tiene varias.",
        "- **Historial rearmado:** el pasado de un municipio recalculado con las secciones que tiene ahora.",
        "- **Punto:** diferencia entre dos porcentajes (de 40% a 45% son 5 puntos).",
        "",
        "## Cambios propuestos para los docs",
        "",
        "Los docs no se tocan en esta fase. Esto es lo que se propone cambiar:",
        "",
        "- `PLAN.md`, Fase 3: la fase produce tres tablas (`municipio_eleccion`, `tabla_municipios_entrenamiento` y "
        "`tabla_municipios_2027`) y este diccionario; se corre con `python ai/src/data_prep/fase3.py`.",
        "- `PLAN.md`, Fase 5, y `reto_y_datos.md`, sección 7, punto 8: el historial de los municipios con cambios de "
        "territorio se rearma con sus secciones (falta el acuerdo del equipo).",
        "- `reto_y_datos.md`, sección 2 («Escenarios»), y `PLAN.md`, Fase 8: la intervención se aplica sobre una copia "
        "de `tabla_municipios_2027`, con el mismo modelo.",
        "- `reto_y_datos.md`, «Niveles de análisis»: los distritos se representan con `n_def`, `n_del`, "
        "`def_principal` y `pct_ln_def_principal`, sin asignar un solo distrito al municipio.",
        "",
    ]
    return "\n".join(r)


def revisar_y_guardar_features(df: pd.DataFrame, destino) -> None:
    """Genera copias, las relee y comprueba que solo se añadan las features."""
    copia = destino.with_name(destino.name + "_features_eda")
    df = redondear(df)
    guardar(df, copia.with_suffix(".parquet"))
    guardar(df, copia.with_suffix(".csv"))
    revisada = pd.read_parquet(copia.with_suffix(".parquet"))
    pd.testing.assert_frame_equal(df, revisada)
    csv = pd.read_csv(copia.with_suffix(".csv"), dtype=df.dtypes.to_dict())
    pd.testing.assert_frame_equal(df, csv, check_dtype=False, check_exact=False, atol=1e-6, rtol=0)
    if destino.with_suffix(".parquet").exists():
        anterior = pd.read_parquet(destino.with_suffix(".parquet"))
        originales = [c for c in anterior if c not in FEATURES_EDA]
        pd.testing.assert_frame_equal(anterior[originales], revisada[originales],
                                      check_dtype=False, check_exact=False, atol=1e-6, rtol=0)
    if destino == PREDICCION and revisada[["conocidos_objetivo", "abstencion_objetivo"]].notna().any().any():
        detener("la tabla 2027 contiene respuestas")


def main(argv=None) -> int:
    argparse.ArgumentParser(description="Fase 3: tablas de municipios").parse_args(argv)
    inicio = time.time()

    cat = leer_catalogo()
    sumas = sumas_por_seccion()
    base = armar_base(sumas, cat)
    revisar_base(base, cat)
    nacional = base.groupby("AELEC")["NV"].sum() / base.groupby("AELEC")["conocidos"].sum()
    cambios = cambios_por_clave(cat)

    fotos, resumenes = [], []
    for objetivo in (*FOTOS, PREDECIR):
        foto, resumen = armar_foto(objetivo, sumas, cambios, base, nacional, cat)
        fotos.append(foto)
        resumenes.append(resumen)
    entrenamiento = pd.concat(fotos[:-1], ignore_index=True)
    prediccion = fotos[-1]

    ext2010, ext2020 = cargar_o_construir_agregados()
    original_entrenamiento = entrenamiento[COL_FOTO_BASE]
    original_prediccion = prediccion[COL_FOTO_BASE]
    entrenamiento = unir_externos(entrenamiento, ext2010, ext2020)
    prediccion = unir_externos(prediccion, ext2010, ext2020)
    avisos = [*validar_externos(original_entrenamiento, entrenamiento),
              *validar_externos(original_prediccion, prediccion)]
    if avisos:
        detener("features externas fuera de rango: " + "; ".join(avisos))
    entrenamiento = entrenamiento[COL_FOTO]
    prediccion = prediccion[COL_FOTO]

    tablas = {BASE: base[COL_BASE], ENTRENAMIENTO: entrenamiento, PREDICCION: prediccion}
    # Publicar las tablas ampliadas solo después de revisar copias contra las actuales.
    for destino, df in ((ENTRENAMIENTO, entrenamiento), (PREDICCION, prediccion)):
        revisar_y_guardar_features(df, destino)
    for destino, df in tablas.items():
        df = redondear(df)
        guardar(df, destino.with_suffix(".parquet"))
        guardar(df, destino.with_suffix(".csv"))
    DICCIONARIO.write_text(escribir_diccionario(base, entrenamiento, prediccion, resumenes, nacional),
                           encoding="utf-8")

    print(f"[fase3] base {len(base):,} filas | entrenamiento {len(entrenamiento):,} | 2027 {len(prediccion):,} "
          f"({time.time() - inicio:.0f} s)")
    for destino in tablas:
        print(f"  -> {destino.relative_to(RAIZ)}.parquet y .csv")
    print(f"  -> {DICCIONARIO.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
