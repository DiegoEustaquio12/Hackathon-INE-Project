"""Análisis exploratorio: pregunta 7.

Uso: python ai/src/eda/eda_p7.py
Actualiza su sección de docs/EDA/reporte_eda.md y guarda sus tablas en
 docs/EDA/resultados/. Puede ejecutarse en paralelo mediante scripts/ejecutar_eda.py.
"""
import numpy as np
import pandas as pd
from eda_common import ROOT, KEY, YEARS, GROUPS, REPORT_DIR, markdown, plotting, run_question, save


def quality_totals(d, keys):
    r = d.groupby(keys)[["LN", "SV", "NV", "NS"]].sum().reset_index()
    r["sin_informacion_pct"] = 100*r.NS/r.LN
    r["abstencion_conocida_pct"] = 100*r.NV/(r.SV+r.NV)
    r["minimo_posible_pct"] = 100*r.NV/r.LN
    r["maximo_posible_pct"] = 100*(r.NV+r.NS)/r.LN
    return r


def question7(base, train, out):
    nat = save(quality_totals(base, ["AELEC"]), "p7_cobertura_nacional", out)
    state = save(quality_totals(base, ["AELEC", "EDOCVE", "nombre_estado"]), "p7_cobertura_estatal", out)
    counts = []
    for year, s in base.groupby("AELEC"):
        counts.append(dict(eleccion=year, sin_dato=int((s.conocidos == 0).sum()),
                           ns_mayor_10=int((s.pct_ns > .1).sum()), ns_mayor_20=int((s.pct_ns > .2).sum()),
                           ns_mayor_50=int((s.pct_ns > .5).sum())))
    save(pd.DataFrame(counts), "p7_municipios_cobertura", out)
    save(base.loc[base.pct_ns > .2, [*KEY, "nombre_estado", "nombre_municipio", "AELEC", "LN", "NS", "pct_ns"]],
         "p7_municipios_ns_alto", out)
    figure(out)
    return ["## Pregunta 7. ¿Dónde y cuándo falta información sobre si las personas votaron?",
            "**Respuesta:** la información faltante nacional va de 0.22% en 2012 a 6.83% en 2018, "
            "pero el bajo valor de 2012 no incluye las secciones ausentes. "
            "El mayor porcentaje estatal observado es 18.55% en Quintana Roo en 2015. "
            "En 2024 hay 488 municipios con más de 10% sin información y 38 con más de la mitad.",
            "NS cuenta personas para las que no se sabe si votaron. Su porcentaje se calcula sobre toda la lista "
            "nominal; la abstención publicada se calcula solo entre quienes sí tienen esa información.",
            markdown(nat[["AELEC", "sin_informacion_pct", "abstencion_conocida_pct", "minimo_posible_pct", "maximo_posible_pct"]]),
            "Los extremos posibles asignan todos los NS a quienes votaron o a quienes no votaron. No son "
            "intervalos de confianza ni predicciones; muestran cuánto desconocimiento deja la información faltante.",
            "Diez combinaciones estado–elección con mayor proporción sin información:",
            markdown(state.nlargest(10, "sin_informacion_pct")[["AELEC", "nombre_estado", "sin_informacion_pct"]]),
            markdown(pd.DataFrame(counts)),
            "**Decisión que apoya:** conservar la definición de abstención sobre casos conocidos y acompañarla de "
            "la cobertura. Comparar resultados con máximos de 10% y 20% de NS, sin tratarlos como límites oficiales. "
            "No asumir que los registros faltantes se comportan como los conocidos. Ausencias de secciones completas "
            "en 2012 no están incluidas en el NS de las secciones presentes (pregunta 8).",
            "Detalle: archivos `p7_*.csv`.",
            '![Registros sin información](eda_p7_cobertura.png)']

def figure(out):
    plt = plotting()
    ns = pd.read_csv(out / "p7_cobertura_nacional.csv")
    fig, ax = plt.subplots(figsize=(8, 5), layout="constrained")
    ax.bar(ns.AELEC.astype(str), ns.sin_informacion_pct, color="#2672a3")
    ax.set(title="Registros sin información sobre el voto", ylabel="Porcentaje de la lista nominal")
    ax.text(.03, .97, "2012: no incluye las secciones ausentes", transform=ax.transAxes, va="top", fontsize=9)
    fig.savefig(REPORT_DIR / "eda_p7_cobertura.png", dpi=160)
    plt.close(fig)


def main():
    run_question(7, question7, __file__)


if __name__ == "__main__":
    main()
