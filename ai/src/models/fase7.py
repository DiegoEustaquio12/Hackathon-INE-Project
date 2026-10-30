"""Entrena y evalúa la Fase 7: python ai/src/models/fase7.py [--sin-censo]."""
import argparse
import importlib.metadata
import json
import platform
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from datos_modelo import (
    BLOQUE_C, LLAVE, PREDICCION, RAIZ, REPORTES, bloques, cargar, filas_entrenables,
    huella, matriz, niveles_pais, sin_2012, variante_ns,
)
from explicacion import explicar, explicar_referencia
from fase1 import detener
from fase2 import guardar, miles, tabla
from calibracion import (
    ajustar, aplicar, predecir_calibrado, predicciones_oof, resumen as resumen_calibracion,
)
from nivel import analizar as analizar_nivel, tabla_escenarios, tabla_nacional
from validacion import (
    FIJOS, aplicar_rango, bootstrap_diferencia, calibrar_rango, centrar, entrenar,
    evaluar, gana, lightgbm, particiones_estados, predecir, regla_2024, seleccionar,
)

ARTIFACTOS = RAIZ / "ai/artifacts"
REPORTE = REPORTES / "reporte_modelo.md"
# Qué guarda cada salida. El reporte se detiene si aparece una sin explicar.
ARCHIVOS_SALIDA = [
    (("predicciones_2027.parquet", "predicciones_2027.csv"),
     "La salida principal, una fila por municipio. Copia `tabla_municipios_2027`, llena `abstencion_objetivo` "
     "y agrega abstención y participación con su rango, las tres razones y las marcas de calidad. "
     "Es lo que usan la Fase 8 y los mapas"),
    (("modelo_2027.txt",),
     "El modelo final de LightGBM, entrenado con las cuatro fotos. Se guarda aunque se publique el punto de partida"),
    (("modelo_config.json",),
     "La ficha de la corrida: método publicado, columnas, ajustes, nivel del país, rango, versiones de las "
     "librerías y huellas SHA256 de las tablas, el código y las salidas"),
    (("seleccion_congelada.json",),
     "Las columnas, los ajustes y los árboles elegidos con 2015 y 2018, guardados antes de mirar 2021"),
    (("seleccion_columnas.csv",),
     "El error de cada bloque de columnas y de cada ajuste probado, en cada grupo de estados"),
    (("validacion.csv",),
     "Los errores del modelo y del punto de partida en las pruebas de 2021, por estados y de 2024"),
    (("predicciones_pruebas.csv",),
     "Las predicciones de esas pruebas, municipio por municipio; con ellas se recalculan los errores"),
    (("sensibilidades.csv",), "Las mismas comparaciones de 2021 con las variantes de la Fase 5"),
    (("explicacion_global.csv",), "Cuánto pesa cada columna en todo el país y hacia dónde empuja"),
    (("escenarios_nivel.csv",),
     "El promedio nacional de 2027 si el país queda 5 puntos arriba o abajo del supuesto"),
    (("nivel_nacional.csv",),
     "El nivel nacional observado, los backtests de 2015 y 2021 y el pronóstico de tendencia para 2027"),
    (("nivel_escenarios.csv",),
     "La predicción municipal bajo el nivel publicado, la tendencia de las intermedias y el último cambio"),
    (("predicciones_oof.csv",),
     "Las predicciones fuera de fold de 2015–2024, por conjunto de calibración (A/B, C y final), usadas para ajustar la recta"),
    (("calibracion.csv",),
     "Los parámetros de calibración y las métricas antes y después en ajuste, 2021, 2024 y la corrida final"),
    (("validacion_bootstrap.csv",),
     "Los intervalos bootstrap del MAE del modelo publicado contra el punto de partida"),
]


def escribir_json(ruta, contenido):
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2, sort_keys=True,
                               allow_nan=False) + "\n", encoding="utf-8")


def registro_predicciones(foto, prediccion, prueba, fold=0, sin_calibrar=None, calibrada=None):
    columnas = [*LLAVE, "eleccion_objetivo", "abstencion_objetivo", "referencia",
                "conocidos_objetivo", "conocidos_ultima", "historial_rearmado", "historial_incompleto"]
    salida = foto[columnas].copy()
    salida["modelo_pred"] = np.asarray(prediccion)
    if sin_calibrar is not None:
        salida["modelo_pred_sin_calibrar"] = np.asarray(sin_calibrar)
    if calibrada is not None:
        salida["modelo_pred_calibrada"] = np.asarray(calibrada)
    salida["prueba"] = prueba
    salida["fold"] = fold
    return salida


def validar_referencia(foto):
    e = evaluar(foto, foto.referencia, "referencia")
    fila = e.loc[e.segmento.eq("todos") & e.metodo.eq("punto de partida")].iloc[0]
    if fila.n != 2458 or abs(fila.mae_pts - 12.40) > 0.01 or abs(fila.mae_ponderado_pts - 8.46) > 0.01:
        raise ValueError(f"El punto de partida no reproduce el EDA: {fila.to_dict()}")


def sensibilidades(train, prueba, base, columnas, parametros, arboles, minimo, nivel, sin_censo):
    filas = []
    variantes = [("minimo_100", 100, None), ("minimo_1000", 1000, None),
                 ("ns_max_10", minimo, 0.1), ("ns_max_20", minimo, 0.2),
                 ("ns_como_no_voto", minimo, None), ("sin_2012", minimo, None),
                 ("sin_censo", minimo, None)]
    for nombre, corte, max_ns in variantes:
        print(f"  Sensibilidad: {nombre}", flush=True)
        t, p, c, n = train, prueba, list(columnas), nivel
        if nombre == "ns_como_no_voto":
            t, p = variante_ns(t, base), variante_ns(p, base)
            n = float(niveles_pais(base, ns_como_nv=True).loc[2015])
        elif nombre == "sin_2012":
            t, c = sin_2012(t, c)
        elif nombre == "sin_censo":
            c = [col for col in c if col not in BLOQUE_C]
        t = filas_entrenables(t, corte, max_ns)
        modelo = entrenar(t, c, parametros, arboles)
        prediccion, _ = predecir(modelo, p, c, n)
        p = p.copy()
        p["prediccion_sensibilidad"] = prediccion
        if max_ns is not None:
            p = p.loc[p.pct_ns_objetivo.le(max_ns)]
        resumen = evaluar(p, p.prediccion_sensibilidad, nombre)
        resumen["n_entrenamiento"] = len(t)
        resumen["n_columnas"] = len(c)
        resumen["nota"] = ("Ya excluido en la ejecución principal" if nombre == "sin_censo"
                            and (sin_censo or not set(columnas) & set(BLOQUE_C)) else "")
        filas.append(resumen)
    return pd.concat(filas, ignore_index=True)


def _calibrar(oof):
    """Huber con respaldo lineal si la recta robusta no es utilizable."""
    try:
        return ajustar(oof, "huber")
    except ValueError:
        return ajustar(oof, "lineal")


def _fila_calibracion(conjunto, variante, y, p, w, fotos, cal=None, unidad="abstencion"):
    fila = resumen_calibracion(y, p, w)
    fila.update(
        conjunto=conjunto, variante=variante, unidad=unidad,
        fotos=" ".join(map(str, fotos)),
        a=float(cal["a"]) if cal else np.nan,
        b=float(cal["b"]) if cal else np.nan,
        metodo=cal["metodo"] if cal else "",
    )
    return fila


def _evaluar_variantes(prueba, prueba_c, pred_a, pred_b, pred_c):
    return pd.concat([
        evaluar(prueba, pred_a, "A_2021"),
        evaluar(prueba, pred_b, "B_estados"),
        evaluar(prueba_c, pred_c, "C_2024"),
    ], ignore_index=True)


def _prediccion_de_nivel(nivel_objetivo, publicada, nivel, aprobado, distancias, pesos):
    if aprobado:
        valores, _ = centrar(distancias, pesos, nivel_objetivo)
    else:
        valores = np.clip(publicada + (nivel_objetivo - nivel), 0, 1)
    return valores


def construir_salida(foto, prediccion, calibracion, metodo, nivel, razones, usa_censo,
                     calibrado=False):
    # Recupera exactamente el esquema y orden canónico; no exporta columnas auxiliares.
    fuente = pd.read_parquet(PREDICCION.with_suffix(".parquet"))
    if not fuente[LLAVE].equals(foto[LLAVE]):
        raise ValueError("El orden de municipios cambió antes de escribir la predicción")
    salida = fuente.copy()
    salida["abstencion_objetivo"] = prediccion
    salida["abstencion_pred"] = prediccion
    minimo, maximo = aplicar_rango(prediccion, foto.conocidos_ultima, calibracion)
    salida["abstencion_min"], salida["abstencion_max"] = minimo, maximo
    salida["participacion_pred"] = 1 - np.asarray(prediccion)
    salida["participacion_min"], salida["participacion_max"] = 1 - maximo, 1 - minimo
    salida["distancia_pais_pred"] = salida.abstencion_pred - nivel
    salida["nivel_pais_supuesto"] = nivel
    salida["metodo"] = metodo
    salida["calibrado"] = bool(calibrado)
    for c in razones:
        salida[c] = razones[c].to_numpy()
    salida["pocos_casos"] = foto.conocidos_ultima.lt(500).to_numpy()
    salida["ns_alto"] = foto.pct_ns_ultima.gt(0.5).to_numpy()
    # sin_censo significa falta de cobertura; el uso del bloque se registra aparte.
    salida["sin_censo"] = foto[BLOQUE_C].isna().all(axis=1).to_numpy()
    salida["censo_utilizado"] = usa_censo
    validar_salida(salida, nivel, metodo)
    return salida


def validar_salida(salida, nivel, metodo):
    if len(salida) != 2477 or salida.duplicated(LLAVE).any():
        raise ValueError("La salida debe tener 2,477 llaves municipales únicas")
    for prefijo in ("abstencion", "participacion"):
        columnas = [f"{prefijo}_{s}" for s in ("min", "pred", "max")]
        valores = salida[columnas]
        if not np.isfinite(valores.to_numpy()).all() or not valores.ge(0).all().all() or not valores.le(1).all().all():
            raise ValueError("Predicciones o rangos fuera de [0, 1]")
        if not ((valores.iloc[:, 0] <= valores.iloc[:, 1]) & (valores.iloc[:, 1] <= valores.iloc[:, 2])).all():
            raise ValueError("El rango no contiene la predicción")
    if not np.allclose(salida.abstencion_pred + salida.participacion_pred, 1):
        raise ValueError("La participación no es el complemento de la abstención")
    if not np.array_equal(salida.abstencion_objetivo, salida.abstencion_pred):
        raise ValueError("La respuesta de 2027 no coincide con la predicción")
    if metodo == "modelo" and not np.isclose(np.average(
        salida.abstencion_pred, weights=salida.conocidos_ultima), nivel, atol=1e-12, rtol=0):
        raise ValueError("El promedio ponderado no coincide con el supuesto nacional")


def reporte_desde_archivos(salida):
    """Todas las cifras se leen de los artefactos que se van a publicar."""
    config = json.loads((salida / "modelo_config.json").read_text(encoding="utf-8"))
    validacion = pd.read_csv(salida / "validacion.csv")
    seleccion = pd.read_csv(salida / "seleccion_columnas.csv")
    sensibilidad = pd.read_csv(salida / "sensibilidades.csv")
    globales = pd.read_csv(salida / "explicacion_global.csv")
    pred = pd.read_parquet(salida / "predicciones_2027.parquet")
    escenarios = pd.read_csv(salida / "escenarios_nivel.csv")
    nivel_nacional = pd.read_csv(salida / "nivel_nacional.csv")
    nivel_escenarios = pd.read_csv(salida / "nivel_escenarios.csv")
    calibracion = pd.read_csv(salida / "calibracion.csv")
    bootstrap = pd.read_csv(salida / "validacion_bootstrap.csv")
    explicados = {nombre for nombres, _ in ARCHIVOS_SALIDA for nombre in nombres}
    sin_explicar = sorted(p.name for p in salida.iterdir()
                          if p.is_file() and not p.name.startswith(".") and p.name not in explicados)
    if sin_explicar:
        raise ValueError(f"Salidas sin explicar en el reporte: {sin_explicar}")

    def markdown(df):
        copia = df.copy()
        for c in copia.select_dtypes("number"):
            if pd.api.types.is_integer_dtype(copia[c]):
                copia[c] = copia[c].map(lambda v: str(v) if pd.notna(v) else "—")
            else:
                copia[c] = copia[c].map(lambda v: f"{v:.3f}" if pd.notna(v) else "—")
        return tabla(list(copia.columns), copia.fillna("—").itertuples(index=False, name=None))

    if config["metodo"] == "modelo":
        etiqueta = "calibrado" if config["calibracion_aplicada"] else "sin calibrar"
        decision = (f"LightGBM {etiqueta} supera al punto de partida en los cuatro errores exigidos de A y B. "
                    "Se publica el modelo municipal.")
    else:
        decision = ("Ni la variante calibrada ni la sin calibrar superan las cuatro condiciones de A y B. "
                    "Se publica el punto de partida: repetir la última elección del mismo tipo.")
    variantes = (
        f"La variante calibrada {'supera' if config['gana_calibrado'] else 'no supera'} A y B; "
        f"la variante sin calibrar {'supera' if config['gana_sin_calibrar'] else 'no supera'} A y B. "
        f"Se publica: **{config['variante']}**."
    )
    regla = config["regla_2024"]
    aplicacion_calibracion = (
        " y es la que se aplica a 2027" if config["calibracion_aplicada"]
        else "; en esta corrida no se aplica porque se publica la variante sin calibrar"
    )
    if regla["cumple"]:
        regla_texto = (
            f"La prueba secundaria de 2024 no empeora el MAE más de {regla['tolerancia_pts']:.1f} pp "
            f"(diferencia {regla['diferencia_pts']:+.3f} pp). La regla pre-registrada se cumple: "
            f"{regla['recomendacion']}."
        )
    else:
        regla_texto = (
            f"La prueba secundaria de 2024 empeora el MAE en {regla['diferencia_pts']:+.3f} pp, "
            f"por encima de la tolerancia pre-registrada de {regla['tolerancia_pts']:.1f} pp. "
            f"La regla no se cumple: {regla['recomendacion']}."
        )
    metricas = ["prueba", "metodo", "n", "mae_pts", "mae_ponderado_pts", "spearman", "mismo_tercio_pct",
                "rojos_detectados_pct"]
    resumen_bloques = seleccion.loc[seleccion.etapa.eq("columnas")].groupby("bloque", sort=False).apply(
        lambda s: pd.Series({"columnas": s.n_columnas.iloc[0],
                             "mae_distancia_pts": np.average(s.mae_distancia_pts, weights=s.n_validacion)}),
        include_groups=False).reset_index().astype({"columnas": int})
    ajustes = seleccion.loc[seleccion.etapa.eq("ajustes")].groupby("candidato", sort=False).apply(
        lambda s: pd.Series(dict(hojas=int(s.num_leaves.iloc[0]), minimo_hoja=int(s.min_data_in_leaf.iloc[0]),
            objetivo=s.objective.iloc[0], mae_distancia_pts=np.average(s.mae_distancia_pts, weights=s.n_validacion),
            arboles_mediana=int(s.arboles.median()), elegido=bool(s.elegido.iloc[0]))),
        include_groups=False).reset_index()
    partes = [
        "# Reporte del modelo municipal (Fase 7)", decision, variantes,
        f"Se entregan {miles(len(pred))} municipios. Método publicado: **{config['metodo']}**. "
        "Generado por `python ai/src/models/fase7.py`; tasas en [0, 1], errores y aportes en puntos porcentuales.",
        "## Definiciones y fuentes",
        "Azael aprobó el 29/10/2026 estos valores para modelar, y el equipo todavía puede cambiarlos: "
        "mínimo de conocidos, NS fuera, conservar 2012, "
        "excluir respuestas ausentes, incluir historial rearmado y probar estados completos. "
        "El ECEG sigue sujeto a decisión del equipo y se evalúa como bloque candidato; `--sin-censo` lo retira.",
        f"Mínimo configurado: {config['minimo']}. Entrenamiento sin pesos; evaluación simple y ponderada por conocidos del objetivo.",
        markdown(pd.DataFrame(config["filas_por_foto"])),
        markdown(pd.DataFrame(config["nacionales"])),
        "Las tasas nacionales se obtienen de sumas NV / (SV + NV), antes de reconstruir territorios. "
        "Los predictores excluyen claves, nombres, año objetivo, vintage censal, distrito principal, "
        "marcas de cobertura, respuestas y los conteos de elecciones previas, que delatan el año de la foto. "
        "Se conservan NaN: LightGBM los trata directamente.",
        "## Selección congelada antes de 2021",
        "Cinco grupos de estados en 2015/2018; se minimiza MAE de la distancia municipal al país. "
        "Primero se comparan bloques con 15 hojas, 50 filas por hoja y error cuadrado; después los 18 ajustes. "
        "Los empates conservan el primer candidato. No se usan 2021 ni 2024 para elegir columnas, "
        "ajustes o árboles. La evaluación de 2021 se ejecuta después de congelarlos. "
        "El paro temprano se hace dentro del fold de entrenamiento con grupos internos de estados; "
        "el fold externo nunca se usa para decidir cuándo parar.",
        markdown(resumen_bloques), markdown(ajustes),
        f"Bloque: **{config['bloque']}**; {len(config['columnas'])} columnas; {config['arboles']} árboles "
        f"(mediana del paro temprano). Ajustes elegidos: `{json.dumps(config['parametros'], ensure_ascii=False, sort_keys=True)}`.",
        "Tasa 0.03, hasta 3,000 árboles y paciencia 100, 80% de filas y columnas por árbol, "
        "cuatro hilos, semilla 2027, deterministic=True y force_row_wise=True.",
        "## Pruebas sin información del futuro",
        "A: ajuste 2015/2018 y prueba 2021. B: ocho grupos definidos por los municipios de 2021; "
        "se retiran esos estados de ambas fotos de entrenamiento. Oaxaca queda sola. "
        "Se reúnen las distancias de B antes de centrarlas nacionalmente; no se centra cada estado a la media del país. "
        "C: ajuste hasta 2021 y prueba presidencial 2024; no decide la adopción.",
        markdown(validacion.loc[validacion.segmento.eq("todos"), metricas]),
        "El punto de partida repite la última elección del mismo tipo sin ajustarse al nivel nacional. "
        "Cada comparación usa las mismas filas con respuesta y referencia conocida, incluidos los casos pequeños. "
        "El centrado del modelo usa todos los municipios de la foto, aun sin respuesta, ponderados por conocidos_ultima. "
        "Para 2021 solo se supone el nivel nacional conocido de 2015; para 2024, el de 2018.",
        "El acierto de color parte cada método en sus propios tercios, como el semáforo por orden: el error "
        "del nivel nacional, igual para todos, no cambia el color. rojos_detectados_pct es la parte de los rojos "
        "reales que el método también pone en rojo. Es un diagnóstico; los cortes definitivos de Fase 8 siguen pendientes.",
        regla_texto,
        "### Intervalos bootstrap",
        "Diferencia de MAE (modelo publicado menos punto de partida) con remuestreo pareado por estado; "
        "el intervalo del 95% respeta la dependencia espacial. Se reporta también la versión ponderada por "
        "conocidos del objetivo.",
        markdown(bootstrap[["prueba", "unidad", "n", "mae_modelo_pts", "mae_referencia_pts",
            "diferencia_pts", "ic95_min_pts", "ic95_max_pts", "diferencia_ponderada_pts",
            "ic95_ponderado_min_pts", "ic95_ponderado_max_pts"]]),
        "Un intervalo que incluye cero indica que la diferencia no es concluyente al 95% con este remuestreo.",
        "### Municipios con cambios territoriales",
        "Las marcas rearmado e incompleto pueden solaparse.",
        markdown(pd.DataFrame(config["calidad_por_foto"])),
        markdown(validacion.loc[validacion.segmento.ne("todos"), ["prueba", "segmento", *metricas[1:]]]),
        "## Calibración",
        "La calibración ajusta la distancia municipal, no el porcentaje final: si se aplicara después del "
        "centrado se rompería la media nacional. Se agrupan las fotos de cada conjunto y se separan estados "
        "completos en cada fold; nunca se usa la fila evaluada. Se ajusta Huber sobre la recta "
        "`distancia_objetivo ~ a + b * distancia_pred` y se recurre a la recta lineal si la robusta no es "
        "utilizable. A y B se calibran solo con 2015/2018; C con 2015/2018/2021; la corrida final con "
        "las cuatro fotos. La tabla muestra el error antes y después, en distancia para los conjuntos de ajuste "
        "y en abstención para las pruebas.",
        markdown(calibracion[["conjunto", "variante", "unidad", "n", "mae_pts", "mae_ponderado_pts",
            "sesgo_pts", "pendiente", "a", "b", "metodo"]]),
        "La pendiente de calibración mide cuánto se acercan las predicciones a la diagonal; un valor "
        "distinto de uno indica desajuste (menor que uno, compresión; mayor que uno, sobre-dispersión). "
        "El sesgo es predicción menos observación. La tabla permite comparar antes y después en A y B y en C; "
        f"la calibración final, ajustada con las cuatro fotos, tiene b={config['calibracion']['final']['b']:.3f}"
        f"{aplicacion_calibracion}. La adopción se decide con A y B; 2024 es una prueba secundaria y no "
        "cambia automáticamente la variante publicada.",
        "## Sensibilidades (no eligen el modelo)",
        "Se mantienen columnas, ajustes y árboles. Mínimos 100/1,000 solo filtran entrenamiento. "
        "NS máximo 10%/20% filtra entrenamiento y evaluación por NS objetivo, con ambos métodos en la misma cohorte. "
        "NS como no voto cambia respuesta, nacional y referencia a (NV+NS)/LN, solo sin historial rearmado ni incompleto; "
        "se conserva la cohorte de A y los predictores históricos mantienen su definición base para aislar el cambio de respuesta. "
        "Sin 2012 usa las tres versiones *_sin_2012 que no son conteos y retira cambios presidenciales, distancia presidencial al país, "
        "composición, conteos y calidad que podrían incorporar 2012; estas últimas no tienen una alternativa canónica. "
        "El censo usa 2010 en 2015/2018: su antigüedad limita la extrapolación.",
        markdown(sensibilidad.loc[sensibilidad.segmento.eq("todos"),
            ["prueba", "metodo", "n_entrenamiento", "n_columnas", "n", "mae_pts", "mae_ponderado_pts", "nota"]]),
        "## Rango empírico nominal del 80%",
        "Se usa observado menos predicho en A, descontando lo que ya se sabe que falló el supuesto nacional de esa "
        f"prueba (nivel real de 2021 menos el de 2015: {config['rango']['error_nacional'] * 100:+.3f} pp), con "
        "percentiles 10/90 por tercil de conocidos_ultima. Así el rango mide solo el error municipal; la "
        "incertidumbre del país va en los escenarios de la sección siguiente. "
        "Se amplía hasta incluir el punto predicho cuando ambos percentiles tienen el mismo signo; "
        "se recorta a [0, 1]. Se calibra con el método publicado, incluido el respaldo si corresponde. "
        "La cobertura se mide sobre esos mismos residuos, con la misma corrección: es aparente, no una prueba "
        "independiente ni una garantía para 2027.",
        markdown(pd.DataFrame(config["rango"]["grupos"])),
        f"Cortes de tamaño: {config['rango']['cortes']}. Cobertura aparente: "
        f"{config['cobertura_rango_pct']:.3f}%. Ancho medio 2027: {config['ancho_rango_medio_pts']:.3f} pp.",
        "## Nivel nacional y escenarios",
        f"Nivel publicado para 2027: **{config['nivel_pais_supuesto'] * 100:.5f}%** "
        f"({config['nivel_pais_supuesto'] * 100:.2f}% redondeado), la última intermedia observada (2021). "
        "Se conserva por compatibilidad con la corrida anterior y con las cifras ya publicadas. "
        "Para el modelo se resuelve un desplazamiento constante para que la media con pesos conocidos_ultima "
        "coincida con ese nivel, incluso tras recortar. No se utiliza el nivel real de la elección que se evalúa "
        "para corregir las predicciones.",
        "La tabla siguiente separa observaciones, backtests y pronóstico. El backtest de 2015 repite 2009; "
        "el de 2021 prueba tanto la última intermedia como la tendencia lineal de las intermedias anteriores. "
        "La tendencia de 2027 se calcula solo con 2009, 2015 y 2021.",
        markdown(nivel_nacional),
        f"Escenarios alternativos: tendencia de intermedias **{config['nivel']['tendencia'] * 100:.3f}%** y "
        f"último cambio **{config['nivel']['cambio'] * 100:.3f}%**. No son observaciones de 2027 ni cambian "
        "la cifra publicada; sirven para mostrar cuánto depende el resultado municipal del supuesto nacional.",
        markdown(nivel_escenarios),
        f"Media ponderada publicada: **{config['media_publicada'] * 100:.5f}%**. "
        "Si se publica la referencia se respeta la repetición exacta: sus pesos actuales pueden cambiar la media.",
        "### Escenarios de ±5 pp",
        markdown(escenarios),
        "Los escenarios ±5 pp solo cambian el supuesto nacional, sin reentrenar ni simular una intervención. "
        "El rango municipal no incluye la incertidumbre sobre ese nivel: para eso están estos escenarios.",
        "## Explicación",
        ("Las razones municipales son los tres mayores aportes absolutos TreeSHAP del modelo final. "
         "Cada aporte suma/resta puntos de abstención a su distancia (en participación el signo se invierte); "
         "faltan la base SHAP, el desplazamiento nacional y, si se aplica, la recta de calibración "
         "para reconstruir la predicción completa. La calibración se ajusta sobre la distancia, así que "
         "las razones explican el candidato antes de calibrar. El recorte puede reducir el efecto final. "
         "La dirección global es la correlación entre valor y aporte; no demuestra causalidad."
         if config["gana"] else "Las razones publicadas describen la repetición histórica. "
         "La tabla siguiente explica únicamente el candidato LightGBM descartado, no la predicción publicada."),
        markdown(globales.head(10)),
        f"Base SHAP: {config['base_shap'] * 100:.5f} pp. Desplazamiento de centrado del candidato: "
        f"{config['ajuste_centrado'] * 100:.5f} pp.",
        "## Calidad y reproducción",
        markdown(pd.DataFrame([{"marca": c, "municipios": int(pred[c].sum())} for c in
            ("pocos_casos", "ns_alto", "historial_rearmado", "historial_incompleto", "sin_censo")])),
        "pocos_casos conserva la definición de menos de 500 personas conocidas en 2024, incluso si --minimo cambia. "
        "sin_censo marca ausencia completa de cobertura; censo_utilizado indica si sus variables entraron en el método publicado. "
        "Ninguna marca borra municipios ni se imputa una respuesta real.",
        "Limitación: cuatro fotos para ajustar y una sola intermedia para decidir; el rango y las importancias "
        "no sustituyen validación prospectiva. La adopción del ECEG y la cartografía siguen pendientes del equipo/INE.",
        "## Carpetas y archivos",
        "Para correr todo: `python ai/src/models/fase7.py`. Para revisarlo: `python -m unittest ai/tests/test_modelo.py`.",
        tabla(["Carpeta", "Qué guarda"], [
            ("`data/processed/`", "Lo que entra: las tres tablas de la Fase 3. El modelo solo las lee, y al terminar "
             "comprueba con huellas SHA256 que no cambiaron"),
            ("`ai/src/data_prep/`", "Piezas de las Fases 1 a 3 que el modelo reutiliza: rutas, listas de columnas y sus descripciones"),
            ("`ai/src/models/`", "El código de esta fase"),
            ("`ai/tests/`", "Las pruebas automáticas; `test_modelo.py` es la de esta fase"),
            ("`ai/artifacts/`", "Lo que sale: el modelo, las pruebas y las predicciones de 2027. Se versiona"),
            ("`docs/reports/`", "Este reporte, que se escribe leyendo las salidas"),
        ]),
        "**Lo que entra**, en `data/processed/`:",
        "- `tabla_municipios_entrenamiento.parquet`: las cuatro fotos (2015, 2018, 2021 y 2024). De aquí aprende "
        "el modelo y aquí se prueba.\n"
        "- `tabla_municipios_2027.parquet`: lo que se sabe hasta 2024 de cada municipio. Es la tabla que el modelo llena.\n"
        "- `municipio_eleccion.parquet`: los conteos de cada municipio en cada elección. De aquí salen el nivel del "
        "país y la variante que cuenta el NS como no voto.",
        "**El código**, en `ai/src/models/`:",
        "- `fase7.py`: el script que se corre. Hace todo en orden y escribe las salidas y este reporte.\n"
        "- `datos_modelo.py`: lee las tablas, calcula la distancia contra el país, arma los bloques de columnas "
        "y dice cuáles no pueden entrar.\n"
        "- `validacion.py`: entrena LightGBM, elige columnas y ajustes con 2015 y 2018, corre las pruebas, "
        "calcula los errores, el rango y los intervalos bootstrap.\n"
        "- `calibracion.py`: genera predicciones fuera de fold y ajusta la recta de calibración sobre distancias.\n"
        "- `nivel.py`: resume el nivel nacional, sus backtests y los escenarios de tendencia.\n"
        "- `explicacion.py`: calcula cuánto aporta cada columna y las tres razones de cada municipio.",
        "**Lo que sale**, en `ai/artifacts/`:",
        tabla(["Archivo", "Qué guarda"], [(" y ".join(f"`{n}`" for n in nombres), texto)
                                          for nombres, texto in ARCHIVOS_SALIDA]),
    ]
    return "\n\n".join(partes) + "\n"


def ejecutar(args, salida):
    lightgbm()
    base, train, pred, fuentes = cargar()
    nacional = niveles_pais(base)
    entrenamiento = filas_entrenables(train.loc[train.eleccion_objetivo.isin([2015, 2018])], args.minimo)
    opciones = bloques(args.sin_censo)
    print("Seleccionando únicamente con 2015 y 2018…", flush=True)
    columnas, parametros, arboles, bloque, seleccion = seleccionar(entrenamiento, opciones)
    # Desde aquí quedan congeladas las decisiones, antes de evaluar 2021.
    guardar(seleccion, salida / "seleccion_columnas.csv")
    congelado = dict(columnas=columnas, parametros=parametros, arboles=arboles, bloque=bloque,
                     fotos_seleccion=[2015, 2018])
    escribir_json(salida / "seleccion_congelada.json", congelado)
    prueba = train.loc[train.eleccion_objetivo.eq(2021)].copy()
    prueba_c = train.loc[train.eleccion_objetivo.eq(2024)].copy()
    validar_referencia(prueba)

    print("Calibrando con predicciones fuera de fold…", flush=True)
    def _oof(anios, nombre):
        print(f"  OOF {nombre}: {' '.join(map(str, anios))}", flush=True)
        foto = filas_entrenables(train.loc[train.eleccion_objetivo.isin(anios)], args.minimo)
        return predicciones_oof(foto, columnas, parametros, arboles)

    # Los estados se separan sobre las fotos agrupadas: el fold nunca mezcla un
    # estado entre entrenamiento y validación, pero sí ambas fotos de los demás.
    oof_ab = _oof([2015, 2018], "A/B")
    oof_c = _oof([2015, 2018, 2021], "C")
    oof_final = _oof([2015, 2018, 2021, 2024], "final")
    oof = pd.concat([
        oof_ab.assign(conjunto="ajuste_2015_2018"),
        oof_c.assign(conjunto="ajuste_2015_2021"),
        oof_final.assign(conjunto="ajuste_2015_2024"),
    ], ignore_index=True)
    guardar(oof, salida / "predicciones_oof.csv")
    cal_ab = _calibrar(oof_ab)
    cal_c = _calibrar(oof_c)
    cal_final = _calibrar(oof_final)

    print("Evaluando A (2021) y B (estados)…", flush=True)
    modelo_a = entrenar(entrenamiento, columnas, parametros, arboles)
    dist_a = modelo_a.predict(matriz(prueba, columnas))
    pred_a_sin, _ = centrar(dist_a, prueba.conocidos_ultima, float(nacional.loc[2015]))
    pred_a_cal, _ = centrar(aplicar(dist_a, cal_ab), prueba.conocidos_ultima,
                            float(nacional.loc[2015]))
    distancias_b, folds = np.empty(len(prueba)), np.zeros(len(prueba), dtype=int)
    for fold, (_, j) in enumerate(particiones_estados(prueba, 8), 1):
        estados = set(prueba.iloc[j].EDOCVE)
        t = entrenamiento.loc[~entrenamiento.EDOCVE.isin(estados)]
        modelo_b = entrenar(t, columnas, parametros, arboles)
        distancias_b[j] = modelo_b.predict(matriz(prueba.iloc[j], columnas))
        folds[j] = fold
    pred_b_sin, _ = centrar(distancias_b, prueba.conocidos_ultima, float(nacional.loc[2015]))
    pred_b_cal, _ = centrar(aplicar(distancias_b, cal_ab), prueba.conocidos_ultima,
                            float(nacional.loc[2015]))
    modelo_c = entrenar(filas_entrenables(train.loc[train.eleccion_objetivo.le(2021)], args.minimo),
                        columnas, parametros, arboles)
    dist_c = modelo_c.predict(matriz(prueba_c, columnas))
    pred_c_sin, _ = centrar(dist_c, prueba_c.conocidos_ultima, float(nacional.loc[2018]))
    pred_c_cal, _ = centrar(aplicar(dist_c, cal_c), prueba_c.conocidos_ultima,
                            float(nacional.loc[2018]))

    val_sin = _evaluar_variantes(prueba, prueba_c, pred_a_sin, pred_b_sin, pred_c_sin)
    val_cal = _evaluar_variantes(prueba, prueba_c, pred_a_cal, pred_b_cal, pred_c_cal)
    gana_sin, gana_cal = gana(val_sin), gana(val_cal)
    if gana_cal:
        variante = "calibrado"
    elif gana_sin:
        variante = "sin_calibrar"
    else:
        variante = "punto_de_partida"
    metodo = "punto de partida" if variante == "punto_de_partida" else "modelo"
    aprobado = metodo == "modelo"
    print(f"Variante elegida: {variante}", flush=True)

    if variante == "calibrado":
        validacion, pred_a, pred_b, pred_c = val_cal, pred_a_cal, pred_b_cal, pred_c_cal
    elif variante == "sin_calibrar":
        validacion, pred_a, pred_b, pred_c = val_sin, pred_a_sin, pred_b_sin, pred_c_sin
    else:
        pred_a = prueba.referencia.to_numpy(float)
        pred_b = prueba.referencia.to_numpy(float)
        pred_c = prueba_c.referencia.to_numpy(float)
        validacion = _evaluar_variantes(prueba, prueba_c, pred_a, pred_b, pred_c)
    regla = regla_2024(validacion)
    regla_cal = regla_2024(val_cal)
    guardar(validacion, salida / "validacion.csv")
    predicciones = [
        registro_predicciones(prueba, pred_a, "A_2021", sin_calibrar=pred_a_sin,
                              calibrada=pred_a_cal),
        registro_predicciones(prueba, pred_b, "B_estados", folds, sin_calibrar=pred_b_sin,
                              calibrada=pred_b_cal),
        registro_predicciones(prueba_c, pred_c, "C_2024", sin_calibrar=pred_c_sin,
                              calibrada=pred_c_cal),
    ]
    guardar(pd.concat(predicciones, ignore_index=True), salida / "predicciones_pruebas.csv")
    guardar(sensibilidades(train.loc[train.eleccion_objetivo.isin([2015, 2018])], prueba,
        base, columnas, parametros, arboles, args.minimo, float(nacional.loc[2015]), args.sin_censo),
        salida / "sensibilidades.csv")

    print("Calculando intervalos bootstrap…", flush=True)
    bootstrap = []
    for nombre, foto, pred_elegida in (("A_2021", prueba, pred_a),
                                        ("B_estados", prueba, pred_b),
                                        ("C_2024", prueba_c, pred_c)):
        bootstrap.append(dict(prueba=nombre, variante=variante, **bootstrap_diferencia(
            foto, pred_elegida, foto.referencia.to_numpy(float), n=2000, semilla=2027)))
    guardar(pd.DataFrame(bootstrap), salida / "validacion_bootstrap.csv")

    print("Registrando calibración antes y después…", flush=True)
    filas_cal = []
    for nombre, anios, cal, conjunto in (
        ("ajuste_2015_2018", (2015, 2018), cal_ab, oof_ab),
        ("ajuste_2015_2021", (2015, 2018, 2021), cal_c, oof_c),
        ("ajuste_2015_2024", (2015, 2018, 2021, 2024), cal_final, oof_final),
    ):
        y = conjunto.distancia_objetivo.to_numpy(float)
        w = conjunto.conocidos_objetivo.to_numpy(float)
        filas_cal.append(_fila_calibracion(nombre, "sin_calibrar", y,
                                          conjunto.distancia_pred, w, anios, None, "distancia"))
        filas_cal.append(_fila_calibracion(nombre, "calibrado", y,
                                          aplicar(conjunto.distancia_pred, cal), w, anios, cal,
                                          "distancia"))
    for nombre, foto, p_sin, p_cal, cal, anios in (
        ("A_2021", prueba, pred_a_sin, pred_a_cal, cal_ab, (2015, 2018)),
        ("B_estados", prueba, pred_b_sin, pred_b_cal, cal_ab, (2015, 2018)),
        ("C_2024", prueba_c, pred_c_sin, pred_c_cal, cal_c, (2015, 2018, 2021)),
    ):
        elegibles = foto.abstencion_objetivo.notna() & foto.referencia.notna()
        y = foto.loc[elegibles, "abstencion_objetivo"].to_numpy(float)
        w = foto.loc[elegibles, "conocidos_objetivo"].to_numpy(float)
        filas_cal.append(_fila_calibracion(nombre, "sin_calibrar", y, p_sin[elegibles], w,
                                          anios, None))
        filas_cal.append(_fila_calibracion(nombre, "calibrado", y, p_cal[elegibles], w,
                                          anios, cal))
    guardar(pd.DataFrame(filas_cal), salida / "calibracion.csv")

    evaluables = prueba.abstencion_objetivo.notna() & prueba.referencia.notna()
    pred_calibracion = pred_a[evaluables]
    # Ambos métodos parten del nivel de 2015; lo que ese supuesto falló en 2021 no se
    # traslada al rango de 2027, que solo mide el error municipal.
    error_nacional = float(nacional.loc[2021] - nacional.loc[2015])
    calibracion = calibrar_rango(prueba.loc[evaluables], pred_calibracion, error_nacional)
    minimo_a, maximo_a = aplicar_rango(pred_calibracion, prueba.loc[evaluables, "conocidos_ultima"],
                                       calibracion)
    y_a = prueba.loc[evaluables, "abstencion_objetivo"].to_numpy() - error_nacional
    cobertura = float(((minimo_a <= y_a) & (y_a <= maximo_a)).mean() * 100)

    print(f"Método publicado: {metodo} ({variante}). Entrenando candidato final…", flush=True)
    modelo_final = entrenar(filas_entrenables(train, args.minimo), columnas, parametros, arboles)
    modelo_final.save_model(str(salida / "modelo_2027.txt"))
    nivel = float(nacional.loc[2021])
    distancias_finales = modelo_final.predict(matriz(pred, columnas))
    distancias_publicadas = (aplicar(distancias_finales, cal_final)
                             if variante == "calibrado" else distancias_finales)
    candidato, ajuste = centrar(distancias_publicadas, pred.conocidos_ultima, nivel)
    razones, globales, base_shap = explicar(modelo_final, pred, columnas)
    guardar(globales, salida / "explicacion_global.csv")
    publicada = candidato if aprobado else pred.referencia.to_numpy(float)
    if not aprobado:
        razones = explicar_referencia(pred)
    resultado = construir_salida(pred, publicada, calibracion, metodo, nivel, razones,
                                 aprobado and bool(set(columnas) & set(BLOQUE_C)),
                                 calibrado=variante == "calibrado")
    guardar(resultado, salida / "predicciones_2027.csv")
    guardar(resultado, salida / "predicciones_2027.parquet")

    nivel_info = analizar_nivel(nacional, objetivo=2027)
    guardar(tabla_nacional(nacional, nivel_info), salida / "nivel_nacional.csv")
    filas_nivel = []
    for escenario in tabla_escenarios(nivel_info).itertuples(index=False):
        valores = _prediccion_de_nivel(float(escenario.nivel_pct) / 100, publicada, nivel,
                                       aprobado, distancias_publicadas, pred.conocidos_ultima)
        filas_nivel.append(dict(
            escenario=escenario.escenario, metodo=escenario.metodo,
            nivel_pct=float(escenario.nivel_pct),
            diferencia_vs_publicado_pts=float(escenario.diferencia_vs_publicado_pts),
            abstencion_media_ponderada_pct=float(np.average(valores, weights=pred.conocidos_ultima) * 100),
            abstencion_mediana_pct=float(np.median(valores) * 100),
            abstencion_min_pct=float(valores.min() * 100),
            abstencion_max_pct=float(valores.max() * 100),
            participacion_media_ponderada_pct=float(np.average(1 - valores, weights=pred.conocidos_ultima) * 100),
            nota=escenario.nota,
        ))
    guardar(pd.DataFrame(filas_nivel), salida / "nivel_escenarios.csv")

    escenarios = []
    for cambio in (-0.05, 0, 0.05):
        valores = _prediccion_de_nivel(nivel + cambio, publicada, nivel, aprobado,
                                       distancias_publicadas, pred.conocidos_ultima)
        escenarios.append(dict(cambio_nivel_pts=cambio * 100, nivel_supuesto_pct=(nivel + cambio) * 100,
            abstencion_media_ponderada_pct=float(np.average(valores, weights=pred.conocidos_ultima) * 100),
            participacion_media_ponderada_pct=float(np.average(1 - valores, weights=pred.conocidos_ultima) * 100)))
    guardar(pd.DataFrame(escenarios), salida / "escenarios_nivel.csv")
    if any(huella(RAIZ / ruta) != valor for ruta, valor in fuentes.items()):
        raise ValueError("Una tabla fuente cambió durante la ejecución; no se publican resultados")

    calibracion_config = dict(
        variante=variante, aplicada=variante == "calibrado",
        a_b={**cal_ab, "fotos": [2015, 2018]},
        c={**cal_c, "fotos": [2015, 2018, 2021]},
        final={**cal_final, "fotos": [2015, 2018, 2021, 2024]},
    )
    nivel_config = dict(
        publicado=float(nivel_info["publicado"]), tendencia=float(nivel_info["tendencia"]),
        cambio=float(nivel_info["cambio"]), objetivo=int(nivel_info["objetivo"]),
        intermedios=[int(a) for a in nivel_info["intermedios"]],
        backtest=json.loads(nivel_info["backtest"].to_json(orient="records")),
    )
    config = dict(**congelado, parametros_fijos=FIJOS, minimo=args.minimo, sin_censo=args.sin_censo,
        gana=aprobado, gana_calibrado=bool(gana_cal), gana_sin_calibrar=bool(gana_sin),
        metodo=metodo, variante=variante, calibracion_aplicada=variante == "calibrado",
        calibracion=calibracion_config, regla_2024=regla, regla_2024_calibrado=regla_cal,
        nivel_pais_supuesto=nivel, nivel=nivel_config,
        media_publicada=float(np.average(publicada, weights=pred.conocidos_ultima)),
        base_shap=base_shap, ajuste_centrado=ajuste, rango=calibracion,
        cobertura_rango_pct=cobertura,
        ancho_rango_medio_pts=float((resultado.abstencion_max - resultado.abstencion_min).mean() * 100),
        fuentes_sha256=fuentes, python=platform.python_version(), plataforma=platform.platform(),
        versiones={p: importlib.metadata.version(p) for p in ("lightgbm", "numpy", "pandas", "scipy", "scikit-learn", "pyarrow")},
        codigo_sha256={str(p.relative_to(RAIZ)): huella(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        artefactos_sha256={p.name: huella(p) for p in sorted(salida.iterdir()) if p.is_file()},
        filas_por_foto=[dict(foto=int(anio), filas=len(s), sin_respuesta=int(s.abstencion_objetivo.isna().sum()),
            entrenables=len(filas_entrenables(s, args.minimo))) for anio, s in train.groupby("eleccion_objetivo")],
        calidad_por_foto=[dict(foto=int(anio), rearmados=int(s.historial_rearmado.sum()),
            incompletos=int(s.historial_incompleto.sum()),
            rearmados_evaluables=int((s.historial_rearmado & s.abstencion_objetivo.notna() & s.referencia.notna()).sum()),
            incompletos_evaluables=int((s.historial_incompleto & s.abstencion_objetivo.notna() & s.referencia.notna()).sum()))
            for anio, s in train.groupby("eleccion_objetivo")],
        nacionales=[dict(eleccion=int(anio), abstencion_pct=float(tasa * 100)) for anio, tasa in nacional.items()],
        decisiones=dict(ns="fuera", conservar_2012=True, rearmados="incluir y evaluar aparte",
                        respuestas_ausentes="excluir", censo="candidato pendiente de decisión del equipo",
                        calibracion="Huber sobre distancia con predicciones fuera de fold; respaldo lineal"))
    escribir_json(salida / "modelo_config.json", config)
    return reporte_desde_archivos(salida), config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sin-censo", action="store_true", help="Excluir completamente el bloque ECEG")
    parser.add_argument("--minimo", type=int, default=500, help="Mínimo de conocidos del objetivo al entrenar")
    args = parser.parse_args(argv)
    if args.minimo < 1:
        parser.error("--minimo debe ser positivo")
    try:
        ARTIFACTOS.mkdir(parents=True, exist_ok=True)
        REPORTES.mkdir(parents=True, exist_ok=True)
        # Ninguna corrida fallida sustituye artefactos válidos anteriores.
        with tempfile.TemporaryDirectory(prefix=".fase7-", dir=ARTIFACTOS) as temporal:
            salida = Path(temporal)
            reporte, config = ejecutar(args, salida)
            temporal_reporte = salida / "reporte_modelo.md"
            temporal_reporte.write_text(reporte, encoding="utf-8")
            for archivo in sorted(salida.iterdir()):
                if archivo != temporal_reporte:
                    archivo.replace(ARTIFACTOS / archivo.name)
            temporal_reporte.replace(REPORTE)
    except (ValueError, FileNotFoundError) as exc:
        detener(str(exc))
    print(f"Listo: {config['metodo']}; predicciones en ai/artifacts y reporte en {REPORTE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
