"""Análisis exploratorio: pregunta 8.

Uso: python ai/src/eda/eda_p8.py
Actualiza su sección de docs/EDA/reporte_eda.md y guarda sus tablas en
 docs/EDA/resultados/. Puede ejecutarse en paralelo mediante scripts/ejecutar_eda.py.
"""
import numpy as np
import pandas as pd
from eda_common import ROOT, KEY, YEARS, GROUPS, REPORT_DIR, markdown, plotting, run_question, save


def question8(base, train, out, data_dir=ROOT / "data/processed"):
    s = pd.read_parquet(ROOT / "data/interim/secciones.parquet")
    sk = ["EDOCVE", "SECCION"]
    sets = {y: set(map(tuple, s.loc[s.AELEC == y, sk].to_numpy())) for y in [2009, 2012, 2015]}
    missing = (sets[2009] & sets[2015]) - sets[2012]
    common = sets[2009] & sets[2012] & sets[2015]
    rows = []
    for year in [2009, 2012, 2015]:
        d = s[s.AELEC == year]
        keys = list(map(tuple, d[sk].to_numpy()))
        for name, keep in [("Todas las disponibles", np.ones(len(d), dtype=bool)),
                           ("Presentes en los tres años", [k in common for k in keys]),
                           ("Ausentes en 2012", [k in missing for k in keys])]:
            z = d.loc[keep]
            nv, sv = int(z.NV.sum()), int(z.SV.sum())
            rows.append(dict(eleccion=year, conjunto=name, secciones=len(z), registrados=int(z.LN.sum()),
                             abstencion_pct=100*nv/(nv+sv) if nv+sv else np.nan))
    r = save(pd.DataFrame(rows), "p8_panel_secciones", out)
    cat = pd.read_csv(data_dir / "catalogo_municipios.csv")
    save(cat.loc[cat.pct_hueco_2012 > 0, [*KEY, "nombre_estado", "nombre_municipio", "pct_hueco_2012"]],
         "p8_municipios_afectados", out)
    # Asociación entre ausencia histórica y el error de repetir la presidencial anterior.
    errors = []
    for year, d in train[train.tipo_objetivo == "presidencial"].groupby("eleccion_objetivo"):
        d = d.dropna(subset=["abstencion_objetivo", "abst_ultima_presidencial"]).copy()
        d["hueco"] = pd.cut(d.pct_hueco_2012, [-.00001, 0, .1, 1.00001], labels=["Sin hueco", "Hasta 10%", "Más de 10%"])
        d["error_pp"] = (d.abstencion_objetivo - d.abst_ultima_presidencial).abs()*100
        for group, z in d.groupby("hueco", observed=True):
            errors.append(dict(eleccion=year, hueco=group, municipios=len(z), error_promedio_pp=z.error_pp.mean()))
    err = save(pd.DataFrame(errors), "p8_error_historial_presidencial", out)
    affected = int((cat.pct_hueco_2012 > 0).sum())
    severe = int((cat.pct_hueco_2012 > 10).sum())
    return ["## Pregunta 8. ¿Cuánto afecta la información ausente de 2012?",
            "**Respuesta:** el problema está concentrado territorialmente. En 2012, limitar el cálculo a las "
            "secciones presentes también en 2009 y 2015 cambia la abstención nacional de 37.92% a 37.73% "
            "(0.19 puntos), pero esta diferencia no recupera la abstención de las secciones ausentes. "
            "Los municipios con más de 10% de hueco tienen un error de referencia de 7.56 puntos en 2018, "
            "frente a 5.86 en los que no tienen hueco; es una asociación, no una estimación del daño causado por la ausencia.",
            f"Faltan **{len(missing):,} secciones** presentes en 2009 y 2015. El catálogo identifica "
            f"**{affected} municipios afectados**, de los que **{severe}** tienen más de 10% de su lista de 2009 en esas secciones. "
            "No son registros NS: las secciones enteras no aparecen en el archivo de 2012.",
            markdown(r),
            "Comparar las mismas secciones en los tres años separa parte del cambio de cobertura del cambio "
            "entre elecciones. Las tasas de 2009 y 2015 de las secciones ausentes describen esos otros años; "
            "no permiten saber cuánto se abstuvieron sus habitantes en 2012.",
            "Error de repetir la última presidencial, por proporción del hueco histórico:", markdown(err),
            "En 2018 la última presidencial es 2012 cuando tiene dato. En 2024 suele ser 2018; "
            "esta segunda comparación sirve como contraste descriptivo, no como medición del efecto causal de 2012.",
            "**Decisión que apoya:** conservar 2012 identificado como incompleto y evaluar un historial alternativo "
            "sin 2012 en la Fase 7. No excluirlo de todos los municipios ni rellenar automáticamente el hueco. "
            "Deben revisarse individualmente los municipios ausentes por completo y los más afectados.",
            "Detalle: archivos `p8_*.csv`; el porcentaje de hueco del catálogo está en escala 0–100."]

def main():
    run_question(8, question8, __file__)


if __name__ == "__main__":
    main()
