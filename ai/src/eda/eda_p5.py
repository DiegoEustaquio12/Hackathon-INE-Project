"""Análisis exploratorio: pregunta 5.

Uso: python ai/src/eda/eda_p5.py
Actualiza su sección de docs/EDA/reporte_eda.md y guarda sus tablas en
 docs/EDA/resultados/. Puede ejecutarse en paralelo mediante scripts/ejecutar_eda.py.
"""
import numpy as np
import pandas as pd
from eda_common import ROOT, KEY, YEARS, GROUPS, REPORT_DIR, markdown, plotting, run_question, save


def question5(base, train, out):
    columns = ["pct_18_24", "pct_25_34", "pct_35_44", "pct_45_59", "pct_60_mas", "pct_mujeres",
               "pct_urbana", "pct_mixta", "pct_rural", "edad_promedio", "ln_ultima", "n_def"]
    rows, pairs = [], []
    for year, d in train.groupby("eleccion_objetivo"):
        for col in columns:
            s = d[["EDOCVE", col, "abstencion_objetivo"]].dropna()
            # Asociación ordenada, sin suponer una relación de línea recta.
            rho = s[col].corr(s.abstencion_objetivo, method="spearman")
            ranked = s[[col, "abstencion_objetivo"]].rank()
            within = ranked - ranked.groupby(s.EDOCVE).transform("mean")
            rows.append(dict(eleccion=year, variable=col, municipios=len(s),
                             relacion_orden=rho, relacion_sin_promedio_estatal=within[col].corr(within.abstencion_objetivo)))
        corr = d[columns].corr()
        for i, a in enumerate(columns):
            for b in columns[i+1:]:
                if abs(corr.loc[a, b]) >= .9:
                    pairs.append(dict(eleccion=year, variable_a=a, variable_b=b, correlacion=corr.loc[a, b]))
    r = save(pd.DataFrame(rows), "p5_asociaciones", out)
    save(pd.DataFrame(pairs), "p5_variables_parecidas", out)
    t = r.pivot(index="variable", columns="eleccion", values="relacion_orden").reset_index()
    names = {"pct_18_24": "% de 18 a 24 años", "pct_25_34": "% de 25 a 34 años", "pct_35_44": "% de 35 a 44 años",
             "pct_45_59": "% de 45 a 59 años", "pct_60_mas": "% de 60 años o más", "pct_mujeres": "% de mujeres",
             "pct_urbana": "% en secciones urbanas", "pct_mixta": "% en secciones mixtas", "pct_rural": "% en secciones rurales",
             "edad_promedio": "Edad promedio", "ln_ultima": "Personas registradas", "n_def": "Número de distritos federales"}
    t["variable"] = t.variable.map(names)
    return ["## Pregunta 5. ¿Qué características se relacionan con más abstención?",
            "**Respuesta:** las relaciones por separado son débiles y algunas cambian de signo entre elecciones. "
            "La proporción de mujeres se relaciona positivamente con la abstención municipal (0.13 a 0.32), "
            "aunque las mujeres votan más que los hombres cuando se comparan las tasas por sexo. Son comparaciones "
            "distintas: un municipio con más mujeres no equivale a medir el comportamiento de una mujer individual. "
            "La relación de la proporción rural con la abstención municipal es negativa (−0.22 a −0.05). "
            "Edad promedio y proporción de mayores tienen una correlación cercana a 0.98 entre sí.",
            "Se compara la composición de la lista de la elección anterior con la abstención posterior. "
            "Cada municipio tiene el mismo peso y cada elección se analiza por separado, para no mezclar presidenciales con intermedias.",
            "Relación entre el orden de los municipios según cada característica y según su abstención "
            "(Spearman, de −1 a 1; positivo: ambos tienden a subir juntos; negativo: uno sube mientras el otro baja):",
            markdown(t.rename(columns={"variable": "Característica previa"})),
            "El archivo `p5_asociaciones.csv` también resta los promedios estatales a los órdenes para comprobar cuánto "
            "cambia la relación al comparar municipios dentro de estados. Es un diagnóstico descriptivo, sin entrenar modelos.",
            "**Decisión que apoya:** llevar las variables a la selección de la Fase 5 según su consistencia entre elecciones, "
            "sin convertir una asociación en una explicación causal ni en una garantía de capacidad predictiva. "
            "Edad promedio y proporción de mayores pueden aportar información repetida; los porcentajes de las cinco edades "
            "suman uno, al igual que urbana/mixta/rural, por lo que un futuro modelo lineal con intercepto necesitaría omitir "
            "una categoría por conjunto. El número de distritos no se interpreta como causa de abstención.",
            "Detalle: `p5_asociaciones.csv` y `p5_variables_parecidas.csv`. No se usa la composición de la propia elección objetivo."]

def main():
    run_question(5, question5, __file__)


if __name__ == "__main__":
    main()
