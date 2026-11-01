"""Escenarios con intervención de la Fase 8: python ai/src/models/fase8.py.

Lee la predicción publicada de 2027 y le aplica, solo en los municipios rojos del
semáforo, el efecto supuesto de tres intervenciones. No reentrena el modelo ni
toca ``data/processed/``. El efecto es un supuesto declarado: no se estima con
estos datos.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data_prep"))
from ccpc import RAIZ, REPORTES
from fase1 import detener
from fase2 import guardar, miles, tabla

sys.path.insert(0, str(Path(__file__).resolve().parent))
from datos_modelo import huella

ARTIFACTOS = RAIZ / "ai" / "artifacts"
ENTRADA = ARTIFACTOS / "predicciones_2027.parquet"
CONFIG = ARTIFACTOS / "modelo_config.json"
SALIDA = ARTIFACTOS / "fase8"
REPORTE = REPORTES / "reporte_fase8.md"
LLAVE = ["EDOCVE", "MPIOCVE"]

# Tres colores por orden: el rojo es el tercio con mayor abstención predicha.
COLORES = ("rojo", "amarillo", "verde", "sin_clasificar")
INTERVENCIONES = {
    "jovenes": "Jóvenes de 18 a 34",
    "hombres": "Hombres",
    "rural": "Zonas rurales",
}
EFECTOS = (0.05, 0.10, 0.15)
PRIMARIO = 0.10

REQUERIDAS = [
    *LLAVE, "nombre_estado", "nombre_municipio", "eleccion_objetivo",
    "abstencion_pred", "abstencion_min", "abstencion_max", "participacion_pred",
    "conocidos_ultima", "ln_ultima", "pct_ns_ultima",
    "pct_18_24", "pct_25_34", "abst_18_24_ui", "abst_25_34_ui",
    "pct_mujeres", "abst_hombres_ui", "pct_rural", "abst_rural_ui",
    "pocos_casos", "ns_alto",
]


def cargar(ruta=ENTRADA, config=CONFIG):
    """Lee la predicción publicada y su ficha; comprueba que sea la esperada."""
    foto = pd.read_parquet(ruta)
    cfg = json.loads(Path(config).read_text(encoding="utf-8"))
    faltan = [c for c in REQUERIDAS if c not in foto.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en la predicción: {faltan}")
    if len(foto) != 2477 or foto.duplicated(LLAVE).any():
        raise ValueError("La predicción debe tener 2,477 llaves municipales únicas")
    valores = foto["abstencion_pred"].to_numpy(float)
    if not np.isfinite(valores).all() or valores.min() < 0 or valores.max() > 1:
        raise ValueError("Hay predicciones fuera de [0, 1]")
    nivel = float(cfg["nivel_pais_supuesto"])
    if not np.isclose(np.average(valores, weights=foto["conocidos_ultima"]), nivel, atol=1e-9, rtol=0):
        raise ValueError("La media ponderada no coincide con el nivel publicado")
    return foto, cfg


def verificar_fuentes(cfg):
    """Las tablas de la Fase 3 no pueden cambiar; solo se leen."""
    for ruta, esperada in cfg.get("fuentes_sha256", {}).items():
        if huella(RAIZ / ruta) != esperada:
            raise ValueError(f"La tabla fuente cambió: {ruta}")


def asignar_colores(foto):
    """Terciles por orden de la predicción sin intervención.

    Los municipios sin personas con dato quedan en gris y no entran al reparto.
    Los empates se rompen por clave municipal para que la corrida sea determinista.
    """
    clasificable = foto["conocidos_ultima"].gt(0)
    orden = (foto.loc[clasificable, ["abstencion_pred", *LLAVE]]
             .sort_values(["abstencion_pred", *LLAVE], ascending=[False, True, True]))
    n = len(orden)
    if n < 3:
        raise ValueError("No hay municipios suficientes para formar terciles")
    k = n // 3
    colores = pd.Series("sin_clasificar", index=foto.index, dtype=object)
    colores.loc[orden.index[:k]] = "rojo"
    colores.loc[orden.index[k:2 * k]] = "amarillo"
    colores.loc[orden.index[2 * k:]] = "verde"
    cortes = {
        "rojo": float(orden["abstencion_pred"].iloc[k - 1]),
        "amarillo": float(orden["abstencion_pred"].iloc[2 * k - 1]),
    }
    return colores, cortes


def color_por_corte(valores, cortes, clasificable, indice):
    """Aplica los cortes fijados en el escenario sin intervención."""
    valores = pd.Series(np.asarray(valores, dtype=float), index=indice)
    color = pd.Series(
        np.where(valores.ge(cortes["rojo"]), "rojo",
                 np.where(valores.ge(cortes["amarillo"]), "amarillo", "verde")),
        index=valores.index, dtype=object,
    )
    return color.where(clasificable, "sin_clasificar")


def grupo(foto, nombre):
    """Parte de la lista y abstención del grupo objetivo, en [0, 1]."""
    if nombre == "jovenes":
        parte = foto["pct_18_24"] + foto["pct_25_34"]
        numerador = (foto["pct_18_24"] * foto["abst_18_24_ui"]
                     + foto["pct_25_34"] * foto["abst_25_34_ui"])
        abstencion = numerador / parte.where(parte.gt(0))
        imputado = pd.Series(False, index=foto.index)
    elif nombre == "hombres":
        parte = 1.0 - foto["pct_mujeres"]
        abstencion = foto["abst_hombres_ui"].astype(float)
        imputado = pd.Series(False, index=foto.index)
    elif nombre == "rural":
        parte = foto["pct_rural"].astype(float)
        abstencion = foto["abst_rural_ui"].astype(float)
        # Sin secciones rurales no hay grupo; si las hay y falta la tasa, se usa la municipal.
        imputado = abstencion.isna() & parte.gt(0)
        abstencion = abstencion.fillna(foto["abstencion_pred"])
    else:
        raise ValueError(f"Intervención desconocida: {nombre}")
    return pd.DataFrame({"grupo_pct": parte, "abst_grupo": abstencion,
                         "grupo_imputado": imputado}, index=foto.index)


def reduccion(foto, nombre, efecto, grupos=None):
    """Puntos de abstención que quita la intervención, sobre personas con dato.

    ``efecto * parte de la lista * abstención del grupo``. La parte del grupo se
    aplica de forma proporcional a las personas con dato: se supone que quienes
    no tienen dato se reparten como quienes sí lo tienen. Así la reducción queda
    acotada y no se dispara en municipios con mucho NS.
    """
    if not 0 <= efecto <= 1:
        raise ValueError("El efecto debe estar en [0, 1]")
    g = grupo(foto, nombre) if grupos is None else grupos
    red = efecto * g["grupo_pct"] * g["abst_grupo"]
    red = red.fillna(0.0).clip(lower=0.0)
    # No se puede quitar más abstención de la que el municipio tiene.
    red = np.minimum(red, foto["abstencion_pred"].to_numpy(float))
    return pd.Series(red, index=foto.index, dtype=float)


def aplicar(foto, red, rojos):
    """Resta la reducción solo donde se aplica la intervención."""
    return (foto["abstencion_pred"] - red.where(rojos, 0.0)).clip(lower=0.0, upper=1.0)


def tabla_ancha(foto, colores, cortes, efecto):
    """Una fila por municipio: línea base y las tres intervenciones al efecto primario."""
    clasificable = foto["conocidos_ultima"].gt(0)
    rojos = colores.eq("rojo")
    salida = foto[[*LLAVE, "nombre_estado", "nombre_municipio", "abstencion_pred",
                   "abstencion_min", "abstencion_max", "participacion_pred",
                   "conocidos_ultima", "ln_ultima", "pocos_casos", "ns_alto"]].copy()
    salida["color_sin"] = colores.to_numpy()
    salida["corte_rojo_pct"] = cortes["rojo"] * 100
    salida["corte_amarillo_pct"] = cortes["amarillo"] * 100
    salida["distancia_corte_pts"] = (foto["abstencion_pred"] - cortes["rojo"]) * 100
    salida.loc[~clasificable, "distancia_corte_pts"] = np.nan
    salida["sin_clasificar"] = ~clasificable
    for nombre in INTERVENCIONES:
        g = grupo(foto, nombre)
        red = reduccion(foto, nombre, efecto, g).where(rojos, 0.0)
        nueva = aplicar(foto, red, rojos)
        color = color_por_corte(nueva, cortes, clasificable, foto.index)
        salida[f"grupo_pct_{nombre}"] = g["grupo_pct"] * 100
        salida[f"abst_grupo_{nombre}"] = g["abst_grupo"] * 100
        salida[f"reduccion_{nombre}_pts"] = red * 100
        salida[f"abstencion_{nombre}"] = nueva
        salida[f"participacion_{nombre}"] = 1.0 - nueva
        salida[f"color_{nombre}"] = color.to_numpy()
        salida[f"cambio_color_{nombre}"] = (color.ne(colores) & rojos).to_numpy()
        salida[f"grupo_imputado_{nombre}"] = g["grupo_imputado"].to_numpy()
    return salida


def tabla_larga(foto, colores, cortes, efectos):
    """Una fila por municipio, intervención y tamaño de efecto."""
    clasificable = foto["conocidos_ultima"].gt(0)
    rojos = colores.eq("rojo")
    piezas = []
    for nombre in INTERVENCIONES:
        g = grupo(foto, nombre)
        for efecto in efectos:
            red = reduccion(foto, nombre, efecto, g).where(rojos, 0.0)
            nueva = aplicar(foto, red, rojos)
            color = color_por_corte(nueva, cortes, clasificable, foto.index)
            piezas.append(pd.DataFrame({
                "EDOCVE": foto["EDOCVE"].to_numpy(),
                "MPIOCVE": foto["MPIOCVE"].to_numpy(),
                "nombre_estado": foto["nombre_estado"].to_numpy(),
                "nombre_municipio": foto["nombre_municipio"].to_numpy(),
                "intervencion": nombre,
                "efecto_pct": efecto * 100,
                "aplica": rojos.to_numpy(),
                "grupo_pct_lista": (g["grupo_pct"] * 100).to_numpy(),
                "abst_grupo": (g["abst_grupo"] * 100).to_numpy(),
                "grupo_imputado": g["grupo_imputado"].to_numpy(),
                "reduccion_pts": (red * 100).to_numpy(),
                "abstencion_sin": foto["abstencion_pred"].to_numpy(),
                "abstencion_con": nueva.to_numpy(),
                "participacion_con": (1.0 - nueva).to_numpy(),
                "color_sin": colores.to_numpy(),
                "color_con": color.to_numpy(),
                "cambio_color": (color.ne(colores) & rojos).to_numpy(),
                "conocidos_ultima": foto["conocidos_ultima"].to_numpy(),
            }))
    return pd.concat(piezas, ignore_index=True)


def resumen(larga):
    """Agregados por intervención y efecto; se recalculan desde la tabla larga."""
    filas = []
    for (nombre, efecto), d in larga.groupby(["intervencion", "efecto_pct"], sort=False):
        rojos = d["aplica"]
        red = d.loc[rojos, "reduccion_pts"]
        pesos = d.loc[rojos, "conocidos_ultima"]
        filas.append(dict(
            intervencion=nombre,
            efecto_pct=float(efecto),
            municipios=int(len(d)),
            municipios_rojos=int(rojos.sum()),
            municipios_con_efecto=int(d["reduccion_pts"].gt(0).sum()),
            salen_de_rojo=int(d["cambio_color"].sum()),
            pct_salen_de_rojo=float(d["cambio_color"].sum() / max(int(rojos.sum()), 1) * 100),
            reduccion_media_pts=float(red.mean()),
            reduccion_mediana_pts=float(red.median()),
            reduccion_max_pts=float(red.max()),
            reduccion_ponderada_pts=float(np.average(red, weights=pesos)),
            abstencion_roja_media_pts=float(d.loc[rojos, "abstencion_sin"].mean() * 100),
            abstencion_roja_media_con_pts=float(d.loc[rojos, "abstencion_con"].mean() * 100),
            municipios_imputados=int(d.loc[rojos, "grupo_imputado"].sum()),
        ))
    return pd.DataFrame(filas)


def validar(ancha, larga, efectos, cortes):
    """Invariantes antes de publicar; cualquier fallo detiene la corrida."""
    if ancha.duplicated(LLAVE).any():
        raise ValueError("La tabla ancha tiene llaves repetidas")
    if len(larga) != len(ancha) * len(INTERVENCIONES) * len(efectos):
        raise ValueError("La tabla larga no tiene todas las combinaciones")
    if larga.duplicated(["EDOCVE", "MPIOCVE", "intervencion", "efecto_pct"]).any():
        raise ValueError("Llaves repetidas en la tabla larga")
    if larga["reduccion_pts"].lt(-1e-9).any():
        raise ValueError("Hay reducciones negativas")
    if not larga["abstencion_con"].between(0, 1).all():
        raise ValueError("Hay abstención con intervención fuera de [0, 1]")
    if not np.allclose(larga["abstencion_con"] + larga["participacion_con"], 1):
        raise ValueError("La participación no es el complemento de la abstención")
    fuera = ~larga["aplica"]
    if not np.allclose(larga.loc[fuera, "abstencion_con"], larga.loc[fuera, "abstencion_sin"]):
        raise ValueError("Cambió un municipio que no es rojo")
    if not (larga.loc[fuera, "reduccion_pts"].abs() < 1e-12).all():
        raise ValueError("Hay reducción fuera de los municipios rojos")
    for nombre in INTERVENCIONES:
        d = larga.loc[larga["intervencion"].eq(nombre)].pivot(
            index=LLAVE, columns="efecto_pct", values="reduccion_pts")
        d = d[sorted(d.columns)]
        if not (d.diff(axis=1).iloc[:, 1:] >= -1e-9).all().all():
            raise ValueError(f"La reducción no crece con el efecto en {nombre}")
    gris = ancha["sin_clasificar"]
    if not (ancha.loc[gris, "color_sin"] == "sin_clasificar").all():
        raise ValueError("Un municipio sin clasificar tiene color")
    if (ancha.loc[~gris, "color_sin"] == "sin_clasificar").any():
        raise ValueError("Un municipio clasificable quedó en gris")
    for nombre in INTERVENCIONES:
        if not (ancha.loc[gris, f"reduccion_{nombre}_pts"].abs() < 1e-12).all():
            raise ValueError("Un municipio sin clasificar recibió intervención")
    if not cortes["rojo"] > cortes["amarillo"]:
        raise ValueError("Los cortes del semáforo están invertidos")


def regla_rural(foto, colores):
    """Verificación de Fase 5: rojos con más de la mitad de abstencionistas rurales."""
    rojos = colores.eq("rojo")
    parte = foto["pct_rural"] * foto["abst_rural_ui"].fillna(foto["abstencion_pred"])
    proporcion = parte / foto["abstencion_pred"].where(foto["abstencion_pred"].gt(0))
    cumple = rojos & proporcion.gt(0.5)
    return dict(rojos=int(rojos.sum()), cumplen=int(cumple.sum()),
                pct=float(cumple.sum() / max(int(rojos.sum()), 1) * 100),
                conserva=bool(cumple.sum() >= 0.10 * rojos.sum()))


def markdown(df, decimales=3):
    copia = df.copy()
    for c in copia.select_dtypes("number"):
        if pd.api.types.is_integer_dtype(copia[c]):
            copia[c] = copia[c].map(lambda v: str(v) if pd.notna(v) else "—")
        else:
            copia[c] = copia[c].map(lambda v: f"{v:.{decimales}f}" if pd.notna(v) else "—")
    return tabla(list(copia.columns), copia.fillna("—").itertuples(index=False, name=None))


def reporte_desde_archivos(salida):
    """El reporte se escribe leyendo lo que se publica, no de variables en memoria."""
    cfg = json.loads((salida / "fase8_config.json").read_text(encoding="utf-8"))
    ancha = pd.read_parquet(salida / "escenarios_municipio.parquet")
    larga = pd.read_csv(salida / "escenarios_detalle.csv", encoding="utf-8-sig")
    res = pd.read_csv(salida / "resumen_intervenciones.csv", encoding="utf-8-sig")

    conteo = ancha["color_sin"].value_counts().rename_axis("color").reset_index(name="municipios")
    orden = {c: i for i, c in enumerate(COLORES)}
    conteo["_orden"] = conteo["color"].map(orden)
    conteo = conteo.sort_values("_orden").drop(columns="_orden")

    primario = res[np.isclose(res["efecto_pct"], cfg["primario_pct"])].copy()
    primario["intervencion"] = primario["intervencion"].map(INTERVENCIONES)
    primario = primario.rename(columns={
        "intervencion": "Intervención", "efecto_pct": "Efecto (%)",
        "municipios_rojos": "Rojos", "municipios_con_efecto": "Con efecto",
        "salen_de_rojo": "Salen de rojo",
        "pct_salen_de_rojo": "% de rojos", "reduccion_media_pts": "Reducción media (pp)",
        "reduccion_mediana_pts": "Mediana (pp)", "reduccion_max_pts": "Máxima (pp)",
        "reduccion_ponderada_pts": "Ponderada (pp)",
    })[["Intervención", "Efecto (%)", "Rojos", "Con efecto", "Salen de rojo", "% de rojos",
        "Reducción media (pp)", "Mediana (pp)", "Máxima (pp)", "Ponderada (pp)"]]

    detalle = larga[np.isclose(larga["efecto_pct"], cfg["primario_pct"])]
    orden_int = {k: i for i, k in enumerate(INTERVENCIONES)}
    tope = (detalle[detalle["aplica"]]
            .assign(_orden=lambda d: d["intervencion"].map(orden_int),
                    reduccion_pts=lambda d: d["reduccion_pts"].round(2),
                    abstencion_sin=lambda d: d["abstencion_sin"] * 100,
                    abstencion_con=lambda d: d["abstencion_con"] * 100)
            .sort_values(["_orden", "reduccion_pts", "EDOCVE", "MPIOCVE"],
                         ascending=[True, False, True, True])
            .groupby("intervencion", sort=False).head(5)
            .assign(intervencion=lambda d: d["intervencion"].map(INTERVENCIONES))
            [["intervencion", "nombre_estado", "nombre_municipio", "reduccion_pts",
              "abstencion_sin", "abstencion_con"]]
            .rename(columns={"intervencion": "Intervención", "nombre_estado": "Estado",
                             "nombre_municipio": "Municipio", "reduccion_pts": "Reducción (pp)",
                             "abstencion_sin": "Sin intervención (%)",
                             "abstencion_con": "Con intervención (%)"}))

    por_estado = (detalle[detalle["aplica"] & detalle["cambio_color"]]
                  .groupby(["intervencion", "nombre_estado"]).size()
                  .sort_values(ascending=False).head(10)
                  .rename("salen_de_rojo").reset_index()
                  .assign(intervencion=lambda d: d["intervencion"].map(INTERVENCIONES))
                  .rename(columns={"intervencion": "Intervención",
                                   "nombre_estado": "Estado"}))

    rural = cfg["regla_rural"]
    return "\n".join([
        "# Escenarios con intervención (Fase 8)",
        "",
        "**El efecto de cada intervención es un supuesto declarado, no un resultado estimado con estos datos.** "
        "Los escenarios parten de la predicción municipal publicada en la Fase 7, con el mismo modelo y los mismos "
        "cortes del semáforo; no se reentrena nada y no se simula una acción real del INE.",
        "",
        "## Semáforo",
        "",
        f"Tres colores por orden de la abstención predicha. El corte rojo es **{cfg['cortes']['rojo'] * 100:.3f}%** "
        f"y el amarillo **{cfg['cortes']['amarillo'] * 100:.3f}%**. Los cortes se fijan una vez en el escenario sin "
        "intervención y se reutilizan en todas las intervenciones, para que los colores sean comparables. Los "
        f"municipios sin personas con dato ({cfg['conteo']['sin_clasificar']}) quedan en gris y no reciben intervención.",
        "",
        markdown(conteo.rename(columns={"color": "Color", "municipios": "Municipios"})),
        "",
        f"El corte rojo queda **{cfg['distancia_nacional_pts']:.2f} pp** por encima del nivel nacional publicado "
        f"({cfg['nivel_pais_pct']:.3f}%), de modo que el tercio rojo reúne a los municipios claramente por encima "
        "del promedio nacional.",
        "",
        "## Intervenciones",
        "",
        "Cada intervención se aplica **solo en los municipios rojos** y se corre por separado: los grupos se "
        "traslapan, así que sus efectos no se suman. La reducción de la abstención es",
        "",
        "```",
        "reducción = efecto × parte de la lista del grupo × abstención del grupo",
        "```",
        "",
        "La parte del grupo se aplica de forma proporcional a las personas con dato: se supone que quienes no tienen "
        "dato se reparten como quienes sí lo tienen. Así la reducción queda acotada y no se dispara en municipios con "
        "mucho NS. Para jóvenes se combinan los tramos 18–24 y 25–34 con su abstención ponderada; para hombres se usa "
        "`1 − pct_mujeres`; para rural, `pct_rural`. Si un municipio no tiene secciones rurales, la reducción rural "
        "es cero.",
        "",
        "## Resultados al efecto primario",
        "",
        markdown(primario),
        "",
        "La reducción media se calcula sobre los municipios rojos. «Salen de rojo» cuenta los que quedan por debajo "
        "del corte rojo al aplicar la intervención; el resto conserva su color. «Con efecto» cuenta los rojos donde "
        "el grupo objetivo existe: en rural excluye los municipios sin secciones rurales.",
        "",
        "## Dónde rinde más",
        "",
        "Municipios con mayor reducción absoluta al efecto primario:",
        "",
        markdown(tope),
        "",
        "Entidades donde más municipios salen de rojo al efecto primario, por intervención:",
        "",
        markdown(por_estado),
        "",
        "## Regla provisional de rural",
        "",
        f"De los {miles(rural['rojos'])} municipios rojos, {miles(rural['cumplen'])} "
        f"({rural['pct']:.1f}%) tienen más de la mitad de sus abstencionistas en secciones rurales. "
        + ("La intervención rural **se conserva**." if rural["conserva"]
           else "Son pocos, así que la intervención rural debería sustituirse por 60 o más."),
        "",
        "## Límites",
        "",
        "- El efecto es un supuesto, no una estimación causal. El mapa de diferencia mide el tamaño del supuesto.",
        "- Las tres intervenciones se traslapan y no deben sumarse.",
        "- Los municipios con pocos casos conservan su marca y su reducción es más incierta.",
        "- El escenario sin intervención tampoco es un contrafactual: los datos ya incluyen lo que el INE hizo hasta 2024.",
        "- Los cortes del semáforo siguen pendientes de ratificación del equipo; aquí se implementa la propuesta de Fase 5.",
        "",
        "## Reproducción",
        "",
        "```",
        "python ai/src/models/fase8.py",
        "python -m unittest ai/tests/test_fase8.py",
        "```",
        "",
        "Las salidas están en `ai/artifacts/fase8/`. La tabla ancha alimenta los mapas; la larga guarda la "
        "sensibilidad de 5%, 10% y 15%.",
        "",
    ])


def ejecutar(salida, efectos=EFECTOS, primario=PRIMARIO):
    foto, cfg = cargar()
    verificar_fuentes(cfg)
    colores, cortes = asignar_colores(foto)
    if not (color_por_corte(foto["abstencion_pred"], cortes,
                            foto["conocidos_ultima"].gt(0), foto.index) == colores).all():
        raise ValueError("El semáforo por cortes no reproduce el reparto por orden")
    ancha = tabla_ancha(foto, colores, cortes, primario)
    larga = tabla_larga(foto, colores, cortes, efectos)
    res = resumen(larga)
    validar(ancha, larga, efectos, cortes)
    if any(huella(RAIZ / ruta) != valor for ruta, valor in cfg["fuentes_sha256"].items()):
        raise ValueError("Una tabla fuente cambió durante la ejecución")
    guardar(ancha, salida / "escenarios_municipio.parquet")
    guardar(ancha, salida / "escenarios_municipio.csv")
    guardar(larga, salida / "escenarios_detalle.csv")
    guardar(res, salida / "resumen_intervenciones.csv")
    conteo = {c: int((colores == c).sum()) for c in COLORES}
    config = dict(
        fase=8,
        eleccion_objetivo=int(foto["eleccion_objetivo"].iloc[0]),
        metodo=str(cfg["metodo"]),
        nivel_pais_pct=float(cfg["nivel_pais_supuesto"]) * 100,
        cortes={k: float(v) for k, v in cortes.items()},
        distancia_nacional_pts=float((cortes["rojo"] - cfg["nivel_pais_supuesto"]) * 100),
        conteo=conteo,
        efectos_pct=[float(e) * 100 for e in efectos],
        primario_pct=float(primario) * 100,
        intervenciones=dict(INTERVENCIONES),
        formula="efecto * parte_lista_grupo * abstencion_grupo",
        regla_rural=regla_rural(foto, colores),
        filas_ancha=int(len(ancha)),
        filas_larga=int(len(larga)),
        fuentes_sha256=cfg.get("fuentes_sha256", {}),
        entrada_sha256=huella(ENTRADA),
        artefactos_sha256={p.name: huella(p) for p in sorted(salida.iterdir()) if p.is_file()},
    )
    (salida / "fase8_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return reporte_desde_archivos(salida), config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--efectos", default=",".join(str(e) for e in EFECTOS),
                        help="Efectos supuestos separados por coma (0 a 1)")
    parser.add_argument("--primario", type=float, default=PRIMARIO,
                        help="Efecto que se publica en la tabla ancha y los mapas")
    args = parser.parse_args(argv)
    try:
        efectos = tuple(float(e) for e in args.efectos.split(","))
    except ValueError:
        parser.error("--efectos debe ser una lista de números")
    if not efectos or any(not 0 <= e <= 1 for e in efectos):
        parser.error("Cada efecto debe estar en [0, 1]")
    if args.primario not in efectos:
        parser.error("--primario debe estar entre los efectos")
    try:
        SALIDA.mkdir(parents=True, exist_ok=True)
        REPORTE.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".fase8-", dir=SALIDA) as temporal:
            salida = Path(temporal)
            reporte, config = ejecutar(salida, efectos, args.primario)
            (salida / "reporte_fase8.md").write_text(reporte, encoding="utf-8")
            for archivo in sorted(salida.iterdir()):
                if archivo.name == "reporte_fase8.md":
                    archivo.replace(REPORTE)
                else:
                    archivo.replace(SALIDA / archivo.name)
    except (ValueError, FileNotFoundError) as exc:
        detener(str(exc))
    print(f"Listo: {config['conteo']['rojo']} municipios rojos; escenarios en {SALIDA} y reporte en {REPORTE}.")


if __name__ == "__main__":
    main()
