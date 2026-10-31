"""Genera escenarios.json para el mapa web, juntando los tres archivos del equipo.

Uso:
    python3 make_escenarios.py escenarios_municipio.csv escenarios_detalle.csv \
        ../ai/artifacts/predicciones_2027.csv equivalencias_municipios.csv escenarios.json

De cada archivo toma:
  - escenarios_municipio.csv : prediccion sin intervencion, rango, banderas de calidad, color y cortes del semaforo
  - escenarios_detalle.csv   : los 9 escenarios (3 intervenciones x efecto 5%, 10% y 15%)
  - predicciones_2027        : brecha intermedia vs presidencial y las razones del modelo
  - equivalencias_municipios : clave INE -> clave INEGI (para unir con los poligonos)

Los colores del semaforo son los del equipo (no se recalculan aqui).
"""
import argparse
import json

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
for nombre in ("municipio", "detalle", "predicciones", "equivalencias", "salida"):
    ap.add_argument(nombre)
a = ap.parse_args()

COD = {"sin_clasificar": 0, "verde": 1, "amarillo": 2, "rojo": 3}
INTERV = ["jovenes", "hombres", "rural"]
EFECTOS = ["5", "10", "15"]


def leer(ruta):
    """CSV o parquet segun la extension (parquet necesita pyarrow)."""
    if ruta.lower().endswith((".parquet", ".pq")):
        return pd.read_parquet(ruta)
    return pd.read_csv(ruta, encoding="utf-8-sig")  # algunos CSV traen BOM


def clave_ine(df):
    return (
        df["EDOCVE"].astype(int).astype(str).str.zfill(2)
        + df["MPIOCVE"].astype(int).astype(str).str.zfill(3)
    )


def num(x, nd=2):
    return None if pd.isna(x) else round(float(x), nd)


m, d, p = leer(a.municipio), leer(a.detalle), leer(a.predicciones)
equiv = pd.read_csv(a.equivalencias, dtype=str)[["clave_ine", "clave_inegi"]]
for df in (m, d, p):
    df["clave_ine"] = clave_ine(df)

for nombre, df in (("escenarios_municipio", m), ("predicciones", p)):
    if df["clave_ine"].duplicated().any():
        raise SystemExit(f"ERROR: municipios repetidos en {nombre}")

# --- comprobaciones entre archivos -------------------------------------------------
claves = set(m["clave_ine"])
print("municipios: municipio=%d detalle=%d predicciones=%d" % (len(claves), d["clave_ine"].nunique(), p["clave_ine"].nunique()))
if claves != set(d["clave_ine"]) or claves != set(p["clave_ine"]):
    print("AVISO: los tres archivos no tienen exactamente los mismos municipios")
cmp_ = m.merge(p[["clave_ine", "abstencion_pred"]], on="clave_ine", suffixes=("", "_p"))
print("max diferencia abstencion_pred municipio vs predicciones: %.2e" % (cmp_["abstencion_pred"] - cmp_["abstencion_pred_p"]).abs().max())
for iv in INTERV:
    b = d[(d["intervencion"] == iv) & (d["efecto_pct"] == 10)].merge(m, on="clave_ine", suffixes=("", "_m"))
    dif = (b["abstencion_con"] - b["abstencion_" + iv]).abs().max()
    print(f"max diferencia detalle(10%) vs municipio, {iv}: {dif:.2e}")

# --- escenarios por municipio ------------------------------------------------------
esc = {}
for r in d.itertuples(index=False):
    e = esc.setdefault(r.clave_ine, {}).setdefault(r.intervencion, {})
    e[str(int(round(r.efecto_pct)))] = [round(r.abstencion_con * 100, 2), COD[r.color_con], round(r.reduccion_pts, 2)]

# efecto nacional de cada escenario, con TODOS los municipios (tambien los que no tienen poligono)
ln_todos = m.set_index("clave_ine")["ln_ultima"]
d["personas"] = d["reduccion_pts"] / 100 * d["clave_ine"].map(ln_todos)
totales = {}
for (iv, ef), q in d.groupby(["intervencion", "efecto_pct"]):
    totales.setdefault(iv, {})[str(int(round(ef)))] = {
        "personas": int(round(q["personas"].sum())),
        "pts": round(float(q["personas"].sum() / ln_todos.sum() * 100), 2),
    }

m = m.merge(
    p[["clave_ine", "brecha_intermedia_presidencial", "sin_censo", "razon_1", "razon_2", "razon_3"]],
    on="clave_ine", how="left",
).merge(equiv, on="clave_ine", how="left")

sin_pol = m[m["clave_inegi"].isna()]
print(f"\nsin poligono (no se pintan): {len(sin_pol)}")
print(sin_pol[["clave_ine", "nombre_municipio"]].to_string(index=False))
m = m.dropna(subset=["clave_inegi"]).reset_index(drop=True)

brecha = m["brecha_intermedia_presidencial"] * 100
brecha_cortes = [round(float(x), 1) for x in np.nanpercentile(brecha, [20, 40, 60, 80])]

BANDERAS = [("pocos_casos", "pocos casos"), ("ns_alto", "NS alto"), ("sin_censo", "sin censo")]
for col, _ in BANDERAS:
    m[col] = m[col].fillna(False).astype(bool)

municipios = {}
for i, f in m.iterrows():
    e = esc.get(f["clave_ine"], {})
    if any(len(e.get(iv, {})) != len(EFECTOS) for iv in INTERV):
        raise SystemExit(f"ERROR: faltan escenarios para {f['clave_ine']} {f['nombre_municipio']}")
    municipios[f["clave_inegi"]] = {
        "n": f["nombre_municipio"],
        "e": f["nombre_estado"],
        "ln": None if pd.isna(f["ln_ultima"]) else int(f["ln_ultima"]),
        "p": num(f["abstencion_pred"] * 100),
        "min": num(f["abstencion_min"] * 100),
        "max": num(f["abstencion_max"] * 100),
        "cs": COD[f["color_sin"]],
        "br": num(brecha[i]),
        "gr": [num(f["grupo_pct_" + iv], 1) for iv in INTERV],
        "im": [int(bool(f["grupo_imputado_" + iv])) for iv in INTERV],
        "rz": [str(f[r]) for r in ("razon_1", "razon_2", "razon_3") if pd.notna(f[r])],
        "av": [txt for col, txt in BANDERAS if f[col]],
        "esc": e,
    }

meta = {
    "corte_amarillo": num(m["corte_amarillo_pct"].dropna().iloc[0], 1),
    "corte_rojo": num(m["corte_rojo_pct"].dropna().iloc[0], 1),
    "brecha_cortes": brecha_cortes,
    "totales": totales,
    "aviso": (
        "Predicción 2027 del modelo. El color es relativo al resto del país (terciles del escenario sin intervención). "
        "La intervención es hipotética: se aplica solo a los municipios en rojo y reduce el % indicado de los "
        "abstencionistas del grupo objetivo; su efecto es un supuesto, no una medición."
    ),
}
with open(a.salida, "w", encoding="utf-8") as fh:
    json.dump({"meta": meta, "municipios": municipios}, fh, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
print(f"\nmunicipios en el JSON: {len(municipios)}")
print("cortes del semaforo:", meta["corte_amarillo"], meta["corte_rojo"], "| cortes de brecha:", brecha_cortes)
print("escrito:", a.salida)