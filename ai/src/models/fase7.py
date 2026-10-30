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
from validacion import (
    FIJOS, aplicar_rango, calibrar_rango, centrar, entrenar, evaluar, gana,
    lightgbm, particiones_estados, predecir, seleccionar,
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
]


def escribir_json(ruta, contenido):
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2, sort_keys=True,
                               allow_nan=False) + "\n", encoding="utf-8")


def registro_predicciones(foto, prediccion, prueba, fold=0):
    columnas = [*LLAVE, "eleccion_objetivo", "abstencion_objetivo", "referencia",
                "conocidos_objetivo", "conocidos_ultima", "historial_rearmado", "historial_incompleto"]
    salida = foto[columnas].copy()
    salida["modelo_pred"] = np.asarray(prediccion)
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


def construir_salida(foto, prediccion, calibracion, metodo, nivel, razones, usa_censo):
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

    decision = ("LightGBM supera al punto de partida en los cuatro errores exigidos."
                if config["gana"] else
                "LightGBM no supera las cuatro condiciones. Se publica el punto de partida: repetir la última intermedia.")
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
        "# Reporte del modelo municipal (Fase 7)", decision,
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
        "ajustes o árboles. La evaluación de 2021 se ejecuta después de congelarlos.",
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
        "### Municipios con cambios territoriales",
        "Las marcas rearmado e incompleto pueden solaparse.",
        markdown(pd.DataFrame(config["calidad_por_foto"])),
        markdown(validacion.loc[validacion.segmento.ne("todos"), ["prueba", "segmento", *metricas[1:]]]),
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
        "## Supuesto nacional y escenarios",
        f"Nivel nacional supuesto 2027: **{config['nivel_pais_supuesto'] * 100:.5f}%**, "
        "calculado con 2021 (48.16% redondeado). Para el modelo se resuelve un desplazamiento constante "
        "para que la media con pesos conocidos_ultima coincida con ese nivel, incluso tras recortar. "
        "No se utiliza el nivel real de la elección que se evalúa para corregir las predicciones.",
        f"Media ponderada publicada: **{config['media_publicada'] * 100:.5f}%**. "
        "Si se publica la referencia se respeta la repetición exacta: sus pesos actuales pueden cambiar la media.",
        markdown(escenarios),
        "Los escenarios ±5 pp solo cambian el supuesto nacional, sin reentrenar ni simular una intervención. "
        "El rango municipal no incluye la incertidumbre sobre ese nivel: para eso están estos escenarios.",
        "## Explicación",
        ("Las razones municipales son los tres mayores aportes absolutos TreeSHAP del modelo final. "
         "Cada aporte suma/resta puntos de abstención a su distancia (en participación el signo se invierte); "
         "faltan la base SHAP y el desplazamiento nacional "
         "para reconstruir la predicción completa. El recorte puede reducir el efecto final. "
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
        "- `validacion.py`: entrena LightGBM, elige columnas y ajustes con 2015 y 2018, corre las pruebas y "
        "calcula los errores y el rango.\n"
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
    validar_referencia(prueba)
    print("Evaluando A (2021) y B (estados)…", flush=True)
    modelo_a = entrenar(entrenamiento, columnas, parametros, arboles)
    pred_a, _ = predecir(modelo_a, prueba, columnas, float(nacional.loc[2015]))
    validaciones = [evaluar(prueba, pred_a, "A_2021")]
    predicciones = [registro_predicciones(prueba, pred_a, "A_2021")]
    distancias_b, folds = np.empty(len(prueba)), np.zeros(len(prueba), dtype=int)
    for fold, (_, j) in enumerate(particiones_estados(prueba, 8), 1):
        estados = set(prueba.iloc[j].EDOCVE)
        t = entrenamiento.loc[~entrenamiento.EDOCVE.isin(estados)]
        modelo_b = entrenar(t, columnas, parametros, arboles)
        distancias_b[j] = modelo_b.predict(matriz(prueba.iloc[j], columnas))
        folds[j] = fold
    pred_b, _ = centrar(distancias_b, prueba.conocidos_ultima, float(nacional.loc[2015]))
    validaciones.append(evaluar(prueba, pred_b, "B_estados"))
    predicciones.append(registro_predicciones(prueba, pred_b, "B_estados", folds))
    prueba_c = train.loc[train.eleccion_objetivo.eq(2024)]
    modelo_c = entrenar(filas_entrenables(train.loc[train.eleccion_objetivo.le(2021)], args.minimo),
                        columnas, parametros, arboles)
    pred_c, _ = predecir(modelo_c, prueba_c, columnas, float(nacional.loc[2018]))
    validaciones.append(evaluar(prueba_c, pred_c, "C_2024"))
    predicciones.append(registro_predicciones(prueba_c, pred_c, "C_2024"))
    validacion = pd.concat(validaciones, ignore_index=True)
    guardar(validacion, salida / "validacion.csv")
    guardar(pd.concat(predicciones, ignore_index=True), salida / "predicciones_pruebas.csv")
    guardar(sensibilidades(train.loc[train.eleccion_objetivo.isin([2015, 2018])], prueba,
        base, columnas, parametros, arboles, args.minimo, float(nacional.loc[2015]), args.sin_censo),
        salida / "sensibilidades.csv")

    aprobado = gana(validacion)
    metodo = "modelo" if aprobado else "punto de partida"
    evaluables = prueba.abstencion_objetivo.notna() & prueba.referencia.notna()
    pred_calibracion = pred_a[evaluables] if aprobado else prueba.loc[evaluables, "referencia"].to_numpy()
    # Ambos métodos parten del nivel de 2015; lo que ese supuesto falló en 2021 no se
    # traslada al rango de 2027, que solo mide el error municipal.
    error_nacional = float(nacional.loc[2021] - nacional.loc[2015])
    calibracion = calibrar_rango(prueba.loc[evaluables], pred_calibracion, error_nacional)
    minimo_a, maximo_a = aplicar_rango(pred_calibracion, prueba.loc[evaluables, "conocidos_ultima"], calibracion)
    y_a = prueba.loc[evaluables, "abstencion_objetivo"].to_numpy() - error_nacional
    cobertura = float(((minimo_a <= y_a) & (y_a <= maximo_a)).mean() * 100)

    print(f"Método elegido: {metodo}. Entrenando candidato final…", flush=True)
    modelo_final = entrenar(filas_entrenables(train, args.minimo), columnas, parametros, arboles)
    modelo_final.save_model(str(salida / "modelo_2027.txt"))
    nivel = float(nacional.loc[2021])
    candidato, ajuste = predecir(modelo_final, pred, columnas, nivel)
    razones, globales, base_shap = explicar(modelo_final, pred, columnas)
    guardar(globales, salida / "explicacion_global.csv")
    publicada = candidato if aprobado else pred.referencia.to_numpy(float)
    if not aprobado:
        razones = explicar_referencia(pred)
    resultado = construir_salida(pred, publicada, calibracion, metodo, nivel, razones,
                                 aprobado and bool(set(columnas) & set(BLOQUE_C)))
    guardar(resultado, salida / "predicciones_2027.csv")
    guardar(resultado, salida / "predicciones_2027.parquet")
    escenarios = []
    for cambio in (-0.05, 0, 0.05):
        if aprobado:
            valores, _ = centrar(modelo_final.predict(matriz(pred, columnas)), pred.conocidos_ultima, nivel + cambio)
        else:
            valores = np.clip(publicada + cambio, 0, 1)
        escenarios.append(dict(cambio_nivel_pts=cambio * 100, nivel_supuesto_pct=(nivel + cambio) * 100,
            abstencion_media_ponderada_pct=float(np.average(valores, weights=pred.conocidos_ultima) * 100),
            participacion_media_ponderada_pct=float(np.average(1 - valores, weights=pred.conocidos_ultima) * 100)))
    guardar(pd.DataFrame(escenarios), salida / "escenarios_nivel.csv")
    if any(huella(RAIZ / ruta) != valor for ruta, valor in fuentes.items()):
        raise ValueError("Una tabla fuente cambió durante la ejecución; no se publican resultados")
    config = dict(**congelado, parametros_fijos=FIJOS, minimo=args.minimo, sin_censo=args.sin_censo,
        gana=aprobado, metodo=metodo, nivel_pais_supuesto=nivel,
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
                        respuestas_ausentes="excluir", censo="candidato pendiente de decisión del equipo"))
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
