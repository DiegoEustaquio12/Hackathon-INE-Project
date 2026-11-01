"""Insumos y variantes de Fase 7; nunca modifica las tablas de Fase 3."""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_prep"))
from ccpc import PROCESSED, RAIZ, REPORTES
from externos import FEATURES
from fase3 import BASE, COL_FOTO_BASE, ENTRENAMIENTO, FOTOS, PREDICCION, PREDECIR
from features_eda import COLUMNAS

LLAVE = ["EDOCVE", "MPIOCVE"]
# Casi todas las filas de una foto comparten estos conteos, así que delatan su año;
# en 2027 toman valores que ninguna intermedia del entrenamiento tuvo.
CONTEOS_CALENDARIO = {
    "n_intermedias_previas", "n_presidenciales_previas", "n_presidenciales_previas_sin_2012",
}
PROHIBIDAS = {
    *LLAVE, "nombre_estado", "nombre_municipio", "eleccion_objetivo",
    "tipo_objetivo", "censo_fuente", "def_principal", "conocidos_objetivo",
    "abstencion_objetivo", "tiene_eceg_2010", "tiene_eceg_2020",
    "distancia_objetivo", "pct_ns_objetivo", "referencia", *CONTEOS_CALENDARIO,
}
BLOQUE_A = [c for c in COL_FOTO_BASE if c not in PROHIBIDAS] + ["es_intermedia"]
BLOQUE_B = [c for c in COLUMNAS if c not in PROHIBIDAS]
BLOQUE_C = [f"ext_{c}" for c in FEATURES]


def huella(ruta):
    """SHA256 por bloques; no carga una tabla adicional en memoria."""
    h = hashlib.sha256()
    with Path(ruta).open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def niveles_pais(base, ns_como_nv=False):
    totales = base.groupby("AELEC")[["NV", "NS", "conocidos", "LN"]].sum()
    numerador = totales.NV + totales.NS if ns_como_nv else totales.NV
    denominador = totales.LN if ns_como_nv else totales.conocidos
    if denominador.le(0).any():
        raise ValueError("Hay una elección sin denominador nacional")
    return numerador / denominador


def punto_partida(foto):
    return foto.abst_ultima_intermedia.where(
        foto.tipo_objetivo.eq("intermedia"), foto.abst_ultima_presidencial
    ).astype(float)


def preparar(foto, base):
    salida = foto.copy()
    if salida.duplicated([*LLAVE, "eleccion_objetivo"]).any():
        raise ValueError("Llaves municipio–elección duplicadas")
    if not salida.tipo_objetivo.isin(["intermedia", "presidencial"]).all():
        raise ValueError("Tipo de elección desconocido")
    salida["es_intermedia"] = salida.tipo_objetivo.eq("intermedia").astype("int8")
    salida["distancia_objetivo"] = (
        salida.abstencion_objetivo - salida.eleccion_objetivo.map(niveles_pais(base))
    )
    salida["referencia"] = punto_partida(salida)
    ns = base[[*LLAVE, "AELEC", "pct_ns"]].rename(
        columns={"AELEC": "eleccion_objetivo", "pct_ns": "pct_ns_objetivo"}
    )
    return salida.merge(ns, on=[*LLAVE, "eleccion_objetivo"], how="left", validate="one_to_one")


def cargar():
    rutas = [p.with_suffix(".parquet") for p in (BASE, ENTRENAMIENTO, PREDICCION)]
    for ruta in rutas:
        if not ruta.is_file():
            raise ValueError(f"Falta el insumo de Fase 3: {ruta}")
    base, entrenamiento, prediccion = [pd.read_parquet(p) for p in rutas]
    if base.duplicated([*LLAVE, "AELEC"]).any():
        raise ValueError("Municipios duplicados en la tabla base")
    if not (base.LN == base.SV + base.NV + base.NS).all():
        raise ValueError("La tabla base no cumple LN = SV + NV + NS")
    if not (base.conocidos == base.SV + base.NV).all():
        raise ValueError("La tabla base no cumple conocidos = SV + NV")
    if set(entrenamiento.eleccion_objetivo.unique()) != set(FOTOS):
        raise ValueError("Se esperaban las cuatro fotos de 2015 a 2024")
    if len(prediccion) != 2477 or not prediccion.eleccion_objetivo.eq(PREDECIR).all():
        raise ValueError("Se esperaban 2,477 municipios de 2027")
    if prediccion.abstencion_objetivo.notna().any():
        raise ValueError("La tabla fuente de 2027 debe tener la respuesta vacía")
    return base, preparar(entrenamiento, base), preparar(prediccion, base), {
        str(p.relative_to(RAIZ)): huella(p) for p in rutas
    }


def bloques(sin_censo=False):
    opciones = {"A": BLOQUE_A, "A+B": [*BLOQUE_A, *BLOQUE_B]}
    if not sin_censo:
        opciones["A+B+C"] = [*BLOQUE_A, *BLOQUE_B, *BLOQUE_C]
    return opciones


def matriz(foto, columnas):
    if len(set(columnas)) != len(columnas) or set(columnas) & PROHIBIDAS:
        raise ValueError("Columnas duplicadas o prohibidas en los predictores")
    x = foto[columnas].astype(float)
    if np.isinf(x.to_numpy()).any():
        raise ValueError("Hay predictores infinitos")
    return x


def filas_entrenables(foto, minimo=500, max_ns=None):
    if minimo < 1:
        raise ValueError("El mínimo de conocidos debe ser positivo")
    mascara = (foto.abstencion_objetivo.notna() & foto.distancia_objetivo.notna()
               & foto.conocidos_objetivo.ge(minimo))
    if max_ns is not None:
        mascara &= foto.pct_ns_objetivo.le(max_ns)
    return foto.loc[mascara].copy()


def solo_seleccion(foto):
    """Falla incluso si accidentalmente llega una fila de 2021 sin respuesta."""
    if foto.empty or not foto.eleccion_objetivo.isin([2015, 2018]).all():
        raise ValueError("La selección solo puede usar las fotos de 2015 y 2018")
    return foto


def variante_ns(foto, base):
    """Cambia respuesta y referencia; evita atribuir conteos a territorios rearmados."""
    # Conserva la cohorte original: cambiar NS no recupera respuestas excluidas en A.
    salida = foto.loc[~foto.historial_rearmado & ~foto.historial_incompleto
                      & foto.abstencion_objetivo.notna()].copy()
    tasas = base.copy()
    tasas["tasa_ns"] = (tasas.NV + tasas.NS) / tasas.LN.where(tasas.LN.gt(0))
    indice = tasas.set_index([*LLAVE, "AELEC"])
    objetivos = pd.MultiIndex.from_frame(salida[[*LLAVE, "eleccion_objetivo"]])
    salida["abstencion_objetivo"] = indice.tasa_ns.reindex(objetivos).to_numpy()
    salida["distancia_objetivo"] = (salida.abstencion_objetivo
        - salida.eleccion_objetivo.map(niveles_pais(base, ns_como_nv=True)))
    referencias = []
    for fila in salida.itertuples():
        anterior = tasas.loc[
            tasas.EDOCVE.eq(fila.EDOCVE) & tasas.MPIOCVE.eq(fila.MPIOCVE)
            & tasas.AELEC.lt(fila.eleccion_objetivo)
            & tasas.tipo_eleccion.eq(fila.tipo_objetivo) & tasas.conocidos.gt(0)
        ].sort_values("AELEC")
        referencias.append(anterior.tasa_ns.iloc[-1] if len(anterior) else np.nan)
    salida["referencia"] = referencias
    return salida


def sin_2012(foto, columnas):
    """Variante conservadora: descarta predictores sin versión libre de 2012.

    La composición y los conteos de «última» en 2015 vienen de 2012. No hay
    alternativas canónicas: se retiran en todas las fotos para no mezclar fuentes.
    """
    salida = foto.copy()
    reemplazos = {c: f"{c}_sin_2012" for c in (
        "abst_ultima_presidencial", "abst_prom_presidenciales", "brecha_intermedia_presidencial",
    )}
    permitidas = {c for c in BLOQUE_A if "intermedia" in c or c.endswith("_ui")}
    permitidas |= set(BLOQUE_C) | set(reemplazos) | {"es_intermedia", *reemplazos.values()}
    # Estas dos dependen exclusivamente de intermedias.
    permitidas |= {"anios_desde_ultima_intermedia", "cambio_intermedias_vs_pais"}
    elegidas = []
    for columna in columnas:
        if columna in permitidas:
            nueva = reemplazos.get(columna, columna)
            if nueva not in elegidas:
                elegidas.append(nueva)
    return salida, elegidas
