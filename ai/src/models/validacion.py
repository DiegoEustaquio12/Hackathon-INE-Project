"""Selección previa a 2021, evaluación por estados y rangos empíricos."""
import itertools

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from datos_modelo import matriz, solo_seleccion

FIJOS = dict(
    learning_rate=0.03, feature_fraction=0.8, bagging_fraction=0.8,
    bagging_freq=1, seed=2027, feature_fraction_seed=2027,
    bagging_seed=2027, data_random_seed=2027, deterministic=True,
    force_row_wise=True, num_threads=4, verbosity=-1, metric="l1",
)
INICIALES = dict(num_leaves=15, min_data_in_leaf=50, objective="regression")


def lightgbm():
    try:
        import lightgbm as lgb
    except (ImportError, OSError) as exc:
        raise ValueError(
            "No se pudo cargar LightGBM. Instala ai/requirements.txt; "
            "en macOS ejecuta brew install libomp."
        ) from exc
    return lgb


def particiones_estados(foto, grupos=5):
    if foto.EDOCVE.nunique() < grupos:
        raise ValueError("No hay suficientes estados para la validación")
    for entrenamiento, prueba in GroupKFold(n_splits=grupos).split(foto, groups=foto.EDOCVE):
        if set(foto.iloc[entrenamiento].EDOCVE) & set(foto.iloc[prueba].EDOCVE):
            raise ValueError("Un estado aparece en entrenamiento y validación")
        yield entrenamiento, prueba


def entrenar(foto, columnas, parametros, arboles, validacion=None):
    lgb = lightgbm()
    datos = lgb.Dataset(matriz(foto, columnas), label=foto.distancia_objetivo.to_numpy(float))
    opciones = {}
    if validacion is not None:
        opciones = dict(
            valid_sets=[lgb.Dataset(matriz(validacion, columnas),
                label=validacion.distancia_objetivo.to_numpy(float), reference=datos)],
            callbacks=[lgb.early_stopping(100, verbose=False)],
        )
    # Sin weight: cada municipio cuenta igual en el ajuste y el paro temprano.
    return lgb.train({**FIJOS, **parametros}, datos, num_boost_round=arboles, **opciones)


def _entrenar_anidado(foto, columnas, parametros, i, j, grupos_internos=4):
    """Early stopping dentro del fold de entrenamiento, nunca en el fold externo."""
    externo = foto.iloc[i]
    grupos = min(grupos_internos, externo.EDOCVE.nunique())
    if grupos < 2:
        raise ValueError("Se necesitan al menos dos estados para la validación interna")
    i_in, j_in = next(particiones_estados(externo, grupos))
    modelo = entrenar(externo.iloc[i_in], columnas, parametros, 3000,
                      externo.iloc[j_in])
    arboles = max(1, int(modelo.best_iteration))
    final = entrenar(externo, columnas, parametros, arboles)
    return final, arboles


def seleccionar(foto, opciones):
    solo_seleccion(foto)
    resultados = []

    def probar(etapa, bloque, columnas, parametros, candidato):
        errores, iteraciones = [], []
        for numero, (i, j) in enumerate(particiones_estados(foto), 1):
            modelo, arboles = _entrenar_anidado(foto, columnas, parametros, i, j)
            error = np.abs(modelo.predict(matriz(foto.iloc[j], columnas))
                           - foto.iloc[j].distancia_objetivo.to_numpy(float))
            errores.extend(error)
            iteraciones.append(arboles)
            resultados.append(dict(
                etapa=etapa, candidato=candidato, bloque=bloque, fold=numero,
                n_columnas=len(columnas), n_entrenamiento=len(i), n_validacion=len(j),
                estados_validacion=" ".join(map(str, sorted(foto.iloc[j].EDOCVE.unique()))),
                fotos="2015 2018", mae_distancia_pts=float(error.mean() * 100),
                arboles=arboles, **parametros,
            ))
        return float(np.mean(errores)), max(1, int(np.median(iteraciones)))

    bloques = []
    for nombre, columnas in opciones.items():
        print(f"  Selección de columnas: {nombre} ({len(columnas)})", flush=True)
        error, arboles = probar("columnas", nombre, columnas, INICIALES, nombre)
        bloques.append((error, nombre, arboles))
    _, bloque, _ = min(bloques, key=lambda x: x[0])
    columnas = opciones[bloque]
    ajustes = []
    for candidato, (hojas, minimo, objetivo) in enumerate(itertools.product(
        (7, 15, 31), (20, 50, 100), ("regression", "regression_l1")
    ), 1):
        parametros = dict(num_leaves=hojas, min_data_in_leaf=minimo, objective=objetivo)
        error, arboles = probar("ajustes", bloque, columnas, parametros, str(candidato))
        ajustes.append((error, candidato, parametros, arboles))
        print(f"  Ajuste {candidato}/18: MAE distancia {error * 100:.3f} pp", flush=True)
    _, candidato, parametros, arboles = min(ajustes, key=lambda x: x[0])
    resumen = pd.DataFrame(resultados)
    resumen["elegido"] = ((resumen.etapa.eq("columnas") & resumen.bloque.eq(bloque))
        | (resumen.etapa.eq("ajustes") & resumen.candidato.eq(str(candidato))))
    return columnas, parametros, arboles, bloque, resumen


def centrar(distancias, pesos, nivel):
    """Desplaza el vector y recorta resolviendo la media, incluso con saturación.

    El desplazamiento usa exclusivamente tamaños históricos, nunca respuestas.
    Bisección evita que recortar a [0, 1] altere la media nacional supuesta.
    """
    d, w = np.asarray(distancias, float), np.asarray(pesos, float)
    if not np.isfinite(d).all() or not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("Distancias o pesos de centrado inválidos")
    if not 0 <= nivel <= 1:
        raise ValueError("El nivel nacional debe estar entre cero y uno")
    inferior, superior = -float(d.max()) - 1, 1 - float(d.min()) + 1
    for _ in range(80):
        desplazamiento = (inferior + superior) / 2
        if np.average(np.clip(nivel + d + desplazamiento, 0, 1), weights=w) < nivel:
            inferior = desplazamiento
        else:
            superior = desplazamiento
    desplazamiento = (inferior + superior) / 2
    return np.clip(nivel + d + desplazamiento, 0, 1), desplazamiento


def predecir(modelo, foto, columnas, nivel):
    return centrar(modelo.predict(matriz(foto, columnas)), foto.conocidos_ultima, nivel)


def tercios(valores):
    """0, 1 o 2 según el tercio dentro de los propios valores (2 = más abstención)."""
    v = np.asarray(valores, float)
    return np.searchsorted(np.quantile(v, [1 / 3, 2 / 3]), v, side="right")


def metricas(real, prediccion, pesos):
    y, p, w = [np.asarray(v, float) for v in (real, prediccion, pesos)]
    if not len(y) or not (np.isfinite(y) & np.isfinite(p) & np.isfinite(w)).all():
        raise ValueError("Métricas sin observaciones o con valores no finitos")
    if (w < 0).any() or w.sum() <= 0:
        raise ValueError("Pesos de evaluación inválidos")
    error = np.abs(y - p)
    # Cada método se parte en sus propios tercios, como el semáforo por orden: así el
    # error del nivel nacional, igual para todos los municipios, no cambia el color.
    color_real, color_pred = tercios(y), tercios(p)
    rojos = color_real == 2
    orden = (pd.Series(y).corr(pd.Series(p), method="spearman")
             if np.std(y) > 0 and np.std(p) > 0 else np.nan)
    return dict(n=len(y), mae_pts=float(error.mean() * 100),
        mae_ponderado_pts=float(np.average(error, weights=w) * 100),
        spearman=float(orden) if np.isfinite(orden) else None,
        mismo_tercio_pct=float((color_real == color_pred).mean() * 100),
        rojos_detectados_pct=float((color_pred[rojos] == 2).mean() * 100) if rojos.any() else None)


def evaluar(foto, prediccion, prueba):
    """Ambos métodos se comparan siempre en exactamente las mismas filas."""
    copia = foto.copy()
    copia["modelo_pred"] = np.asarray(prediccion)
    copia = copia.dropna(subset=["abstencion_objetivo", "referencia", "modelo_pred"])
    filas = []
    segmentos = {
        "todos": np.ones(len(copia), bool),
        "rearmado": copia.historial_rearmado,
        "incompleto": copia.historial_incompleto,
        "sin_marcas": ~copia.historial_rearmado & ~copia.historial_incompleto,
    }
    for segmento, mascara in segmentos.items():
        s = copia.loc[mascara]
        if s.empty:
            continue
        for metodo, columna in (("modelo", "modelo_pred"), ("punto de partida", "referencia")):
            filas.append(dict(prueba=prueba, segmento=segmento, metodo=metodo,
                **metricas(s.abstencion_objetivo, s[columna], s.conocidos_objetivo)))
    return pd.DataFrame(filas)


def gana(validacion):
    for prueba in ("A_2021", "B_estados"):
        s = validacion.loc[validacion.prueba.eq(prueba) & validacion.segmento.eq("todos")]
        if len(s) != 2 or set(s.metodo) != {"modelo", "punto de partida"}:
            return False
        s = s.set_index("metodo")
        for columna in ("mae_pts", "mae_ponderado_pts"):
            if not s.loc["modelo", columna] < s.loc["punto de partida", columna]:
                return False
    return True


def regla_2024(validacion, tolerancia=0.3):
    """Prueba secundaria: no debe empeorar más de ``tolerancia`` puntos."""
    s = validacion.loc[validacion.prueba.eq("C_2024") & validacion.segmento.eq("todos")]
    if len(s) != 2 or set(s.metodo) != {"modelo", "punto de partida"}:
        raise ValueError("La prueba 2024 necesita modelo y punto de partida")
    s = s.set_index("metodo")
    diferencia = float(s.loc["modelo", "mae_pts"] - s.loc["punto de partida", "mae_pts"])
    cumple = bool(diferencia <= tolerancia)
    return dict(
        diferencia_pts=diferencia,
        tolerancia_pts=float(tolerancia),
        cumple=cumple,
        mae_modelo_pts=float(s.loc["modelo", "mae_pts"]),
        mae_referencia_pts=float(s.loc["punto de partida", "mae_pts"]),
        recomendacion=("mantener la adopción" if cumple else
                       "evaluar una mezcla con el punto de partida o un modelo más simple; "
                       "no cambiar automáticamente la adopción"),
    )


def bootstrap_diferencia(foto, pred_modelo, pred_referencia, n=5000, semilla=2027,
                         por_estado=True):
    """IC bootstrap pareado para MAE modelo − punto de partida.

    Por estado es más conservador: respeta la dependencia espacial. También
    devuelve la versión simple y la ponderada por conocidos del objetivo.
    """
    y = foto.abstencion_objetivo.to_numpy(float)
    pm = np.asarray(pred_modelo, dtype=float)
    pr = np.asarray(pred_referencia, dtype=float)
    w = foto.conocidos_objetivo.to_numpy(float)
    valido = np.isfinite(y) & np.isfinite(pm) & np.isfinite(pr) & np.isfinite(w)
    y, pm, pr, w = y[valido], pm[valido], pr[valido], w[valido]
    if not len(y):
        raise ValueError("No hay filas para el bootstrap")
    grupos = foto.EDOCVE.to_numpy()[valido]
    rng = np.random.default_rng(semilla)

    if por_estado:
        unicos, inverse = np.unique(grupos, return_inverse=True)
        indices = [np.flatnonzero(inverse == k) for k in range(len(unicos))]

        def muestra():
            return np.concatenate([indices[k] for k in rng.integers(0, len(unicos), len(unicos))])
    else:
        def muestra():
            return rng.integers(0, len(y), len(y))

    simple, ponderado = [], []
    for _ in range(n):
        idx = muestra()
        error_modelo = np.abs(y[idx] - pm[idx])
        error_referencia = np.abs(y[idx] - pr[idx])
        simple.append(float(error_modelo.mean() - error_referencia.mean()) * 100)
        ponderado.append(float(
            np.average(error_modelo, weights=w[idx])
            - np.average(error_referencia, weights=w[idx])
        ) * 100)
    simple, ponderado = np.asarray(simple), np.asarray(ponderado)
    return dict(
        n=int(len(y)),
        n_bootstrap=int(n),
        unidad="estado" if por_estado else "municipio",
        mae_modelo_pts=float(np.abs(y - pm).mean() * 100),
        mae_referencia_pts=float(np.abs(y - pr).mean() * 100),
        diferencia_pts=float((np.abs(y - pm).mean() - np.abs(y - pr).mean()) * 100),
        ic95_min_pts=float(np.quantile(simple, 0.025)),
        ic95_max_pts=float(np.quantile(simple, 0.975)),
        mae_ponderado_modelo_pts=float(np.average(np.abs(y - pm), weights=w) * 100),
        mae_ponderado_referencia_pts=float(np.average(np.abs(y - pr), weights=w) * 100),
        diferencia_ponderada_pts=float((
            np.average(np.abs(y - pm), weights=w)
            - np.average(np.abs(y - pr), weights=w)
        ) * 100),
        ic95_ponderado_min_pts=float(np.quantile(ponderado, 0.025)),
        ic95_ponderado_max_pts=float(np.quantile(ponderado, 0.975)),
    )


def calibrar_rango(foto, prediccion, error_nacional=0.0):
    """Residuo = observado − predicho − error del supuesto nacional de la prueba.

    Ese error ya se conoce (nivel real menos supuesto); sin descontarlo, el rango
    repetiría en 2027 el cambio nacional de 2015 a 2021. La incertidumbre del país
    va en los escenarios. Cobertura aparente, sin garantía conformal.
    """
    tamanos = foto.conocidos_ultima.to_numpy(float)
    cortes = np.quantile(tamanos, [1 / 3, 2 / 3])
    grupos = np.searchsorted(cortes, tamanos, side="right")
    residuos = foto.abstencion_objetivo.to_numpy(float) - np.asarray(prediccion) - error_nacional
    filas = []
    for grupo in range(3):
        s = residuos[grupos == grupo]
        if not len(s):
            raise ValueError("Un grupo de tamaño quedó sin residuos para el rango")
        q10, q90 = np.quantile(s, [0.1, 0.9])
        # El rango siempre contiene la predicción aunque el error tenga sesgo.
        filas.append(dict(grupo=grupo, n=len(s), q10=float(q10), q90=float(q90),
            margen_min=float(min(q10, 0)), margen_max=float(max(q90, 0))))
    return dict(cortes=cortes.tolist(), error_nacional=float(error_nacional), grupos=filas)


def aplicar_rango(prediccion, tamanos, calibracion):
    p = np.asarray(prediccion, float)
    grupo = np.searchsorted(calibracion["cortes"], np.asarray(tamanos, float), side="right")
    margenes = calibracion["grupos"]
    inferior = np.clip(p + np.array([margenes[g]["margen_min"] for g in grupo]), 0, 1)
    superior = np.clip(p + np.array([margenes[g]["margen_max"] for g in grupo]), 0, 1)
    return inferior, superior
