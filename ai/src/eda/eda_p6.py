"""Análisis exploratorio: pregunta 6.

Uso: python ai/src/eda/eda_p6.py
Actualiza su sección de docs/EDA/reporte_eda.md y guarda sus tablas en
 docs/EDA/resultados/. Puede ejecutarse en paralelo mediante scripts/ejecutar_eda.py.
"""
import numpy as np
import pandas as pd
from eda_common import ROOT, KEY, YEARS, GROUPS, REPORT_DIR, markdown, plotting, run_question, save


def question6(base, train, out, data_dir=ROOT / "data/processed"):
    pieces = []
    catalog = pd.read_csv(data_dir / "catalogo_municipios.csv")
    for earlier, later in [(2009, 2015), (2015, 2021), (2012, 2018), (2018, 2024)]:
        cols = [*KEY, "conocidos", "abstencion", "pct_ns"]
        a = base.loc[base.AELEC == earlier, cols]
        b = base.loc[base.AELEC == later, cols]
        d = a.merge(b, on=KEY, suffixes=("_antes", "_despues"), validate="one_to_one")
        d = d.merge(catalog[[*KEY, *[f"situacion_{y}" for y in YEARS if earlier < y <= later]]], on=KEY)
        changes = d.filter(regex="^situacion_").isin(["nuevo", "cambio_limites", "clave_reasignada", "sin_registro"]).any(axis=1)
        d = d[(~changes) & (d.pct_ns_antes <= .1) & (d.pct_ns_despues <= .1)].copy()
        d = d.dropna(subset=["abstencion_antes", "abstencion_despues"])
        d["periodo"] = f"{earlier}–{later}"
        d["minimo_con_dato"] = d[["conocidos_antes", "conocidos_despues"]].min(axis=1)
        d["cambio_absoluto_pp"] = (d.abstencion_despues - d.abstencion_antes).abs() * 100
        pieces.append(d[[*KEY, "periodo", "minimo_con_dato", "cambio_absoluto_pp"]])
    d = pd.concat(pieces, ignore_index=True)
    d["tamano"] = pd.cut(d.minimo_con_dato, [0, 100, 500, 1000, 5000, 10000, np.inf], right=False,
                         labels=["1–99", "100–499", "500–999", "1,000–4,999", "5,000–9,999", "10,000 o más"])
    summary = d.groupby(["periodo", "tamano"], observed=True).cambio_absoluto_pp.agg(
        municipios="size", cambio_mediano_pp="median", cambio_promedio_pp="mean", p90_pp=lambda x: x.quantile(.9)).reset_index()
    save(summary, "p6_estabilidad_por_tamano", out)
    save(d, "p6_pares_comparables", out)
    coverage = []
    for year, s in base.groupby("AELEC"):
        for minimum in [100, 500, 1000, 5000]:
            drop = (s.conocidos > 0) & (s.conocidos < minimum)
            coverage.append(dict(eleccion=year, minimo=minimum, municipios_excluidos=drop.sum(),
                                 personas_con_dato_excluidas=s.loc[drop, "conocidos"].sum(),
                                 porcentaje_personas=100*s.loc[drop, "conocidos"].sum()/s.conocidos.sum()))
    cov = save(pd.DataFrame(coverage), "p6_cobertura_segun_minimo", out)
    table = summary[summary.periodo == "2015–2021"]
    figure(out)
    return ["## Pregunta 6. ¿Desde cuántas personas con dato se estabiliza el porcentaje?",
            "**Respuesta:** no se observa un tamaño a partir del cual los cambios desaparezcan. "
            "En 2015–2021, el cambio mediano es 10.1 puntos para municipios con 100–499 personas con dato, "
            "8.9 para 500–999 y 8.5 para 10,000 o más. El patrón no es una reducción continua con el tamaño.",
            "Se comparan elecciones consecutivas del mismo tipo, sin cambios territoriales detectados durante el intervalo "
            "y con un máximo de 10% de registros sin información en ambas. El tamaño es el menor número de personas con dato "
            "entre las dos elecciones. Ejemplo de intermedias 2015–2021:", markdown(table),
            "**No existe un mínimo universal que estos datos permitan certificar.** Los cambios observados también "
            "incluyen cambios reales de participación, composición y cobertura. No son errores de una muestra aleatoria: "
            "el CCPC cuenta registros censales disponibles. Un municipio pequeño puede tener una tasa exacta para sus "
            "registros conocidos y aun así una tasa poco estable en el tiempo.",
            "Costo de aplicar distintos mínimos en 2024 (solo municipios con alguna información):",
            markdown(cov[cov.eleccion == 2024].drop(columns="eleccion")),
            "**Decisión que apoya:** evaluar 100, 500 y 1,000 personas como reglas de sensibilidad en la Fase 5, "
            "sin declarar automáticamente confiables a los municipios que superen un corte. Mantener visibles los casos "
            "pequeños y su cobertura. La Fase 7 deberá comparar el error y la cobertura de esas reglas.",
            "Detalle: `p6_estabilidad_por_tamano.csv`, `p6_pares_comparables.csv` y `p6_cobertura_segun_minimo.csv`.",
            '![Estabilidad por tamaño](eda_p6_estabilidad.png)']

def figure(out):
    plt = plotting()
    size = pd.read_csv(out / "p6_estabilidad_por_tamano.csv")
    fig, ax = plt.subplots(figsize=(8, 5), layout="constrained")
    for period in ["2009–2015", "2015–2021"]:
        s = size[size.periodo == period].iloc[1:]
        ax.plot(s.tamano, s.cambio_mediano_pp, marker="o", label=period)
    ax.tick_params(axis="x", rotation=25)
    ax.set(title="No aparece un mínimo claro de estabilidad", ylabel="Cambio mediano (puntos porcentuales)",
           xlabel="Menor número de personas con dato entre elecciones")
    ax.legend()
    fig.savefig(REPORT_DIR / "eda_p6_estabilidad.png", dpi=160)
    plt.close(fig)


def main():
    run_question(6, question6, __file__)


if __name__ == "__main__":
    main()
