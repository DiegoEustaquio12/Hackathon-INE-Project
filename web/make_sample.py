"""Genera escenarios_ejemplo.json a partir de tu tabla real, para probar el mapa.

Uso:
    python3 make_sample.py TABLA.csv equivalencias_municipios.csv escenarios_ejemplo.json

OJO: los numeros son DE EJEMPLO, no son predicciones.
  - "riesgo sin intervencion" = abstencion de la ultima intermedia (se usa solo para tener datos reales que pintar)
  - "riesgo con intervencion" = supuesto de juguete: baja 4 puntos en municipios con muchos jovenes (18-24)
Cuando exista el modelo real, solo se reemplazan estas dos columnas.
"""
import sys
import json
import numpy as np
import pandas as pd

tabla, equiv, salida = sys.argv[1:4]

t = pd.read_csv(tabla)
e = pd.read_csv(equiv, dtype=str)

t["clave_ine"] = (
    t["EDOCVE"].astype(int).astype(str).str.zfill(2)
    + t["MPIOCVE"].astype(int).astype(str).str.zfill(3)
)

# una sola "foto" por municipio: la ultima eleccion objetivo disponible
t = t[t["eleccion_objetivo"] == t["eleccion_objetivo"].max()].copy()
t = t.merge(e[["clave_ine", "clave_inegi"]], on="clave_ine", how="left")

sin_clave = t["clave_inegi"].isna().sum()
t = t.dropna(subset=["clave_inegi", "abst_ultima_intermedia"])
print(f"municipios en el JSON: {len(t)} (sin poligono o sin dato, descartados: {sin_clave})")

# la tabla puede traer proporciones (0-1) o puntos (0-100); aqui todo va en puntos
k = 100 if t["abst_ultima_intermedia"].max() <= 1.0 else 1
sin = t["abst_ultima_intermedia"] * k
brecha = t["brecha_intermedia_presidencial"] * k

jovenes = t["pct_18_24"] >= t["pct_18_24"].median()
con = (sin - np.where(jovenes, 4.0, 0.0)).clip(lower=0)

# cortes del semaforo: terciles del escenario SIN intervencion, los mismos para el escenario CON
cortes = np.percentile(sin, [100 / 3, 200 / 3])
semaforo = lambda r: (np.digitize(r, cortes) + 1).astype(int)
t["sem_sin"] = semaforo(sin)
t["sem_con"] = semaforo(con)


def num(x, nd=1):
    return None if pd.isna(x) else round(float(x), nd)


municipios = {}
for i, fila in t.iterrows():
    municipios[fila["clave_inegi"]] = {
        "nombre": fila["nombre_municipio"],
        "estado": fila["nombre_estado"],
        "ln": num(fila["ln_ultima"], 0),
        "riesgo_sin": num(sin[i]),
        "sem_sin": int(fila["sem_sin"]),
        "riesgo_con": num(con[i]),
        "sem_con": int(fila["sem_con"]),
        "dif": num(con[i] - sin[i]),
        "brecha": num(brecha[i]),
    }

salida_json = {
    "meta": {
        "cortes": [round(float(c), 1) for c in cortes],
        "aviso": "DATOS DE EJEMPLO: el riesgo es la abstencion de la ultima intermedia, no una prediccion.",
    },
    "municipios": municipios,
}
with open(salida, "w", encoding="utf-8") as f:
    json.dump(salida_json, f, ensure_ascii=False, allow_nan=False)
print("cortes del semaforo (puntos de abstencion):", salida_json["meta"]["cortes"])
print("escrito:", salida)
