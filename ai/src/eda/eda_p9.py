"""Análisis exploratorio: pregunta 9.

Uso: python ai/src/eda/eda_p9.py
Actualiza su sección de docs/EDA/reporte_eda.md y guarda sus tablas en
 docs/EDA/resultados/. Puede ejecutarse en paralelo mediante scripts/ejecutar_eda.py.
"""
import numpy as np
import pandas as pd
from eda_common import ROOT, KEY, YEARS, GROUPS, REPORT_DIR, markdown, plotting, run_question, save


def question9(base, train, out):
    missing = base[base.conocidos == 0][[*KEY, "AELEC", "nombre_estado", "nombre_municipio", "LN", "NS"]]
    save(missing, "p9_municipios_sin_respuesta", out)
    rows = []
    for year, d in train.groupby("eleccion_objetivo"):
        d = d.copy()
        d["grupo"] = np.select([d.historial_incompleto, d.historial_rearmado],
                                ["Reconstruido incompleto", "Reconstruido completo"], default="Sin reconstrucción")
        prev = "abst_ultima_intermedia" if d.tipo_objetivo.iloc[0] == "intermedia" else "abst_ultima_presidencial"
        for group, z in d.groupby("grupo"):
            valid = z.dropna(subset=["abstencion_objetivo", prev])
            error = (valid.abstencion_objetivo - valid[prev]).abs()*100
            rows.append(dict(eleccion=year, grupo=group, municipios=len(z),
                             sin_respuesta=z.abstencion_objetivo.isna().sum(),
                             sin_historial_mismo_tipo=z[prev].isna().sum(), evaluables=len(valid),
                             abstencion_mediana_pct=z.abstencion_objetivo.median()*100,
                             error_promedio_pp=error.mean(),
                             error_mediano_pp=error.median(),
                             personas_mediana=z.conocidos_objetivo.median()))
    r = save(pd.DataFrame(rows), "p9_historial_y_error", out)
    return ["## Pregunta 9. ¿Se comportan distinto los municipios sin información o con historial reconstruido?",
            "**Respuesta:** los municipios reconstruidos presentan un mayor error de referencia en los dos años "
            "donde aparecen. En 2021 es de 14.66 puntos con reconstrucción completa y 19.45 con reconstrucción "
            "incompleta, frente a 12.37 sin reconstrucción. En 2024 las diferencias son menores: 6.31, 7.14 y 5.69. "
            "Los tamaños de los grupos son pequeños; no basta para justificar una exclusión general.",
            f"Hay **{len(missing)} registros municipio–elección sin respuesta conocida** en la tabla de análisis. "
            "Su abstención está vacía y no debe interpretarse como cero. No se puede comparar su abstención "
            "con la de los demás porque precisamente se desconoce.",
            "El historial reconstruido recalcula el pasado con las secciones del territorio que se analiza. "
            "Se separa el que pudo reconstruirse completo del que dejó secciones sin asignar. "
            "Las categorías siguientes no se superponen; se evalúa el error de repetir la última elección del mismo tipo:",
            markdown(r[["eleccion", "grupo", "municipios", "sin_respuesta", "evaluables", "error_promedio_pp"]]),
            "**Decisión que apoya:** excluir del entrenamiento las filas sin respuesta, conservándolas en la cobertura. "
            "Los municipios reconstruidos requieren una evaluación separada antes de descartarlos. "
            "Las diferencias observadas no aíslan el efecto de reconstruir: también cambian los estados, tamaños "
            "y condiciones de los municipios. Los grupos reconstruidos tienen pocos casos; evitar conclusiones generales.",
            "Detalle: `p9_municipios_sin_respuesta.csv` y `p9_historial_y_error.csv`."]

def main():
    run_question(9, question9, __file__)


if __name__ == "__main__":
    main()
