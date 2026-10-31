
"""Genera escenarios.json para el mapa, a partir de las predicciones del modelo.

Uso:
    python3 make_escenarios.py PREDICCIONES.parquet equivalencias_municipios.csv escenarios.json

Cuando exista el escenario con intervencion:
    python3 make_escenarios.py PREDICCIONES.parquet equivalencias_municipios.csv escenarios.json --con PREDICCIONES_CON.parquet
"""
import argparse
import json

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("predicciones")
ap.add_argument("equivalencias")
ap.add_argument("salida")
ap.add_argument("--con", help="Parquet con las mismas columnas, corrido con intervencion")
a = ap.parse_args()


def clave_ine(df):
    return (
        df["EDOCVE"].astype(int).astype(str).str.zfill(2)
        + df["MPIOCVE"].astype(int).astype(str).str.zfill(3)
    )


def num(x, nd=1):
    return None if pd.isna(x) else round(float(x), nd)


# Equivalencias: sigue siendo CSV
equiv = pd.read_csv(a.equivalencias, dtype=str)[["clave_ine", "clave_inegi"]]

# Predicciones: ahora se leen desde Parquet
t = pd.read_parquet(a.predicciones)
t["clave_ine"] = clave_ine(t)

if t["clave_ine"].duplicated().any():
    raise SystemExit("ERROR: hay municipios repetidos en las predicciones")

t = t.merge(equiv, on="clave_ine", how="left")

sin_poligono = t[t["clave_inegi"].isna()]
print(f"sin poligono (no se pintan): {len(sin_poligono)}")
print(sin_poligono[["clave_ine", "nombre_municipio"]].to_string(index=False))

t = t.dropna(subset=["clave_inegi", "abstencion_pred"]).reset_index(drop=True)

# El modelo entrega proporciones (0-1); el mapa trabaja en puntos (0-100)
k = 100 if t["abstencion_pred"].max() <= 1.5 else 1

sin = t["abstencion_pred"] * k
mn = t["abstencion_min"] * k
mx = t["abstencion_max"] * k
brecha = t["brecha_intermedia_presidencial"] * k

cortes = np.percentile(sin, [100 / 3, 200 / 3])

semaforo = lambda r: (np.digitize(r, cortes) + 1).astype(int)
sem_sin = semaforo(sin)

con = sem_con = dif = None

if a.con:
    # Escenario con intervencion: tambien Parquet
    c = pd.read_parquet(a.con)
    c["clave_ine"] = clave_ine(c)
    c = c.drop_duplicates("clave_ine").set_index("clave_ine")

    con = t["clave_ine"].map(c["abstencion_pred"]) * k

    faltan = con.isna().sum()
    if faltan:
        print(f"AVISO: {faltan} municipios sin valor en el escenario con intervencion")

    sem_con = pd.Series(
        np.where(con.isna(), 0, semaforo(con.fillna(0))),
        index=t.index
    )
    dif = con - sin

BANDERAS = [
    ("pocos_casos", "pocos casos"),
    ("ns_alto", "NS alto"),
    ("sin_censo", "sin censo")
]

for col, _ in BANDERAS:
    t[col] = t[col].fillna(False).astype(bool)

municipios = {}

for i, f in t.iterrows():
    razones = [
        str(f[r])
        for r in ("razon_1", "razon_2", "razon_3")
        if pd.notna(f.get(r))
    ]

    municipios[f["clave_inegi"]] = {
        "nombre": f["nombre_municipio"],
        "estado": f["nombre_estado"],
        "ln": num(f["ln_ultima"], 0),
        "riesgo_sin": num(sin[i]),
        "min": num(mn[i]),
        "max": num(mx[i]),
        "sem_sin": int(sem_sin[i]),
        "riesgo_con": None if con is None else num(con[i]),
        "sem_con": None if sem_con is None or sem_con[i] == 0 else int(sem_con[i]),
        "dif": None if dif is None else num(dif[i]),
        "brecha": num(brecha[i]),
        "razones": razones,
        "avisos": [txt for col, txt in BANDERAS if f[col]],
    }

aviso = (
    "Predicción 2027 del modelo. El color es relativo: "
    "terciles de la predicción sin intervención. "
)
aviso += (
    "Escenario con intervención incluido."
    if a.con
    else "Escenario con intervención: pendiente."
)

out = {
    "meta": {
        "cortes": [round(float(x), 1) for x in cortes],
        "tiene_con": bool(a.con),
        "aviso": aviso,
    },
    "municipios": municipios,
}

with open(a.salida, "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, allow_nan=False)

print(f"municipios en el JSON: {len(municipios)}")
print("cortes del semaforo (puntos de abstencion):", out["meta"]["cortes"])
print("escrito:", a.salida)
