"""Calibración de distancias municipales con predicciones out-of-fold.

La calibración se ajusta sobre distancias, no sobre el porcentaje final: si se
calibrara después de centrar al nivel nacional se rompería la media ponderada.
El modelo final usa las cuatro fotos; las pruebas usan solo años anteriores.
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import HuberRegressor

from datos_modelo import matriz
from validacion import centrar, entrenar, particiones_estados


def predicciones_oof(foto, columnas, parametros, arboles, grupos=5):
    """Predicción fuera de fold por estados, sin usar la fila evaluada."""
    if foto.empty:
        raise ValueError("No hay filas para calibrar")
    piezas = []
    for fold, (i, j) in enumerate(particiones_estados(foto, grupos), 1):
        modelo = entrenar(foto.iloc[i], columnas, parametros, arboles)
        pred = modelo.predict(matriz(foto.iloc[j], columnas))
        piezas.append(pd.DataFrame(dict(
            fold=fold,
            EDOCVE=foto.iloc[j].EDOCVE.to_numpy(),
            MPIOCVE=foto.iloc[j].MPIOCVE.to_numpy(),
            eleccion_objetivo=foto.iloc[j].eleccion_objetivo.to_numpy(),
            distancia_pred=np.asarray(pred, dtype=float),
            distancia_objetivo=foto.iloc[j].distancia_objetivo.to_numpy(float),
            conocidos_objetivo=foto.iloc[j].conocidos_objetivo.to_numpy(),
        ), index=foto.iloc[j].index))
    return pd.concat(piezas).sort_index()


def ajustar(oof, metodo="huber"):
    """Ajusta ``distancia_objetivo ~ a + b * distancia_pred`` con OOF."""
    if oof.empty:
        raise ValueError("No hay predicciones OOF para calibrar")
    x = oof.distancia_pred.to_numpy(float)
    y = oof.distancia_objetivo.to_numpy(float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("La calibración recibió valores no finitos")
    if np.std(x) == 0:
        raise ValueError("No se puede calibrar una predicción constante")
    if metodo == "huber":
        modelo = HuberRegressor(epsilon=1.35, alpha=1e-6, max_iter=1000)
        modelo.fit(x.reshape(-1, 1), y)
        a, b = float(modelo.intercept_), float(modelo.coef_[0])
    elif metodo == "lineal":
        b, a = np.polyfit(x, y, 1)
        a, b = float(a), float(b)
    else:
        raise ValueError(f"Método de calibración desconocido: {metodo}")
    if not np.isfinite(a) or not np.isfinite(b):
        raise ValueError("La calibración produjo parámetros no finitos")
    if b <= 0:
        raise ValueError("La calibración debe conservar el orden (b > 0)")
    return dict(metodo=metodo, a=a, b=b, n=int(len(y)))


def aplicar(distancias, calibracion):
    """Aplica la recta y recorta a un rango de distancia válido."""
    if not {"a", "b"} <= set(calibracion):
        raise ValueError("Faltan parámetros de calibración")
    d = np.asarray(distancias, dtype=float)
    return np.clip(calibracion["a"] + calibracion["b"] * d, -1, 1)


def predecir_calibrado(modelo, foto, columnas, nivel, calibracion):
    """Predice distancia, la calibra y la centra al nivel nacional."""
    distancias = modelo.predict(matriz(foto, columnas))
    valores, _ = centrar(aplicar(distancias, calibracion), foto.conocidos_ultima, nivel)
    return valores, distancias


def resumen(y, p, w):
    """MAE, sesgo y pendiente de calibración en puntos porcentuales."""
    y, p, w = [np.asarray(v, dtype=float) for v in (y, p, w)]
    if not len(y) or not (np.isfinite(y) & np.isfinite(p) & np.isfinite(w)).all():
        raise ValueError("Métricas de calibración sin datos finitos")
    if (w < 0).any() or w.sum() <= 0:
        raise ValueError("Pesos de calibración inválidos")
    error = np.abs(y - p)
    if np.std(p) > 0:
        b, a = np.polyfit(p, y, 1)
        pendiente, intercepto = float(b), float(a)
    else:
        pendiente, intercepto = None, None
    return dict(
        n=int(len(y)),
        mae_pts=float(error.mean() * 100),
        mae_ponderado_pts=float(np.average(error, weights=w) * 100),
        sesgo_pts=float((p - y).mean() * 100),
        pendiente=pendiente,
        intercepto=intercepto,
    )
