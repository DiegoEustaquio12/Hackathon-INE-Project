"""Fase 2 del plan: consistencia entre años.

Sigue cada sección electoral a lo largo de las seis elecciones para saber qué municipios conservan
su territorio. Si una sección pasa de un municipio a otro, el territorio de los dos cambió aunque
conserven su clave y su nombre. También elige un nombre para cada municipio y mide las secciones
que faltan en 2012.

Retoma ideas de consistencia.py (rama proposals-Max): resumir por sección antes de comparar,
clasificar las secciones por su historial y contar los cambios de tipo de sección y de distrito.

Uso, desde la raíz del repo y con el entorno activado (necesita la tabla limpia de la Fase 1):
    python ai/src/data_prep/fase2.py

Salidas:
    data/interim/secciones.parquet          una fila por sección y elección (no se versiona)
    data/processed/catalogo_municipios.csv  una fila por municipio, con su situación en cada elección
    data/processed/cambios_secciones.csv    las secciones que cambian de municipio
    docs/reports/reporte_consistencia.md    el reporte de esta fase
"""
import argparse
import re
import sys
import time
import unicodedata

import numpy as np
import pandas as pd

from ccpc import ANIOS, CONTEOS, PROCESSED, RAIZ, REPORTES, leer_tabla
from fase1 import detener

SECCIONES = RAIZ / "data" / "interim" / "secciones.parquet"
CATALOGO = PROCESSED / "catalogo_municipios.csv"
CAMBIOS = PROCESSED / "cambios_secciones.csv"
REPORTE = REPORTES / "reporte_consistencia.md"

LLAVE_SECCION = ["EDOCVE", "SECCION"]
LLAVE_MUNICIPIO = ["EDOCVE", "MPIOCVE"]
LLAVE_ELECCION = ["AELEC", "EDOCVE", "MPIOCVE"]  # un municipio en una elección
COLUMNAS = ["AELEC", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM", "SECCION", "TIPOSEC", "DEF", "DEL", *CONTEOS]
PRIMERA, ULTIMA = ANIOS[0], ANIOS[-1]
ANTES_HUECO, HUECO, DESPUES_HUECO = 2009, 2012, 2015  # en 2012 faltan secciones que sí están en 2009 y 2015

# Situación de un municipio en una elección, en el orden en que se revisa. Sus secciones se comparan
# con la última vez que aparecieron.
SITUACIONES = {
    "sin_registro": "La clave no aparece en esa elección",
    "nuevo": f"Primera elección en la que aparece la clave ({PRIMERA} es el punto de partida y ahí no cuenta)",
    "clave_reasignada": "La clave ya existía, pero ninguna de sus secciones anteriores sigue en ella "
                        "y recibió secciones de otro municipio",
    "cambio_limites": "Recibió secciones de otro municipio o le cedió secciones",
    "sin_cambio": "Conserva sus secciones. Las secciones nuevas por reseccionamiento dentro del "
                  "municipio no cuentan como cambio",
}
CAMBIOS_TERRITORIO = ["nuevo", "clave_reasignada", "cambio_limites"]

# Nombres que la regla (el nombre más reciente) deja mal. Cada uno es una escritura que ya traen
# los archivos del INE para esa clave; si no lo fuera, el script se detiene.
CORRECCIONES_NOMBRE = {
    (4, 6): ("Hopelchén", "«Hopelche}én» (2024) es errata"),
    (7, 38): ("Huitiupán", "«Huitiupaán» (2024) es errata"),
    (7, 107): ("Villa Comaltitlán", "«Villacomaltitlán» (2024) viene junto"),
    (13, 50): ("San Agustín Metzquititlán", "«San Agustón» (2024) es errata"),
    (19, 10): ("El Carmen", "2024 le quita el «El»"),
    (19, 14): ("Doctor Arroyo", "2024 lo abrevia («Dr.»)"),
    (19, 15): ("Doctor Coss", "2024 lo abrevia («Dr.»)"),
    (19, 16): ("Doctor González", "2024 lo abrevia («Dr.»)"),
    (19, 20): ("General Bravo", "2024 lo abrevia («Gral.»)"),
    (19, 21): ("General Escobedo", "2024 lo abrevia («Gral.»)"),
    (19, 22): ("General Terán", "2024 lo abrevia («Gral.»)"),
    (19, 23): ("General Treviño", "2024 lo abrevia («Gral.»)"),
    (19, 24): ("General Zaragoza", "2024 lo abrevia («Gral.»)"),
    (19, 25): ("General Zuazua", "2024 lo abrevia («Gral.»)"),
    (20, 208): ("San Juan Mixtepec Dto 08", "sin el distrito se llama igual que la clave 209"),
    (20, 209): ("San Juan Mixtepec Dto 26", "sin el distrito se llama igual que la clave 208"),
    (20, 316): ("San Pedro Mixtepec Dto 22", "sin el distrito se llama igual que la clave 317"),
    (20, 317): ("San Pedro Mixtepec Dto 26", "sin el distrito se llama igual que la clave 316"),
    (30, 10): ("Alto Lucero de Gutiérrez Barrios", "«Barios» (2024) es errata"),
}

HISTORIAL = {  # historial de una sección en las seis elecciones (idea de consistencia.py de Max)
    "completa": "En las seis elecciones",
    "nueva": f"Aparece después de {PRIMERA}",
    "desaparece": f"Está desde {PRIMERA} y ya no está en {ULTIMA}",
    "con_huecos": f"Está en {PRIMERA} y en {ULTIMA}, pero falta en alguna elección entre ellas",
}


def normalizar(texto: str) -> str:
    """Mayúsculas, sin acentos ni signos y con espacios sencillos. Solo sirve para comparar nombres."""
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]", " ", texto.upper())).strip()


def enumerar(partes: list[str]) -> str:
    """'a', 'a y b', 'a, b y c'."""
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]


def miles(n) -> str:
    return f"{int(n):,}"


def secciones_txt(n) -> str:
    """'1 sección' o 'n secciones'."""
    return "1 sección" if n == 1 else f"{miles(n)} secciones"


def resumir_secciones() -> pd.DataFrame:
    """Una fila por sección y elección. Se detiene si al sumar cambia algún total."""
    piezas = []
    for anio in ANIOS:
        df = leer_tabla(anios=[anio], columnas=COLUMNAS)
        s = df.groupby(["AELEC", *LLAVE_SECCION], as_index=False).agg(
            EDONOM=("EDONOM", "first"), MPIOCVE=("MPIOCVE", "first"), MPIONOM=("MPIONOM", "first"),
            TIPOSEC=("TIPOSEC", "first"), DEF=("DEF", "first"), DEL=("DEL", "first"),
            municipios=("MPIOCVE", "nunique"), **{c: (c, "sum") for c in CONTEOS},
        )
        if (s["municipios"] > 1).any():
            detener(f"{anio}: hay secciones con más de un municipio")
        # Conciliación (punto 4 de la Fase 2): por estado, lo sumado por sección es igual a la tabla limpia
        if not df.groupby("EDOCVE")[CONTEOS].sum().equals(s.groupby("EDOCVE")[CONTEOS].sum()):
            detener(f"{anio}: algún total por estado cambia al sumar por sección")
        piezas.append(s.drop(columns="municipios"))
        del df  # libera la memoria antes de leer la siguiente elección
    return pd.concat(piezas, ignore_index=True)


def ultima_aparicion(sec: pd.DataFrame) -> pd.DataFrame:
    """Agrega a cada sección lo que tenía la última vez que apareció y cuándo vuelve a aparecer.

    Se compara contra la última aparición y no contra la elección anterior: así, una sección que
    falta en 2012 y regresa en 2015 se compara contra 2009 y no parece nueva.
    """
    sec = sec.sort_values([*LLAVE_SECCION, "AELEC"], ignore_index=True)
    grupos = sec.groupby(LLAVE_SECCION)
    antes = grupos[["AELEC", "MPIOCVE", "TIPOSEC", "DEF", "DEL", "LN"]].shift()
    sec["eleccion_antes"] = antes["AELEC"].astype("Int16")
    sec["MPIOCVE_antes"] = antes["MPIOCVE"].astype("Int16")
    for col in ["TIPOSEC", "DEF", "DEL", "LN"]:
        sec[f"{col}_antes"] = antes[col]
    sec["eleccion_despues"] = grupos["AELEC"].shift(-1).astype("Int16")
    # sigue: estaba en el mismo municipio la última vez; cambia: estaba en otro
    sec["sigue"] = sec["MPIOCVE_antes"].eq(sec["MPIOCVE"]).fillna(False).astype(bool)
    sec["cambia"] = sec["MPIOCVE_antes"].notna().to_numpy() & ~sec["sigue"].to_numpy()
    return sec


def guardar(df: pd.DataFrame, destino) -> None:
    """Escribe primero a un temporal y luego lo renombra, para no dejar archivos a medias."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    if destino.suffix == ".parquet":
        df.to_parquet(temporal, index=False, compression="zstd")
    else:
        # Con BOM, para que Excel muestre bien los acentos. En Python: pd.read_csv(ruta, encoding="utf-8-sig")
        df.to_csv(temporal, index=False, encoding="utf-8-sig")
    temporal.replace(destino)


def historial_secciones(sec: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Qué pasa con las secciones entre elecciones. Idea tomada de consistencia.py (rama proposals-Max)."""
    hay_antes = sec["eleccion_antes"].notna().to_numpy()
    filas = []
    for anterior, anio in zip([None, *ANIOS], ANIOS):
        en = (sec["AELEC"] == anio).to_numpy()
        fila = {"eleccion": anio, "secciones": int(en.sum())}
        if anterior is not None:
            regresa = sec["eleccion_antes"].ne(anterior).fillna(False).to_numpy(dtype=bool)
            no_sigue = sec["eleccion_despues"].ne(anio).fillna(True).to_numpy(dtype=bool)
            fila.update(
                siguen=int((en & sec["sigue"].to_numpy()).sum()),
                cambian=int((en & sec["cambia"].to_numpy()).sum()),
                nuevas=int((en & ~hay_antes).sum()),
                regresan=int((en & hay_antes & regresa).sum()),
                ya_no_estan=int(((sec["AELEC"] == anterior).to_numpy() & no_sigue).sum()),
            )
            # Tipo de sección y distritos: solo se compara cuando hay valor en las dos elecciones
            for col in ["TIPOSEC", "DEF", "DEL"]:
                distinto = sec[col].ne(sec[f"{col}_antes"]) & sec[col].notna() & sec[f"{col}_antes"].notna()
                fila[f"cambia_{col}"] = int((en & distinto.fillna(False).to_numpy(dtype=bool)).sum())
        filas.append(fila)

    vida = sec.groupby(LLAVE_SECCION)["AELEC"].agg(["min", "max", "size"])
    clase = np.select(
        [vida["size"] == len(ANIOS), vida["min"] > PRIMERA, vida["max"] < ULTIMA],
        ["completa", "nueva", "desaparece"], default="con_huecos",
    )
    return pd.DataFrame(filas), pd.Series(clase).value_counts()


def nombres(sec: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Un nombre por estado y por municipio, y las escrituras que traen los archivos.

    Municipio: el nombre de la elección más reciente. Si ese nombre solo cambia acentos, mayúsculas
    o espacios respecto a otros años, se usa la escritura más frecuente (2024 trae errores como «ARío»).
    Encima van las correcciones a mano. Estado: el nombre más reciente.
    """
    por_anio = sec.groupby(LLAVE_ELECCION, as_index=False).agg(
        MPIONOM=("MPIONOM", "first"), escrituras=("MPIONOM", "nunique"), EDONOM=("EDONOM", "first"))
    if (por_anio["escrituras"] > 1).any():
        detener("hay municipios con más de un nombre dentro de una misma elección")

    veces = (por_anio.groupby([*LLAVE_MUNICIPIO, "MPIONOM"])["AELEC"]
             .agg(veces="size", primera="min", ultima="max",
                  anios=lambda a: ", ".join(str(x) for x in sorted(a)))
             .reset_index())
    frecuente = (veces.sort_values([*LLAVE_MUNICIPIO, "veces", "ultima"], ascending=[True, True, False, False])
                 .groupby(LLAVE_MUNICIPIO)["MPIONOM"].first())
    reciente = (veces.sort_values([*LLAVE_MUNICIPIO, "ultima"], ascending=[True, True, False])
                .groupby(LLAVE_MUNICIPIO)["MPIONOM"].first())
    solo_forma = reciente.map(normalizar) == frecuente.map(normalizar)
    elegido = reciente.where(~solo_forma, frecuente)
    for clave, (nombre, _) in CORRECCIONES_NOMBRE.items():
        existe = (veces["EDOCVE"] == clave[0]) & (veces["MPIOCVE"] == clave[1]) & (veces["MPIONOM"] == nombre)
        if not existe.any():
            detener(f"la corrección de {clave} no es una escritura que traigan los archivos: {nombre}")
        elegido.loc[clave] = nombre

    variantes = (veces.sort_values([*LLAVE_MUNICIPIO, "primera"])
                 .assign(texto=lambda d: d["MPIONOM"] + " (" + d["anios"] + ")")
                 .groupby(LLAVE_MUNICIPIO)["texto"].agg(lambda t: " · ".join(t) if len(t) > 1 else ""))
    estado = por_anio.sort_values("AELEC").groupby("EDOCVE")["EDONOM"].last()
    salida = pd.DataFrame({"nombre_municipio": elegido, "variantes_nombre": variantes})
    salida.insert(0, "nombre_estado", salida.index.get_level_values("EDOCVE").map(estado))
    # Escrituras que siguen siendo distintas sin acentos, mayúsculas ni signos (para el reporte)
    salida["escrituras_distintas"] = (veces.assign(norma=veces["MPIONOM"].map(normalizar))
                                      .groupby(LLAVE_MUNICIPIO)["norma"].nunique())

    norma = pd.DataFrame({"EDOCVE": salida.index.get_level_values("EDOCVE"),
                          "nombre": salida["nombre_municipio"].map(normalizar).to_numpy()})
    repetidos = norma.duplicated(keep=False).to_numpy()
    if repetidos.any():
        detener(f"hay nombres repetidos dentro de un estado: {salida.index[repetidos].tolist()}")
    return salida, por_anio


def clasificar_municipios(sec: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Situación de cada municipio en cada elección y los flujos de secciones entre municipios."""
    movidas = sec[sec["cambia"]].astype({"MPIOCVE_antes": "int16"})
    flujos = (movidas.groupby(["AELEC", "EDOCVE", "MPIOCVE_antes", "MPIOCVE"], as_index=False)
              .agg(secciones=("SECCION", "size"), LN=("LN", "sum"), LN_antes=("LN_antes", "sum")))

    mun = (sec.assign(LN_conocida=sec["LN"].where(sec["eleccion_antes"].notna(), 0))
           .groupby(LLAVE_ELECCION, as_index=False)
           .agg(secciones=("SECCION", "size"), LN=("LN", "sum"), LN_conocida=("LN_conocida", "sum"),
                siguen=("sigue", "sum")))
    recibe = flujos.groupby(LLAVE_ELECCION)["secciones"].sum().rename("recibe").reset_index()
    cede = (flujos.drop(columns="MPIOCVE").rename(columns={"MPIOCVE_antes": "MPIOCVE"})
            .groupby(LLAVE_ELECCION)["secciones"].sum().rename("cede").reset_index())
    mun = mun.merge(recibe, on=LLAVE_ELECCION, how="left").merge(cede, on=LLAVE_ELECCION, how="left")
    mun[["recibe", "cede"]] = mun[["recibe", "cede"]].fillna(0).astype(int)

    # Lo que tenía el municipio la última elección en que apareció su clave
    mun = mun.sort_values([*LLAVE_MUNICIPIO, "AELEC"], ignore_index=True)
    previa = mun.groupby(LLAVE_MUNICIPIO)[["AELEC", "secciones", "LN"]].shift()
    mun["eleccion_previa"] = previa["AELEC"]
    mun["secciones_previa"] = previa["secciones"]
    mun["LN_previa"] = previa["LN"]

    primera_vez = mun["eleccion_previa"].isna().to_numpy()
    mun["situacion"] = np.select(
        [primera_vez & (mun["AELEC"] == PRIMERA).to_numpy(),
         primera_vez,
         ((mun["siguen"] == 0) & (mun["recibe"] > 0)).to_numpy(),
         ((mun["recibe"] > 0) | (mun["cede"] > 0)).to_numpy()],
        ["sin_cambio", "nuevo", "clave_reasignada", "cambio_limites"],
        default="sin_cambio",
    )
    return mun, flujos


def notas(mun: pd.DataFrame, flujos: pd.DataFrame, nombre: pd.Series, por_anio: pd.DataFrame) -> pd.Series:
    """Una frase por municipio con lo que pasó en cada elección en la que cambió su territorio."""
    original = por_anio.set_index(LLAVE_ELECCION)["MPIONOM"]
    texto = {}
    for f in mun[mun["situacion"].isin(CAMBIOS_TERRITORIO)].itertuples():
        partes = []
        if f.situacion == "nuevo":
            partes.append("municipio nuevo")
        if f.situacion == "clave_reasignada":
            previa = int(f.eleccion_previa)
            partes.append(f"la clave ya no es el territorio de {previa} (entonces "
                          f"{original[(previa, f.EDOCVE, f.MPIOCVE)]}, con {secciones_txt(f.secciones_previa)})")
        del_mismo = (flujos["AELEC"] == f.AELEC) & (flujos["EDOCVE"] == f.EDOCVE)
        llegan = flujos[del_mismo & (flujos["MPIOCVE"] == f.MPIOCVE)]
        if len(llegan):
            origen = [f"{r.secciones} de {nombre[(f.EDOCVE, r.MPIOCVE_antes)]} (clave {r.MPIOCVE_antes})"
                      for r in llegan.itertuples()]
            partes.append(f"recibió {secciones_txt(llegan['secciones'].sum())} "
                          f"({100 * llegan['LN'].sum() / f.LN:.1f}% de su lista): {enumerar(origen)}")
        elif f.situacion == "nuevo":
            partes.append("su única sección es nueva, así que no se sabe de qué municipio salió" if f.secciones == 1
                          else f"sus {f.secciones} secciones son nuevas, así que no se sabe de qué municipio salieron")
        salen = flujos[del_mismo & (flujos["MPIOCVE_antes"] == f.MPIOCVE)]
        if len(salen):
            destino = [f"{r.secciones} a {nombre[(f.EDOCVE, r.MPIOCVE)]} (clave {r.MPIOCVE})"
                       for r in salen.itertuples()]
            partes.append(f"cedió {secciones_txt(salen['secciones'].sum())} "
                          f"({100 * salen['LN_antes'].sum() / f.LN_previa:.1f}% de su lista de {int(f.eleccion_previa)}): "
                          f"{enumerar(destino)}")
        texto.setdefault((int(f.EDOCVE), int(f.MPIOCVE)), []).append(f"{f.AELEC}: " + "; ".join(partes))
    indice = pd.MultiIndex.from_tuples(list(texto), names=LLAVE_MUNICIPIO)
    return pd.Series([" · ".join(t) for t in texto.values()], index=indice, dtype="object")


def hueco_2012(sec: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
    """Secciones que están en 2009 y en 2015 pero faltan en 2012, y cuánto pesan en cada municipio.

    El peso se mide con la lista de 2009, porque en 2012 esas secciones no traen datos.
    """
    regresan = sec[(sec["AELEC"] == DESPUES_HUECO).to_numpy()
                   & sec["eleccion_antes"].eq(ANTES_HUECO).fillna(False).to_numpy(dtype=bool)]
    falta = (regresan.astype({"MPIOCVE_antes": "int16"})
             .groupby(["EDOCVE", "MPIOCVE_antes"]).agg(secciones=("SECCION", "size"), LN=("LN_antes", "sum")))
    falta.index.names = LLAVE_MUNICIPIO
    lista = sec[sec["AELEC"] == ANTES_HUECO].groupby(LLAVE_MUNICIPIO)["LN"].sum()
    falta["pct"] = 100 * falta["LN"] / lista.reindex(falta.index)
    pct = (100 * falta["LN"] / lista).fillna(0)  # 0 en los municipios de 2009 sin secciones en el hueco
    return pct, falta, regresan


def armar_catalogo(mun: pd.DataFrame, nombre_mpio: pd.DataFrame, pct_hueco: pd.Series,
                   nota: pd.Series) -> pd.DataFrame:
    """Una fila por municipio: nombre, situación en cada elección, hueco de 2012 y nota."""
    situacion = mun.pivot(index=LLAVE_MUNICIPIO, columns="AELEC", values="situacion")
    situacion.columns = [f"situacion_{a}" for a in situacion.columns]
    situacion = situacion.reindex(columns=[f"situacion_{a}" for a in ANIOS]).fillna("sin_registro")

    cat = nombre_mpio[["nombre_estado", "nombre_municipio", "variantes_nombre"]].join(situacion)
    registro = mun.groupby(LLAVE_MUNICIPIO)["AELEC"]
    cat["primera_eleccion"] = registro.min()
    cat["elecciones_con_registro"] = registro.size()
    cat["pct_hueco_2012"] = pct_hueco.round(2)
    cat["nota"] = nota.reindex(cat.index).fillna("")

    # Cada municipio que aparece en una elección debe tener ahí una situación distinta de sin_registro
    if (cat[situacion.columns] != "sin_registro").to_numpy().sum() != len(mun):
        detener("el catálogo no cuadra con los municipios que aparecen en cada elección")
    return cat.sort_index().reset_index()


def tabla_cambios(sec: pd.DataFrame, nombre: pd.Series) -> pd.DataFrame:
    """Las secciones que cambian de municipio, con su municipio antes y después."""
    m = sec[sec["cambia"]].astype({"MPIOCVE_antes": "int16", "eleccion_antes": "int16"})
    salida = pd.DataFrame({
        "EDOCVE": m["EDOCVE"].to_numpy(),
        "SECCION": m["SECCION"].to_numpy(),
        "eleccion_antes": m["eleccion_antes"].to_numpy(),
        "eleccion": m["AELEC"].to_numpy(),
        "MPIOCVE_antes": m["MPIOCVE_antes"].to_numpy(),
        "nombre_municipio_antes": [nombre[c] for c in zip(m["EDOCVE"], m["MPIOCVE_antes"])],
        "MPIOCVE": m["MPIOCVE"].to_numpy(),
        "nombre_municipio": [nombre[c] for c in zip(m["EDOCVE"], m["MPIOCVE"])],
        "LN": m["LN"].to_numpy(),
    })
    return salida.sort_values(["eleccion", "EDOCVE", "MPIOCVE_antes", "MPIOCVE", "SECCION"], ignore_index=True)


def tabla(encabezados: list[str], filas) -> str:
    """Tabla en Markdown."""
    lineas = ["| " + " | ".join(encabezados) + " |", "|" + "---|" * len(encabezados)]
    lineas += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def escribir_reporte(por_eleccion, historial, nombre_mpio, por_anio, mun, catalogo, falta, regresan) -> str:
    """Arma reporte_consistencia.md. Todas las cifras salen de lo que calculó este script."""
    cat = catalogo.set_index(LLAVE_MUNICIPIO)
    col_sit = [f"situacion_{a}" for a in ANIOS]
    nombre_estado = cat.groupby(level="EDOCVE")["nombre_estado"].first()
    original = por_anio.set_index(LLAVE_ELECCION)["MPIONOM"]

    def estado(e) -> str:
        return f"{nombre_estado[e]} ({e})"

    def celda(x) -> str:
        return "—" if pd.isna(x) else miles(x)

    con_cambio = cat[cat[col_sit].isin(CAMBIOS_TERRITORIO).any(axis=1)]
    sin_registro = cat[(cat[col_sit] == "sin_registro").any(axis=1)]
    faltan_hueco = cat[(cat[f"situacion_{HUECO}"] == "sin_registro") & (cat[f"situacion_{ANTES_HUECO}"] != "sin_registro")]
    reasignadas = mun[mun["situacion"] == "clave_reasignada"]
    nuevos = mun[mun["situacion"].isin(["nuevo", "clave_reasignada"])].copy()
    nuevos["pct_conocida"] = 100 * nuevos["LN_conocida"] / nuevos["LN"]
    en_2024 = int((cat[f"situacion_{ULTIMA}"] != "sin_registro").sum())

    movidas = por_eleccion[por_eleccion["cambian"].fillna(0) > 0]
    total_movidas = int(movidas["cambian"].sum())
    movidas_txt = enumerar([f"{miles(r.cambian)} en {r.eleccion}" for r in movidas.itertuples()])
    if len(movidas) and movidas["eleccion"].min() > ANIOS[1]:
        movidas_txt += f"; antes de {movidas['eleccion'].min()}, ninguna"
    donde_reasignadas = enumerar(sorted({f"{estado(e)}, en {a}" for e, a in zip(reasignadas["EDOCVE"], reasignadas["AELEC"])}))

    n10, n50 = int((falta["pct"] > 10).sum()), int((falta["pct"] > 50).sum())
    cambian_hueco = int(regresan["cambia"].sum())
    casi_todo = nuevos["pct_conocida"] > 99
    resto = nuevos[~casi_todo]
    if len(resto) and (resto["pct_conocida"] < 1).all():
        resto_txt = f"los otros {len(resto)} están hechos solo de secciones nuevas, así que no se sabe de dónde salieron"
    elif len(resto):
        resto_txt = f"en los otros {len(resto)}, esa parte va de {resto['pct_conocida'].min():.1f}% a {resto['pct_conocida'].max():.1f}%"
    else:
        resto_txt = "no hay otros casos"

    previas = por_eleccion[(por_eleccion["eleccion"] < ULTIMA) & por_eleccion["cambia_DEF"].notna()]
    distritos_quietos = previas[["cambia_DEF", "cambia_DEL"]].to_numpy().sum() == 0

    variantes = nombre_mpio[nombre_mpio["variantes_nombre"] != ""]
    reales = variantes[variantes["escrituras_distintas"] > 1]
    estados_varios = por_anio.groupby(["EDOCVE", "EDONOM"])["AELEC"].unique()
    estados_varios = estados_varios[estados_varios.index.get_level_values("EDOCVE").duplicated(keep=False)]

    r = [
        "# Reporte de consistencia: Fase 2 (consistencia entre años)",
        "",
        "Lo genera `python ai/src/data_prep/fase2.py` a partir de la tabla limpia de la Fase 1. No se edita a mano: "
        "si algo cambia, se vuelve a correr el script.",
        "",
        "Sirve para saber qué municipios se pueden comparar entre elecciones. La idea es seguir cada sección "
        "electoral: si una sección pasa de un municipio a otro, el territorio de los dos cambió, aunque conserven "
        "su clave y su nombre.",
        "",
        "## Resultado",
        "",
        "- ✅ Al sumar por sección, los totales de cada estado y elección quedan iguales a los de la tabla limpia: "
        "no se perdió nada.",
        "- ✅ En cada elección, cada sección cae en un solo municipio y cada municipio trae un solo nombre.",
        f"- ✅ Las {len(CORRECCIONES_NOMBRE)} correcciones de nombre son escrituras que ya traen los archivos, y "
        "ningún nombre elegido se repite dentro de un estado.",
        f"- El catálogo tiene **{miles(len(cat))} municipios**, uno por cada clave que aparece en alguna elección. "
        + ("Todos siguen en 2024." if en_2024 == len(cat) else f"En {ULTIMA} aparecen {miles(en_2024)}."),
        f"- **{miles(total_movidas)} secciones cambian de municipio** ({movidas_txt}). Por eso **{len(con_cambio)} "
        "municipios** cambian de territorio.",
        f"- **{len(reasignadas)} claves pasan a otro territorio** ({donde_reasignadas}).",
        f"- **{len(sin_registro)} claves no aparecen en alguna elección**: los municipios creados después de "
        f"{PRIMERA} y los {len(faltan_hueco)} que faltan en {HUECO}.",
        f"- **{miles(len(regresan))} secciones faltan en {HUECO}** aunque están en {ANTES_HUECO} y en {DESPUES_HUECO}.",
        "",
        "## Salidas",
        "",
        tabla(["Archivo", "Qué trae"], [
            ("`data/processed/catalogo_municipios.csv`", "Una fila por municipio: nombre, situación en cada "
             "elección, peso del hueco de 2012 y una nota con sus cambios de territorio"),
            ("`data/processed/cambios_secciones.csv`", f"Las {miles(total_movidas)} secciones que cambian de "
             "municipio, con su municipio antes y después"),
            ("`data/interim/secciones.parquet`", "Una fila por sección y elección, con la elección y el municipio "
             "de su aparición anterior. No se sube a GitHub"),
        ]),
        "",
        "Los CSV llevan BOM para que Excel muestre bien los acentos. En Python se leen con "
        "`pd.read_csv(ruta, encoding=\"utf-8-sig\")`.",
        "",
        "## 1. Las secciones entre elecciones",
        "",
        "Cada sección se compara con la última elección en la que apareció. Así, una sección que falta en 2012 y "
        "regresa en 2015 se compara contra 2009 y no parece nueva.",
        "",
        tabla(["Elección", "Secciones", "Siguen en su municipio", "Cambian de municipio", "Nuevas",
               "Regresan después de faltar", "De la elección anterior, ya no están"],
              [(f.eleccion, miles(f.secciones), celda(f.siguen), celda(f.cambian), celda(f.nuevas),
                celda(f.regresan), celda(f.ya_no_estan)) for f in por_eleccion.itertuples()]),
        "",
        "- **Nuevas:** no habían aparecido antes. Casi todas salen del reseccionamiento (cuando el INE divide o "
        "redibuja secciones).",
        "- **Regresan después de faltar:** no estaban en la elección anterior, pero sí en una más vieja.",
        "- **Ya no están:** estaban en la elección anterior y no en esta. Algunas regresan después, como las que "
        "faltan en 2012.",
        "",
        "Historial de cada sección en las seis elecciones (idea tomada de `consistencia.py`, rama `proposals-Max`):",
        "",
        tabla(["Historial", "Secciones"], [(texto, miles(historial.get(clave, 0))) for clave, texto in HISTORIAL.items()]),
        "",
        "Cambios de tipo de sección y de distrito. Solo se comparan cuando la sección tiene valor en las dos elecciones:",
        "",
        tabla(["Elección", "Cambian de tipo (U, M, R)", "Cambian de distrito federal", "Cambian de distrito local"],
              [(f.eleccion, miles(f.cambia_TIPOSEC), miles(f.cambia_DEF), miles(f.cambia_DEL))
               for f in por_eleccion.dropna(subset=["cambia_TIPOSEC"]).itertuples()]),
        "",
        "Según el diccionario del INE, `DEF` y `DEL` de 2009 a 2021 vienen en el mapa de distritos de 2021, y los de "
        "2024 en el de 2023 (`reporte_calidad.md`, sección 3)."
        + (f" Por eso todos los cambios de distrito aparecen en {ULTIMA}." if distritos_quietos else "")
        + " Un cambio de distrito, por sí solo, no cambia el territorio del municipio.",
        "",
        "## 2. Situación de cada municipio en cada elección",
        "",
        "Cada municipio recibe una situación por elección. Se revisan en este orden y gana la primera que se cumple:",
        "",
        tabla(["Situación", "Qué quiere decir"], [(f"`{k}`", v) for k, v in SITUACIONES.items()]),
        "",
        "Municipios en cada situación:",
        "",
        tabla(["Situación", *map(str, ANIOS)],
              [(f"`{s}`", *[miles((cat[f"situacion_{a}"] == s).sum()) for a in ANIOS]) for s in SITUACIONES]),
        "",
        "Si un municipio queda `sin_cambio` en dos elecciones seguidas, su territorio es el mismo en ambas y su "
        "historial se puede comparar.",
        "",
        "## 3. Municipios con cambios de territorio",
        "",
        f"Son {len(con_cambio)} municipios con al menos una elección en `nuevo`, `clave_reasignada` o "
        "`cambio_limites`. Su historial no se puede comparar tal como viene de un lado al otro del cambio. "
        "La columna `nota` del catálogo trae el mismo texto.",
        "",
        tabla(["Estado", "Clave", "Municipio", "Qué pasó"],
              [(estado(e), m, f["nombre_municipio"], f["nota"]) for (e, m), f in con_cambio.iterrows()]),
        "",
        "## 4. Municipios nuevos y claves reasignadas",
        "",
        "La última columna dice qué parte de su lista está en secciones que ya existían en elecciones anteriores. "
        "Si es casi 100%, su historial se puede rearmar con esas secciones.",
        "",
        tabla(["Elección", "Estado", "Clave", "Nombre en esa elección", "Situación", "Secciones", "Lista nominal",
               "En secciones que ya existían"],
              [(f.AELEC, estado(f.EDOCVE), f.MPIOCVE, original[(f.AELEC, f.EDOCVE, f.MPIOCVE)], f"`{f.situacion}`",
                f.secciones, miles(f.LN), f"{f.pct_conocida:.1f}%") for f in nuevos.itertuples()]),
        "",
        "Una clave reasignada tenía antes secciones que ya no aparecen después, y en la elección siguiente la misma "
        "clave es otro municipio. Unir por clave mezclaría municipios distintos, y unir por nombre compararía un "
        "pedazo de territorio con el municipio completo.",
        "",
        "## 5. Claves que no aparecen en alguna elección",
        "",
        tabla(["Estado", "Clave", "Municipio", "Sin registro en"],
              [(estado(e), m, f["nombre_municipio"],
                ", ".join(str(a) for a in ANIOS if f[f"situacion_{a}"] == "sin_registro"))
               for (e, m), f in sin_registro.iterrows()]),
        "",
        f"## 6. El hueco de {HUECO}",
        "",
        f"- {miles(len(regresan))} secciones están en {ANTES_HUECO} y en {DESPUES_HUECO} pero no en {HUECO}. En "
        f"{ANTES_HUECO} tenían {miles(regresan['LN_antes'].sum())} personas en la lista nominal.",
        (f"- Ninguna cambia de municipio entre {ANTES_HUECO} y {DESPUES_HUECO}: el hueco no es un cambio de "
         "territorio, es información que falta." if cambian_hueco == 0 else
         f"- {miles(cambian_hueco)} cambian de municipio entre {ANTES_HUECO} y {DESPUES_HUECO}."),
        f"- Afectan a {miles(len(falta))} municipios. En {n10} son más del 10% de su lista de {ANTES_HUECO}, y en "
        f"{n50}, más de la mitad.",
        f"- {len(faltan_hueco)} municipios faltan completos en {HUECO}: "
        + enumerar([f"{f['nombre_municipio']} ({estado(e)})" for (e, m), f in faltan_hueco.iterrows()]) + ".",
        "- Esto coincide con lo que documenta el manual del INE: en 2012 se excluyeron los cuadernillos no "
        "disponibles (ver «¿Qué es NS?» en `reto_y_datos.md`).",
        "",
        "Municipios con más de la mitad de su lista en el hueco:",
        "",
        tabla(["Estado", "Clave", "Municipio", "Secciones que faltan", f"% de su lista de {ANTES_HUECO}"],
              [(estado(e), m, cat.loc[(e, m), "nombre_municipio"], miles(f.secciones), f"{f.pct:.1f}%")
               for (e, m), f in falta[falta["pct"] > 50].sort_values("pct", ascending=False).iterrows()]),
        "",
        "La columna `pct_hueco_2012` del catálogo trae este porcentaje para cada municipio.",
        "",
        "## 7. Nombres",
        "",
        "Entre elecciones, los municipios se unen con este catálogo, nunca por nombre. El nombre solo sirve para mostrar.",
        "",
        f"- **Municipio:** el nombre más reciente ({ULTIMA}). Si ese nombre solo cambia acentos, mayúsculas o "
        "espacios respecto a otros años, se usa la escritura más frecuente: en 2024 vienen errores como «ARío» o "
        "«Dr. BelisaRío Domínguez».",
        "- **Estado:** el nombre más reciente.",
        "- **Correcciones a mano:** los casos que esa regla deja mal. Cada una es una escritura que ya traen los archivos.",
        "",
        tabla(["Estado", "Clave", "Nombre elegido", "Por qué"],
              [(estado(e), m, nombre, motivo) for (e, m), (nombre, motivo) in CORRECCIONES_NOMBRE.items()]),
        "",
        "**Estados con más de un nombre:**",
        "",
        *[f"- Estado {e}: " + " · ".join(f"{n} ({', '.join(map(str, sorted(a)))})"
                                          for (_, n), a in sorted(grupo.items(), key=lambda par: min(par[1])))
          + f" → queda **{nombre_estado[e]}**" for e, grupo in estados_varios.groupby(level="EDOCVE")],
        "",
        f"**Municipios:** {len(variantes)} claves aparecen con más de una escritura. En {len(variantes) - len(reales)} "
        f"solo cambian acentos, mayúsculas o espacios. En las otras {len(reales)}, este es el nombre elegido:",
        "",
        tabla(["Estado", "Clave", "Escrituras (años)", "Nombre elegido"],
              [(estado(e), m, f["variantes_nombre"], f["nombre_municipio"]) for (e, m), f in reales.iterrows()]),
        "",
        "## 8. Pendiente",
        "",
        "- **Comparar con el tablero del INE** (punto 5 de la Fase 2): falta que alguien del equipo exporte las "
        "cifras por estado y elección.",
        f"- **Qué hacer con los {len(con_cambio)} municipios con cambios** (decisión 8 de la Fase 5): marcarlos y no "
        "usar su historial anterior al cambio, o rearmar su historial sumando las secciones que hoy les pertenecen. "
        f"De los {len(nuevos)} casos de `nuevo` o `clave_reasignada`, {int(casi_todo.sum())} tienen más del 99% de "
        f"su lista en secciones que ya existían; {resto_txt}.",
        "",
        "## 9. Cambios propuestos para los docs",
        "",
        "Los docs no se tocan en esta fase. Esto es lo que se propone cambiar:",
        "",
        f"- `reto_y_datos.md`, «Lo que cambia con el tiempo»: {miles(total_movidas)} secciones cambian de municipio "
        f"({movidas_txt}), así que {len(con_cambio)} municipios cambian de territorio aunque conserven su clave y su "
        f"nombre. Además, {len(reasignadas)} claves pasan a otro territorio (secciones 3 y 4).",
        "- `reto_y_datos.md`, «Cosas a cuidar cuando limpiemos»: entre elecciones, los municipios se unen con "
        "`catalogo_municipios.csv`, no por nombre ni solo por clave: hay claves reasignadas y nombres repetidos "
        "dentro de un estado (secciones 4 y 7).",
        f"- `reto_y_datos.md`, «¿Qué es NS?»: en {HUECO} faltan {miles(len(regresan))} secciones que sí están en "
        f"{ANTES_HUECO} y {DESPUES_HUECO}; en {n10} municipios son más del 10% de su lista (sección 6).",
        "- `reto_y_datos.md`, «Lo que falta verificar»: ya se sabe qué municipios se pueden comparar y por qué; "
        "falta contrastar los totales con el tablero.",
        "- `PLAN.md`, Fase 2: anotar que se corre con `python ai/src/data_prep/fase2.py` y que sus salidas son "
        "`catalogo_municipios.csv`, `cambios_secciones.csv` y este reporte.",
        "",
        "## Qué sigue",
        "",
        "Fase 3: armar la tabla de municipios con este catálogo. El nombre sale de `nombre_municipio`, y las columnas "
        "`situacion_AAAA` dicen qué parte del historial de cada municipio se puede comparar.",
        "",
    ]
    return "\n".join(r)


def main(argv=None) -> int:
    argparse.ArgumentParser(description="Fase 2: consistencia de los municipios entre elecciones").parse_args(argv)
    inicio = time.time()

    sec = ultima_aparicion(resumir_secciones())
    guardar(sec[["AELEC", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM", "SECCION", "TIPOSEC", "DEF", "DEL",
                 *CONTEOS, "eleccion_antes", "MPIOCVE_antes"]]
            .sort_values(["AELEC", "EDOCVE", "MPIOCVE", "SECCION"], ignore_index=True), SECCIONES)

    por_eleccion, historial = historial_secciones(sec)
    nombre_mpio, por_anio = nombres(sec)
    mun, flujos = clasificar_municipios(sec)
    nota = notas(mun, flujos, nombre_mpio["nombre_municipio"], por_anio)
    pct_hueco, falta, regresan = hueco_2012(sec)
    catalogo = armar_catalogo(mun, nombre_mpio, pct_hueco, nota)
    cambios = tabla_cambios(sec, nombre_mpio["nombre_municipio"])

    guardar(catalogo, CATALOGO)
    guardar(cambios, CAMBIOS)
    REPORTE.write_text(escribir_reporte(por_eleccion, historial, nombre_mpio, por_anio, mun, catalogo, falta,
                                        regresan), encoding="utf-8")

    con_cambio = catalogo[[f"situacion_{a}" for a in ANIOS]].isin(CAMBIOS_TERRITORIO).any(axis=1).sum()
    print(f"[fase2] {len(sec):,} secciones-elección | {len(cambios):,} cambian de municipio | "
          f"{con_cambio} municipios con cambios de territorio ({time.time() - inicio:.0f} s)")
    for ruta in (SECCIONES, CATALOGO, CAMBIOS, REPORTE):
        print(f"  -> {ruta.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
