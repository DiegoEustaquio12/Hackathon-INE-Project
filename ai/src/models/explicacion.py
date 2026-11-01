"""Aportes TreeSHAP de LightGBM, expresados en puntos porcentuales."""
import numpy as np
import pandas as pd

from datos_modelo import matriz
from fase3 import DESC_FOTO

DESCRIPCIONES = {c: d for _, filas in DESC_FOTO for c, d in filas}
DESCRIPCIONES["es_intermedia"] = "Si la elección objetivo es intermedia"


def explicar(modelo, foto, columnas):
    x = matriz(foto, columnas)
    aportes = np.asarray(modelo.predict(x, pred_contrib=True))
    if not np.allclose(aportes.sum(axis=1), modelo.predict(x), atol=1e-9):
        raise ValueError("Los aportes no reconstruyen la distancia predicha")
    razones = []
    for fila in aportes[:, :-1]:
        orden = np.argsort(-np.abs(fila), kind="stable")[:3]
        razones.append({f"razon_{i}":
            f"{DESCRIPCIONES.get(columnas[j], columnas[j])}: {fila[j] * 100:+.2f} pp de abstención"
            for i, j in enumerate(orden, 1)})
    globales = []
    for j, columna in enumerate(columnas):
        valores, efecto = x[columna], aportes[:, j]
        correlacion = (valores.corr(pd.Series(efecto, index=x.index))
                       if valores.nunique() > 1 and np.std(efecto) > 0 else np.nan)
        globales.append(dict(columna=columna, descripcion=DESCRIPCIONES.get(columna, columna),
            aporte_absoluto_medio_pts=float(np.abs(efecto).mean() * 100),
            aporte_medio_pts=float(efecto.mean() * 100),
            correlacion_valor_aporte=float(correlacion) if np.isfinite(correlacion) else None,
            direccion=("valores altos suben" if correlacion > 0 else "valores altos bajan")
                if np.isfinite(correlacion) and abs(correlacion) > 0.05 else "relación no monotónica"))
    globales = pd.DataFrame(globales).sort_values(
        "aporte_absoluto_medio_pts", ascending=False, kind="stable"
    ).reset_index(drop=True)
    return pd.DataFrame(razones, index=foto.index), globales, float(aportes[0, -1])


def explicar_referencia(foto):
    """No atribuye aportes del modelo descartado a una predicción de referencia."""
    return pd.DataFrame({
        "razon_1": foto.referencia.map(lambda v: f"Repetir la última intermedia: {v * 100:.2f}%"),
        "razon_2": "Sin ajuste por columnas: se utiliza el punto de partida",
        "razon_3": "LightGBM no superó las cuatro condiciones de evaluación",
    }, index=foto.index)
