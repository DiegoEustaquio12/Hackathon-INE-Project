#!/usr/bin/env python3
"""Fase 2: tendencias de participación, desfase de edades y adultos mayores en la lista nominal.

Parte de data/interim/ccpc_unificado.parquet (lo genera carga_limpieza.py) y produce:
  - docs/reports/reporte_tendencias.md
  - data/processed/tendencias/*.csv   (tablas agregadas, sin datos personales)

Uso (desde la raíz del repo):
    python ai/src/data_prep/analisis_tendencias.py

IMPORTANTE sobre lo que son estimaciones:
  * "Adultos mayores que probablemente fallecieron" NO está en los datos: es una estimación
    (cota superior) que compara la abstención de 80+ contra la de 60-74 años.
  * Los "eventos externos" son contexto cualitativo escrito a mano (EVENTOS, abajo).
    Con 6 elecciones no se puede medir su efecto; sirven para interpretar, no para atribuir causas.
"""
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
PARQUET = ROOT / "data" / "interim" / "ccpc_unificado.parquet"
OUT_DIR = ROOT / "data" / "processed" / "tendencias"
OUT_REPORT = ROOT / "docs" / "reports" / "reporte_tendencias.md"

# Grupo de referencia para estimar la "abstención normal" de adultos mayores vivos.
BASE_MIN, BASE_MAX = 60, 74
# Edades que se revisan como posible rezago de la lista nominal (personas fallecidas aún inscritas).
MAYORES_MIN = 80

BINS = [-1, 17, 24, 34, 44, 59, 74, 79, 84, 89, 99, 400]
ETIQ = ["<18", "18-24", "25-34", "35-44", "45-59", "60-74", "75-79", "80-84", "85-89", "90-99", "100+"]

# Contexto por elección. ES TEXTO ESCRITO A MANO a partir de conocimiento general: revisar y citar
# fuentes (INE, INEGI, prensa) antes de usarlo en el reporte final. No son variables del modelo.
EVENTOS = {
    2009: dict(fecha="5 jul 2009", contexto=(
        "Crisis económica global 2008-09; brote de influenza A(H1N1) (abr-may 2009) con medidas sanitarias; "
        "campaña ciudadana por anular el voto; violencia por la estrategia contra el crimen organizado.")),
    2012: dict(fecha="1 jul 2012", contexto=(
        "Presidencial con regreso del PRI; movimiento estudiantil #YoSoy132; elecciones locales concurrentes. "
        "Ojo con los datos: la lista nominal de 2012 excluye cuadernillos no disponibles, y casi no tiene NS.")),
    2015: dict(fecha="7 jun 2015", contexto=(
        "Intermedia posterior al caso Ayotzinapa (sep 2014) y protestas; campañas por voto nulo/abstención; "
        "bloqueos y boicot de la CNTE en varios estados; primeras candidaturas independientes; 9 gubernaturas.")),
    2018: dict(fecha="1 jul 2018", contexto=(
        "Presidencial con elecciones locales concurrentes en casi todas las entidades y muchísimos cargos en disputa; "
        "alta violencia política; alternancia con Morena.")),
    2021: dict(fecha="6 jun 2021", contexto=(
        "Intermedia en plena pandemia de COVID-19 (medidas sanitarias, vacunación en curso); 15 gubernaturas; "
        "violencia política; fuerte polarización.")),
    2024: dict(fecha="2 jun 2024", contexto=(
        "Presidencial con las dos principales candidatas mujeres; elecciones locales concurrentes en las 32 entidades "
        "(9 gubernaturas); violencia política elevada; primer año con código de sexo no binario en el CCPC.")),
}


def md(df):
    """DataFrame -> tabla markdown (sin depender de tabulate)."""
    cols = list(df.columns)
    filas = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        celdas = []
        for c, v in zip(cols, r):
            if c == "anio":
                celdas.append(str(v))
            elif v is None or (isinstance(v, float) and np.isnan(v)):
                celdas.append("—")
            elif isinstance(v, (float, np.floating)) and not float(v).is_integer():
                celdas.append(f"{v:,.2f}")
            elif isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
                celdas.append(f"{int(v):,}")
            else:
                celdas.append(str(v))
        filas.append("| " + " | ".join(celdas) + " |")
    return "\n".join(filas)


def mediana_ponderada(edades, pesos):
    edades, pesos = np.asarray(edades), np.asarray(pesos, dtype=float)
    if pesos.sum() <= 0:
        return np.nan
    o = np.argsort(edades)
    e, w = edades[o], pesos[o]
    c = np.cumsum(w)
    return float(e[np.searchsorted(c, c[-1] / 2)])


# --------------------------------------------------------------------------- 1. Tendencia
def tendencia_nacional(con):
    df = con.execute("""
        SELECT anio, any_value(tipo_eleccion) AS tipo,
               sum(ln)::BIGINT AS ln, sum(sv)::BIGINT AS sv, sum(nv)::BIGINT AS nv, sum(ns)::BIGINT AS ns,
               sum(ln) FILTER (sexo = 0)::DOUBLE AS ln_h, sum(ln) FILTER (sexo = 1)::DOUBLE AS ln_m,
               sum(sv) FILTER (sexo = 0)::DOUBLE AS sv_h, sum(sv) FILTER (sexo = 1)::DOUBLE AS sv_m
        FROM read_parquet(?) GROUP BY anio ORDER BY anio""", [PARQUET.as_posix()]).df()
    df["participacion_pct"] = 100 * df.sv / (df.sv + df.nv)
    df["abstencion_pct"] = 100 * df.nv / (df.sv + df.nv)
    df["ns_pct_de_ln"] = 100 * df.ns / df.ln
    df["iml"] = 100 * df.ln_h / df.ln_m
    df["imv"] = 100 * df.sv_h / df.sv_m
    df["cambio_pp_vs_anterior"] = df.participacion_pct.diff()
    df["cambio_pp_vs_misma_clase"] = df.groupby("tipo").participacion_pct.diff()
    df["cambio_ln_pct_vs_anterior"] = 100 * df.ln.pct_change()
    return df.drop(columns=["ln_h", "ln_m", "sv_h", "sv_m"])


def tendencia_estado(con):
    df = con.execute("""
        SELECT anio, any_value(tipo_eleccion) AS tipo, edo_nom AS estado,
               100.0 * sum(sv) / nullif(sum(sv + nv), 0) AS participacion_pct
        FROM read_parquet(?) GROUP BY anio, edo_nom ORDER BY estado, anio""", [PARQUET.as_posix()]).df()
    return df


def resumen_estado(est):
    """Cambio por estado entre la primera y la última elección de cada clase (solo se compara lo comparable)."""
    filas = []
    for tipo, g in est.groupby("tipo"):
        anios = sorted(g.anio.unique())
        if len(anios) < 2:
            continue
        a0, a1 = anios[0], anios[-1]
        p = g.pivot(index="estado", columns="anio", values="participacion_pct")
        d = (p[a1] - p[a0]).rename("cambio_pp").reset_index()
        d["tipo"], d["desde"], d["hasta"] = tipo, a0, a1
        filas.append(d)
    return pd.concat(filas, ignore_index=True) if filas else pd.DataFrame()


# --------------------------------------------------------------------------- 2. Edades
def tabla_edades(con):
    return con.execute("""
        SELECT anio, edo_nom, edad, sum(ln)::BIGINT AS ln, sum(sv)::BIGINT AS sv, sum(nv)::BIGINT AS nv
        FROM read_parquet(?) GROUP BY anio, edo_nom, edad""", [PARQUET.as_posix()]).df()


def desfase_edades(ed):
    """Edad de quienes votaron vs edad de la lista nominal (y de quienes se abstuvieron)."""
    nac = ed.groupby(["anio", "edad"], as_index=False)[["ln", "sv", "nv"]].sum()
    filas = []
    for anio, g in nac.groupby("anio"):
        media = lambda w: float((g.edad * g[w]).sum() / g[w].sum())
        filas.append(dict(
            anio=anio,
            edad_media_ln=media("ln"), edad_media_votantes=media("sv"), edad_media_abstencion=media("nv"),
            edad_mediana_ln=mediana_ponderada(g.edad, g.ln),
            edad_mediana_votantes=mediana_ponderada(g.edad, g.sv),
        ))
    out = pd.DataFrame(filas)
    out["desfase_media_anios"] = out.edad_media_votantes - out.edad_media_ln
    out["desfase_mediana_anios"] = out.edad_mediana_votantes - out.edad_mediana_ln
    return out


def participacion_por_etapa(ed):
    nac = ed.groupby(["anio", "edad"], as_index=False)[["ln", "sv", "nv"]].sum()
    nac["etapa"] = pd.cut(nac.edad, BINS, labels=ETIQ)
    t = nac.groupby(["anio", "etapa"], observed=True)[["ln", "sv", "nv"]].sum().reset_index()
    t["participacion_pct"] = 100 * t.sv / (t.sv + t.nv).replace(0, np.nan)
    t["pct_de_ln"] = 100 * t.ln / t.groupby("anio").ln.transform("sum")
    t["pct_de_votantes"] = 100 * t.sv / t.groupby("anio").sv.transform("sum")
    return t


# --------------------------------------------------------------------------- 3. Adultos mayores
def _exceso(sv, nv, base):
    """Abstención por encima de la que tendría el grupo si votara como el grupo base."""
    return np.maximum(0.0, nv - (sv + nv) * (1 - base))


def adultos_mayores(ed):
    """Estimación del rezago de la lista nominal en edades altas. Es una COTA SUPERIOR, no un conteo."""
    nac = ed.groupby(["anio", "edad"], as_index=False)[["ln", "sv", "nv"]].sum()
    base = (nac[nac.edad.between(BASE_MIN, BASE_MAX)].groupby("anio")[["sv", "nv"]].sum())
    base = (base.sv / (base.sv + base.nv)).rename("part_base")

    nac = nac.join(base, on="anio")
    nac["grupo"] = pd.cut(nac.edad, BINS, labels=ETIQ)
    may = nac[nac.edad >= MAYORES_MIN]
    g = may.groupby(["anio", "grupo"], observed=True).agg(
        ln=("ln", "sum"), sv=("sv", "sum"), nv=("nv", "sum"), part_base=("part_base", "first")).reset_index()
    g["participacion_pct"] = 100 * g.sv / (g.sv + g.nv).replace(0, np.nan)
    g["exceso_abstencion_est"] = _exceso(g.sv, g.nv, g.part_base)
    g["pct_del_grupo_en_ln"] = 100 * g.exceso_abstencion_est / g.ln.replace(0, np.nan)
    por_grupo = g.drop(columns="part_base")

    tot = nac.groupby("anio")[["ln", "sv", "nv"]].sum()
    m = may.groupby("anio").agg(
        ln_mayores=("ln", "sum"), sv_mayores=("sv", "sum"), nv_mayores=("nv", "sum"))
    m["edad_media_mayores_85"] = (nac[nac.edad >= 85].assign(p=lambda d: d.edad * d.ln)
                                  .groupby("anio").p.sum() / nac[nac.edad >= 85].groupby("anio").ln.sum())
    m["ln_100_mas"] = nac[nac.edad >= 100].groupby("anio").ln.sum()
    m["ln_100_mas"] = m.ln_100_mas.fillna(0)
    m["exceso_abstencion_est"] = g.groupby("anio").exceso_abstencion_est.sum()
    m = m.join(tot).join(base)
    m["pct_ln_mayores"] = 100 * m.ln_mayores / m.ln
    m["pct_ln_exceso_est"] = 100 * m.exceso_abstencion_est / m.ln
    m["participacion_pct"] = 100 * m.sv / (m.sv + m.nv)
    # Participación "ajustada": se quita del denominador el exceso estimado (posibles fallecidos inscritos).
    m["participacion_ajustada_pct"] = 100 * m.sv / (m.sv + m.nv - m.exceso_abstencion_est)
    m["ajuste_pp"] = m.participacion_ajustada_pct - m.participacion_pct
    m["part_base_pct"] = 100 * m.part_base
    cols = ["ln", "ln_mayores", "pct_ln_mayores", "ln_100_mas", "edad_media_mayores_85", "part_base_pct",
            "exceso_abstencion_est", "pct_ln_exceso_est", "participacion_pct", "participacion_ajustada_pct", "ajuste_pp"]
    return m[cols].reset_index(), por_grupo


def adultos_mayores_estado(ed):
    d = ed.copy()
    b = d[d.edad.between(BASE_MIN, BASE_MAX)].groupby(["anio", "edo_nom"])[["sv", "nv"]].sum()
    b = (b.sv / (b.sv + b.nv)).rename("part_base")
    m = d[d.edad >= MAYORES_MIN].groupby(["anio", "edo_nom"])[["ln", "sv", "nv"]].sum().join(b)
    m["exceso_abstencion_est"] = _exceso(m.sv, m.nv, m.part_base)
    tot = d.groupby(["anio", "edo_nom"]).ln.sum().rename("ln_total")
    m = m.join(tot)
    m["pct_ln_exceso_est"] = 100 * m.exceso_abstencion_est / m.ln_total
    return m.reset_index().rename(columns={"edo_nom": "estado", "ln": "ln_mayores"})[
        ["anio", "estado", "ln_mayores", "exceso_abstencion_est", "pct_ln_exceso_est"]]


# --------------------------------------------------------------------------- Reporte
def frase_tendencia(t):
    out = []
    for tipo, g in t.groupby("tipo"):
        g = g.sort_values("anio")
        if len(g) < 2:
            continue
        a, b = g.iloc[0], g.iloc[-1]
        sentido = "subió" if b.participacion_pct > a.participacion_pct else "bajó"
        out.append(f"- En elecciones **{tipo}s**, la participación {sentido} de {a.participacion_pct:.1f}% ({int(a.anio)}) "
                   f"a {b.participacion_pct:.1f}% ({int(b.anio)}): {b.participacion_pct - a.participacion_pct:+.1f} puntos.")
    return "\n".join(out) or "- Hace falta más de una elección por clase para ver tendencia."


def main():
    if not PARQUET.exists():
        raise SystemExit(f"No existe {PARQUET}. Corre primero ai/src/data_prep/carga_limpieza.py")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    nac = tendencia_nacional(con)
    est = tendencia_estado(con)
    res_est = resumen_estado(est)
    ed = tabla_edades(con)
    desf = desfase_edades(ed)
    etapas = participacion_por_etapa(ed)
    may, may_grupo = adultos_mayores(ed)
    may_est = adultos_mayores_estado(ed)
    eventos = pd.DataFrame([dict(anio=a, **v) for a, v in EVENTOS.items()])
    eventos = eventos[eventos.anio.isin(nac.anio)]

    for nombre, df in [("tendencia_nacional", nac), ("tendencia_estado", est), ("cambio_por_estado", res_est),
                       ("desfase_edad", desf), ("participacion_por_etapa", etapas),
                       ("adultos_mayores_nacional", may), ("adultos_mayores_grupo", may_grupo),
                       ("adultos_mayores_estado", may_est), ("eventos_contexto", eventos)]:
        df.to_csv(OUT_DIR / f"{nombre}.csv", index=False, encoding="utf-8")

    t = nac[["anio", "tipo", "ln", "participacion_pct", "abstencion_pct", "ns_pct_de_ln",
             "cambio_pp_vs_anterior", "cambio_pp_vs_misma_clase", "iml", "imv"]]
    cambios = ""
    if len(res_est):
        top = lambda d, n, asc: d.sort_values("cambio_pp", ascending=asc).head(n)[["estado", "desde", "hasta", "cambio_pp"]]
        for tipo, d in res_est.groupby("tipo"):
            cambios += (f"\n**{tipo.capitalize()}s: mayor aumento**\n\n{md(top(d, 5, False))}\n"
                        f"\n**{tipo.capitalize()}s: mayor caída**\n\n{md(top(d, 5, True))}\n")

    top_mayor = may_est.sort_values(["anio", "pct_ln_exceso_est"], ascending=[True, False]).groupby("anio").head(3)
    ev = nac[["anio", "tipo", "participacion_pct"]].merge(eventos, on="anio", how="left")[
        ["anio", "tipo", "participacion_pct", "fecha", "contexto"]]

    prom = may[["pct_ln_mayores", "pct_ln_exceso_est", "ajuste_pp", "edad_media_mayores_85"]].mean()

    reporte = f"""# Reporte de tendencias, edades y lista nominal (Fase 2)

Generado por `ai/src/data_prep/analisis_tendencias.py`. Tablas en `data/processed/tendencias/`.

## 1. Tendencia de participación
{md(t)}

Participación = SV / (SV + NV); `abstencion_pct` es su complemento y `ns_pct_de_ln` = NS / LN.
`cambio_pp_vs_anterior` compara con la elección anterior (sea del tipo que sea);
`cambio_pp_vs_misma_clase` compara con la elección anterior **del mismo tipo** (intermedia con intermedia,
presidencial con presidencial), que es la comparación justa.

{frase_tendencia(nac)}

**Cambio por estado** entre la primera y la última elección de cada tipo:
{cambios or chr(10) + 'Sin datos suficientes.' + chr(10)}

## 2. Desfase de edades entre votantes y lista nominal
{md(desf.round(2))}

`desfase_*` = edad de quienes votaron menos edad de la lista nominal. Si es **positivo**, votan personas más
grandes que el promedio de la lista (los jóvenes participan menos). Si crece con los años, la brecha generacional
de participación se está ampliando.

Participación y peso de cada etapa de vida:
{md(etapas.round(2))}

## 3. Adultos mayores en la lista nominal (estimación)

**Método.** Se toma la participación de las personas de {BASE_MIN}-{BASE_MAX} años como la "abstención normal" de
adultos mayores vivos. En 80+ se calcula cuánta abstención **sobra** respecto a ese nivel
(`exceso_abstencion_est`). Ese exceso incluye personas fallecidas que siguen inscritas, pero también adultos
mayores vivos con dificultades para votar (salud, movilidad), así que es una **cota superior**. Se usa como
orden de magnitud, no como conteo de fallecidos.

{md(may.round(2))}

- `edad_media_mayores_85`: edad media de quienes tienen 85 años o más en la lista.
- `ln_100_mas`: personas de 100 años o más inscritas. Es poco probable que sigan vivas casi todas.
- `participacion_ajustada_pct` quita el exceso estimado del denominador; `ajuste_pp` es cuánto sube por ello.

**Promedio de todos los años:** {prom.pct_ln_mayores:.2f}% de la lista tiene {MAYORES_MIN}+ años; el exceso
estimado equivale a {prom.pct_ln_exceso_est:.2f}% de la lista y subiría la participación en
{prom.ajuste_pp:.2f} puntos; edad media de los 85+: {prom.edad_media_mayores_85:.1f} años.

Detalle por grupo de edad:
{md(may_grupo.round(2))}

Estados con mayor exceso estimado (3 por año):
{md(top_mayor.round(2))}

## 4. Contexto externo por elección
{md(ev)}

**Cómo usar esto:** son hechos de contexto para **interpretar** los cambios, no variables medidas. Con solo seis
elecciones no se puede separar el efecto de un evento del efecto de ser presidencial o intermedia, ni del
reseccionamiento o de cambios en la lista nominal. Conviene **verificar cada dato con fuentes** antes de citarlo
en el reporte final, y presentarlo como hipótesis.

## 5. Límites
- Las cifras son agregados nacionales y por estado: no se sabe quién votó, solo cuántas personas por sección, sexo y edad.
- Las comparaciones entre años usan secciones que pueden haber cambiado por reseccionamiento.
- 2012 tiene una lista nominal menor y casi sin NS por exclusión de cuadernillos: compárala con cuidado.
- El CCPC no incluye casillas especiales ni votantes en el extranjero.
"""
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(reporte, encoding="utf-8")
    print(t.round(2).to_string(index=False))
    print(f"\nReporte: {OUT_REPORT}\nTablas:  {OUT_DIR}")


if __name__ == "__main__":
    main()
