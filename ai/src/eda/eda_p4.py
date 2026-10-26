"""Análisis exploratorio: pregunta 4.

Uso: python ai/src/eda/eda_p4.py
Actualiza su sección de docs/EDA/reporte_eda.md y guarda sus tablas en
 docs/EDA/resultados/. Puede ejecutarse en paralelo mediante scripts/ejecutar_eda.py.
"""
import numpy as np
import pandas as pd
from eda_common import ROOT, KEY, YEARS, GROUPS, REPORT_DIR, markdown, plotting, run_question, save


def question4(base, train, out):
    """Tasas nacionales exactas por grupo; la tabla base no conserva sus denominadores."""
    national = []
    for year in YEARS:
        d = pd.read_parquet(ROOT / f"data/interim/ccpc/ccpc_{year}.parquet",
                            columns=["EDAD", "SEXO", "TIPOSEC", "LN", "SV", "NV"])
        for column, mapping in [
            ("EDAD", None), ("SEXO", {0: "hombres", 1: "mujeres", 2: "no_binario"}),
            ("TIPOSEC", {"U": "urbana", "M": "mixta", "R": "rural"}),
        ]:
            if column == "EDAD":
                labels = pd.cut(d.EDAD, [17, 24, 34, 44, 59, np.inf], labels=list(GROUPS)[:5])
            else:
                labels = d[column].map(mapping)
            agg = d.groupby(labels, observed=True)[["LN", "SV", "NV"]].sum()
            # Cada clasificación cubre todo el universo, incluido no binario en 2024.
            assert agg.sum().equals(d[["LN", "SV", "NV"]].sum())
            for group, row in agg.iterrows():
                n = int(row.SV + row.NV)
                assert 0 <= int(row.NV) <= n <= int(row.LN)
                national.append(dict(eleccion=year, grupo=group, registrados=int(row.LN),
                                     con_dato=n, no_votaron=int(row.NV),
                                     abstencion_pct=100.0 * int(row.NV) / n if n else np.nan))
        assert int(d.NV.sum()) == int(base.loc[base.AELEC == year, "NV"].sum())
        del d
    national = save(pd.DataFrame(national), "p4_grupos_nacional", out)
    municipality = []
    for year, d in base.groupby("AELEC"):
        for group in GROUPS:
            v = d[f"abst_{group}"] * 100
            municipality.append(dict(eleccion=year, grupo=group, municipios_con_dato=v.count(),
                                     mediana_pct=v.median(), p10_pct=v.quantile(.1), p90_pct=v.quantile(.9)))
    save(pd.DataFrame(municipality), "p4_grupos_municipios", out)
    table = national.pivot(index="grupo", columns="eleccion", values="abstencion_pct").round(2)
    table = table.reindex([*GROUPS, "no_binario"]).rename(index={**GROUPS, "no_binario": "No binario"})
    paired = []
    for year, d in base.groupby("AELEC"):
        for a, b in [("hombres", "mujeres"), ("urbana", "rural"), ("25_34", "45_59")]:
            valid = d[[f"abst_{a}", f"abst_{b}"]].dropna()
            diff = (valid.iloc[:, 0] - valid.iloc[:, 1])*100
            paired.append(dict(eleccion=year, comparacion=f"{a} menos {b}", municipios=len(valid),
                               diferencia_mediana_pp=diff.median(), porcentaje_diferencia_positiva=100*(diff > 0).mean()))
    save(pd.DataFrame(paired), "p4_comparaciones_dentro_municipio", out)
    n21 = national[national.eleccion == 2021].set_index("grupo")
    n24 = national[national.eleccion == 2024].set_index("grupo")
    figure(out)
    return ["## Pregunta 4. ¿Qué grupos se abstienen más?", 
            f"**Respuesta:** las personas de 25 a 34 años tienen la mayor abstención nacional entre las edades "
            f"analizadas en cinco de las seis elecciones; en 2018 las superan las de 18 a 24. "
            f"En 2021 alcanzan {n21.loc['25_34', 'abstencion_pct']:.1f}% "
            f"y en 2024 {n24.loc['25_34', 'abstencion_pct']:.1f}%. Los hombres superan a las mujeres "
            f"en {n21.loc['hombres', 'abstencion_pct']-n21.loc['mujeres', 'abstencion_pct']:.1f} puntos en 2021 "
            f"y {n24.loc['hombres', 'abstencion_pct']-n24.loc['mujeres', 'abstencion_pct']:.1f} en 2024. "
            "La diferencia entre zonas urbanas y rurales cambia de tamaño según la elección.",
            "Porcentaje de personas con registro conocido que no votaron, sumando primero personas en todo el país:",
            markdown(table.reset_index().rename(columns={"grupo": "Grupo"})),
            "![Abstención nacional por grupos en 2021 y 2024](eda_p4_grupos.png)",
            "Los grupos de edad, sexo y zona se analizan por separado: se superponen y sus efectos no se pueden sumar. "
            "La clasificación urbana/rural corresponde a la sección electoral, no a una característica individual. "
            "El grupo no binario solo está registrado en 2024; su tamaño se conserva en el CSV para no equipararlo a grupos grandes.",
            "**Decisión que apoya:** priorizar el análisis de los grupos con mayor abstención y mayor número de personas. "
            "Estos datos describen a quiénes no votaron; no demuestran que una campaña dirigida a un grupo vaya a tener más efecto.",
            "Detalle: `p4_grupos_nacional.csv`, `p4_grupos_municipios.csv` y "
            "`p4_comparaciones_dentro_municipio.csv`. El último compara grupos dentro de un mismo municipio."]

def figure(out):
    plt = plotting()
    national = pd.read_csv(out / "p4_grupos_nacional.csv")
    fig, axes = plt.subplots(1, 3, figsize=(13, 5), layout="constrained", sharey=True)
    for ax, keys, title in zip(axes, [list(GROUPS)[:5], ["mujeres", "hombres"], ["urbana", "mixta", "rural"]],
                               ["Por edad", "Por sexo", "Por sección electoral"]):
        for offset, year, color in [(-.18, 2021, "#2672a3"), (.18, 2024, "#cc6633")]:
            values = national[national.eleccion == year].set_index("grupo").loc[keys, "abstencion_pct"]
            ax.bar(np.arange(len(keys))+offset, values, width=.36, label=str(year), color=color)
        labels = [GROUPS[k].replace(" años", "").replace("Secciones ", "").replace("60 o más", "60+") for k in keys]
        ax.set_xticks(range(len(keys)), labels, rotation=30, ha="right")
        ax.set_title(title)
        ax.set_ylim(0, 70)
    axes[0].set_ylabel("Personas que no votaron entre quienes tienen dato (%)")
    axes[-1].legend()
    fig.suptitle("La abstención varía entre grupos y elecciones", fontsize=15)
    fig.savefig(ROOT / "docs/EDA/eda_p4_grupos.png", dpi=160)
    plt.close(fig)


def main():
    run_question(4, question4, __file__)


if __name__ == "__main__":
    main()
