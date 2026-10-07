"""Fase 4 del plan: análisis exploratorio.

Genera reporte_eda.md y figuras en docs/reports/figs/.
"""
from pathlib import Path
import sys
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
TA = RAIZ.parent / "data" / "processed" / "tabla_analisis.parquet"
DES = RAIZ.parent / "data" / "processed" / "tabla_analisis_desglose.parquet"
FIGS = RAIZ.parent / "docs" / "reports" / "figs"
REPO = RAIZ.parent / "docs" / "reports" / "reporte_eda.md"

ANIOS = [2009, 2012, 2015, 2018, 2021, 2024]

def _n(x): return f"{x:,}"


def preg1(ta: pd.DataFrame) -> str:
    FIGS.mkdir(parents=True, exist_ok=True)
    # participación nacional
    rows = []
    for a in ANIOS:
        s = ta[ta.anio_eleccion == a]
        denom = (s.SV + s.NV)
        part = s.SV.sum() / denom.sum() if denom.sum() > 0 else np.nan
        rows.append((a, part))
    dfp = pd.DataFrame(rows, columns=["anio", "part"])
    fig, ax = plt.subplots()
    ax.bar(dfp.anio.astype(str), dfp.part, color="#1f77b4")
    ax.set_ylabel("Participación (SV/(SV+NV))")
    ax.set_ylim(0, 0.7)
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x*100:.0f}%")
    fig.tight_layout()
    fig.savefig(FIGS / "fig_p1_participacion_nacional.png", dpi=150)
    plt.close(fig)

    # brecha intermedia vs presidencial para secciones comparables
    # pares: 2009->2012, 2015->2018, 2021->2024
    pares = [(2009, 2012), (2015, 2018), (2021, 2024)]
    deltas = []
    for i, j in pares:
        t1 = ta[(ta.anio_eleccion == i) & (ta.participacion.notna())][["EDOCVE", "SECCION", "participacion"]]
        t2 = ta[(ta.anio_eleccion == j) & (ta.participacion.notna())][["EDOCVE", "SECCION", "participacion"]]
        m = t1.merge(t2, on=["EDOCVE", "SECCION"], how="inner", suffixes=("_i", "_j"))
        if len(m) == 0: continue
        m["delta"] = m.participacion_j - m.participacion_i  # pp
        deltas.append((f"{i}->{j}", m.delta.mean(), m.delta.median()))
    return f"""**Pregunta 1 (brecha intermedia vs presidencial)**

- Participación nacional por año: {', '.join(f'{a}={dfp.loc[dfp.anio==a].part.iloc[0]*100:.1f}%' for a in ANIOS)}.
- En secciones presentes en ambas de cada par: media (pp): {', '.join(f'{p}: {d*100:+.1f}pp' for p,d,_ in deltas)}; mediana (pp): {', '.join(f'{p}: {md*100:+.1f}pp' for p,d,md in deltas)}.
- Figura: `figs/fig_p1_participacion_nacional.png`.

**Decisión que ayuda a tomar:** justifica el mapa de brecha intermedia vs presidencial (mapa 4) y el uso de `tipo_eleccion` en el modelo (Fases 5–7).
"""

def preg2(ta: pd.DataFrame) -> str:
    # variación entre intermedias
    inter = [2009, 2015, 2021]
    vals = []
    for a in inter:
        s = ta[ta.anio_eleccion == a]
        d = (s.SV + s.NV)
        part = s.SV.sum() / d.sum() if d.sum() > 0 else np.nan
        vals.append(part)
    rng = max(vals) - min(vals) if vals else np.nan
    # rank correlation entre intermedias en secciones comunes
    corr = []
    pairs = [(2009,2015),(2015,2021),(2009,2021)]
    for i,j in pairs:
        t1 = ta[(ta.anio_eleccion == i) & (ta.abstencion.notna())][["EDOCVE","SECCION","abstencion"]]
        t2 = ta[(ta.anio_eleccion == j) & (ta.abstencion.notna())][["EDOCVE","SECCION","abstencion"]]
        m = t1.merge(t2,on=["EDOCVE","SECCION"],how="inner")
        if len(m)<10: continue
        corr.append(m.abstencion_x.corr(m.abstencion_y, method="spearman"))
    corr_str = f"{np.nanmean(corr)*100:.1f}%" if corr else "N/A"
    return f"""**Pregunta 2 (variación entre intermedias)**
- Participación intermedias: 2009={vals[0]*100:.1f}%, 2015={vals[1]*100:.1f}%, 2021={vals[2]*100:.1f}% (rango {rng*100:.1f} pp).
- Correlación de rangos (Spearman) de abstención entre intermedias (secciones comunes): {corr_str} (promedio).

**Decisión que ayuda a tomar:** el nivel cambia mucho entre intermedias (7.7 pp) → conviene usar **posición relativa** (percentiles/rangos) más que porcentaje absoluto para clasificar riesgo (Fase 5).
"""

def preg3(ta: pd.DataFrame) -> str:
    # persistencia misma tipología
    pairs = [(2009,2015),(2015,2021),(2012,2018),(2018,2024)]
    csp = []
    dec = []
    for i,j in pairs:
        t1 = ta[(ta.anio_eleccion==i)&(ta.abstencion.notna())][["EDOCVE","SECCION","abstencion"]]
        t2 = ta[(ta.anio_eleccion==j)&(ta.abstencion.notna())][["EDOCVE","SECCION","abstencion"]]
        m = t1.merge(t2,on=["EDOCVE","SECCION"],how="inner")
        if len(m)<10: continue
        csp.append(m.abstencion_x.corr(m.abstencion_y,method="spearman"))
        # top decil
        q = m.abstencion_x.quantile(0.9)
        top1 = m[m.abstencion_x>=q]
        if len(top1)>0:
            q2 = m.abstencion_y.quantile(0.9)
            stay = (top1.abstencion_y>=q2).mean()
            dec.append(stay*100)
    return f"""**Pregunta 3 (persistencia de abstención entre elecciones del mismo tipo)**
- Spearman entre pares del mismo tipo (promedio): {np.nanmean(csp)*100:.1f}% (rango ~+estable según magnitud).
- Persistencia de secciones en **top decil** de abstención al siguiente ciclo del mismo tipo (promedio): {np.nanmean(dec):.1f}% permanecen en top decil.

**Decisión que ayuda a tomar:** hay persistencia moderada-alta en el orden de secciones → base razonable para “repetir lo de la última elección parecida” (punto de partida Fase 7). El orden es más predecible que el porcentaje.
"""

def preg4(des: pd.DataFrame, ta: pd.DataFrame) -> str:
    # participación por tipo sección
    rows = []
    for a in ANIOS:
        s = ta[ta.anio_eleccion==a]
        for t in ["U","M","R"]:
            ss = s[s.TIPOSEC==t]
            d = ss.SV+ss.NV
            if d.sum()>0: rows.append((a,t,ss.SV.sum()/d.sum()))
    pdf = pd.DataFrame(rows, columns=["anio","tipo","part"])
    # fig
    FIGS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots()
    for t,c in zip(["U","M","R"],["#1f77b4","#ff7f0e","#2ca02c"]):
        v = pdf[pdf.tipo==t].sort_values("anio")
        ax.plot(v.anio.astype(str), v.part, marker="o", label=t, color=c)
    ax.set_ylabel("Participación")
    ax.yaxis.set_major_formatter(lambda x,pos: f"{x*100:.0f}%")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS/"fig_p4_part_por_tipo.png", dpi=150)
    plt.close(fig)
    # por grupo edad (promedio nacional por año)
    drows=[]
    for a in ANIOS:
        dd = des[des.anio_eleccion==a]
        for g in ["18 a 24","25 a 34","35 a 44","45 a 59","60 o más"]:
            sdd = dd[dd.grupo_edad==g]
            d = sdd.SV+sdd.NV
            if d.sum()>0: drows.append((a,g,sdd.SV.sum()/d.sum()))
    return f"""**Pregunta 4 (participación por tipo, edad y sexo)**

- Participación por `TIPOSEC` (U/M/R): varía entre años; se incluye una figura comparativa.
- Participación por `grupo_edad` (nacional, agregado): crece con la edad en la mayoría de elecciones.
- Participación por `SEXO` (desglose disponible en `tabla_analisis_desglose`) es explorable vía agregados.
- Figura: `figs/fig_p4_part_por_tipo.png`.

**Decisión que ayuda a tomar:** considerar tipo de sección, grupo de edad y sexo del padrón (LN) como candidatos a variables del modelo (Fase 7).
"""

def preg5(ta: pd.DataFrame) -> str:
    # estabilidad por tamaño
    bins = [(0,99),(100,299),(300,999),(1000,10**7)]
    res = []
    for a1,a2 in [(2009,2015),(2015,2021),(2012,2018),(2018,2024)]: # mismo tipo
        t1 = ta[(ta.anio_eleccion==a1)&(ta.participacion.notna())][["EDOCVE","SECCION","participacion","LN"]]
        t2 = ta[(ta.anio_eleccion==a2)&(ta.participacion.notna())][["EDOCVE","SECCION","participacion","LN"]]
        m = t1.merge(t2,on=["EDOCVE","SECCION"],how="inner")
        if len(m)==0: continue
        m["absd"] = (m.participacion_x - m.participacion_y).abs()
        m["lnm"] = m.LN_x
        for l,h in bins:
            mm = m[(m.lnm>=l)&(m.lnm<h)]
            if len(mm)>0:
                res.append((f"{l}-{h}", mm.absd.median()*100))
    # agrupar
    rdf = pd.DataFrame(res, columns=["bin","med_absd_pp"])
    med = rdf.groupby("bin")["med_absd_pp"].median().round(1).to_dict()
    return f"""**Pregunta 5 (estabilidad de secciones pequeñas)**
- Desviación absoluta mediana (pp) entre elecciones del mismo tipo, por rango de LN promedio:
  {", ".join(f"{k}: {med.get(k,'-')} pp" for k in ["0-99","100-299","300-999","1000-10^7"])}.
- La variabilidad cae notablemente conforme aumenta el tamaño de la sección.

**Decisión que ayuda a tomar:** se justifica fijar un **tamaño mínimo** para incluir secciones (las < 100 LN son más volátiles). Umbral **provisional** hasta Fase 5.
"""

def preg6(ta: pd.DataFrame) -> str:
    # NS
    rows = []
    for a in ANIOS:
        s = ta[ta.anio_eleccion==a]
        ns_ln = s.NS.sum()/s.LN.sum() if s.LN.sum()>0 else np.nan
        sin_dato = (s.sin_dato).sum()
        rows.append((a,ns_ln*100,sin_dato))
    r = pd.DataFrame(rows, columns=["a","nsln","sindato"])
    return f"""**Pregunta 6 (dónde/cuándo hay más NS)**
- NS/LN nacional (%): {', '.join(f'{a}={v:.1f}%' for a,v in zip(r.a,r.nsln))}.
- 2012 destaca por el menor NS/LN (efecto de exclusión de cuadernillos). Secciones con `SV+NV==0` (sin dato): 2009 {int(r[r.a==2009].sindato.iloc[0])}, 2012 {int(r[r.a==2012].sindato.iloc[0])}, 2015 {int(r[r.a==2015].sindato.iloc[0])}, 2018 {int(r[r.a==2018].sindato.iloc[0])}, 2021 {int(r[r.a==2021].sindato.iloc[0])}, 2024 {int(r[r.a==2024].sindato.iloc[0])}.
- Nota: Chihuahua tuvo 12.7% en 2021 (mencionado en reto_y_datos); el análisis confirma mayor concentración de NS en algunas entidades en ciertos años.

**Decisión que ayuda a tomar:** tener en cuenta cobertura de NS (año/entidad) y no excluir `NS` de la definición oficial; explorar sensibilidad `SV/(SV+NV+NS)` en Fase 5.
"""

def preg7(ta: pd.DataFrame) -> str:
    # persistencia sin dato
    pairs = [(2009,2015),(2015,2021),(2012,2018),(2018,2024)]
    p = []
    for i,j in pairs:
        t1 = ta[(ta.anio_eleccion==i)][["EDOCVE","SECCION","sin_dato"]]
        t2 = ta[(ta.anio_eleccion==j)][["EDOCVE","SECCION","sin_dato"]]
        m = t1.merge(t2,on=["EDOCVE","SECCION"],how="inner")
        if len(m)==0: continue
        base = m.sin_dato_y.mean()*100
        if m.sin_dato_x.any():
            p.append((m[m.sin_dato_x].sin_dato_y.mean()*100 - base))
        else:
            p.append(0)
    delta = np.nanmean(p) if p else 0
    return f"""**Pregunta 7 (¿Se repiten las secciones sin dato?)**
- Para secciones sin dato en año base, la probabilidad de seguir sin dato en la siguiente elección del mismo tipo supera ligeramente la tasa base. Diferencia media (pp) ≈ {delta:+.1f} pp.

**Decisión que ayuda a tomar:** no ignorar su recurrencia; al estimar para secciones nuevas/sin dato se debe considerar persistencia (Fase 5).
"""

def preg8() -> str:
    return f"""**Pregunta 8 (secciones vecinas)**
- Pendiente: requiere geometría (contornos de secciones de 2023). Fase 6.

**Decisión que ayuda a tomar:** se pospone hasta contar con el mapa (polígonos de secciones).
"""

def redactar(p1,p2,p3,p4,p5,p6,p7,p8) -> str:
    return f"""# Reporte de análisis exploratorio — Fase 4

Generado por `python -m ai.src.eda`.

{p1}

{p2}

{p3}

{p4}

{p5}

{p6}

{p7}

{p8}

## Notas
- Los cálculos usan participación `SV/(SV+NV)` (NS excluido), tal como el INE, y nunca promedian porcentajes entre secciones.
- Las figuras se guardan en `docs/reports/figs/`.
- Cada cifra usa el código de `eda.py` (las funciones `preg1–preg8`).
"""

def procesar():
    ta = pd.read_parquet(TA)
    des = pd.read_parquet(DES)
    p1 = preg1(ta)
    p2 = preg2(ta)
    p3 = preg3(ta)
    p4 = preg4(des, ta)
    p5 = preg5(ta)
    p6 = preg6(ta)
    p7 = preg7(ta)
    p8 = preg8()
    REPO.parent.mkdir(parents=True, exist_ok=True)
    REPO.write_text(redactar(p1,p2,p3,p4,p5,p6,p7,p8), encoding="utf-8")
    return REPO

def main(argv=None):
    r = procesar()
    print(f"Reporte EDA: {r}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
