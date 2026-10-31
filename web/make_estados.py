"""Genera estados_web.geojson (contorno de cada estado) para el mapa web.

Uso:
    python3 make_estados.py municipios_web.geojson estados_web.geojson

Une los poligonos municipales por los 2 primeros digitos de CVEGEO (clave del estado).
No usa datos externos: sale de los mismos poligonos que pinta el mapa.
"""
import argparse

import geopandas as gpd

ap = argparse.ArgumentParser()
ap.add_argument("municipios")
ap.add_argument("salida")
a = ap.parse_args()

m = gpd.read_file(a.municipios)
m["CVE_ENT"] = m["CVEGEO"].str[:2]
# buffer(0) corrige anillos invalidos antes de unir
m["geometry"] = m.geometry.buffer(0)
e = m.dissolve(by="CVE_ENT", as_index=False)[["CVE_ENT", "geometry"]]
# simplificacion ligera: solo se dibuja el borde, no hace falta el detalle municipal
e["geometry"] = e.geometry.simplify(0.002, preserve_topology=True)
e.to_file(a.salida, driver="GeoJSON", COORDINATE_PRECISION=4)
print(f"estados: {len(e)} | escrito: {a.salida}")
