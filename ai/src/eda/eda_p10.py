"""Análisis exploratorio: pregunta 10.

Uso: python ai/src/eda/eda_p10.py
Actualiza su sección de docs/EDA/reporte_eda.md y guarda sus tablas en
 docs/EDA/resultados/. Puede ejecutarse en paralelo mediante scripts/ejecutar_eda.py.
"""
import numpy as np
import pandas as pd
from eda_common import ROOT, KEY, YEARS, GROUPS, REPORT_DIR, markdown, plotting, run_question, save
import re
import unicodedata
from scipy import sparse


def normalize(text):
    return re.sub(r"[^A-Z0-9]", "", unicodedata.normalize("NFKD", text.upper()).encode("ascii", "ignore").decode())


def question10(base, train, out, map_path, data_dir=ROOT / "data/processed"):
    import geopandas as gpd

    if not map_path.exists():
        raise FileNotFoundError(f"Falta {map_path}. Ejecuta scripts/descargar_cartografia_eda.py")
    geo = gpd.read_file(map_path, encoding="utf-8")
    assert geo.CVEGEO.is_unique and len(geo) == 2475
    geo["EDOCVE"] = geo.CVE_ENT.astype(int)
    geo["normalizado"] = geo.NOMGEO.map(normalize)
    # Variantes verificadas contra NOMGEO en la cartografía, sin coincidencias difusas.
    aliases = {
        (7, 17): "Cintalapa de Figueroa", (10, 6): "General Simón Bolívar",
        (17, 13): "Jonacatepec de Leandro Valle", (20, 43): "Juchitán de Zaragoza",
        (20, 121): "San Blas Atempa", (20, 459): "Villa de Santiago Chazumba",
        (20, 562): "Villa Hidalgo", (24, 1): "Ahualulco del Sonido 13",
        (29, 37): "Ziltlaltépec de Trinidad Sánchez Santos", (30, 47): "Cosamaloapan de Carpio",
    }
    catalog = pd.read_parquet(data_dir / "tabla_municipios_2027.parquet")
    cross = catalog[[*KEY, "nombre_estado", "nombre_municipio"]].copy()
    cross["nombre_buscado"] = [aliases.get((r.EDOCVE, r.MPIOCVE), r.nombre_municipio) for r in cross.itertuples()]
    cross["normalizado"] = cross.nombre_buscado.map(normalize)
    cross = cross.merge(geo[["EDOCVE", "normalizado", "CVEGEO", "NOMGEO"]], on=["EDOCVE", "normalizado"],
                        how="left", validate="one_to_one")
    cross["metodo"] = ["Variante de nombre explícita" if tuple(r) in aliases else "Nombre normalizado y estado" for r in cross[KEY].to_numpy()]
    cross.loc[cross.CVEGEO.isna(), "metodo"] = "Sin polígono de 2022"
    unmatched = set(map(tuple, cross.loc[cross.CVEGEO.isna(), KEY].to_numpy()))
    assert unmatched == {(25, 19), (25, 20)}, unmatched
    save(cross.drop(columns="normalizado"), "p10_equivalencias_ine_inegi", out)
    geo = geo.merge(cross[[*KEY, "CVEGEO"]].dropna(), on=["EDOCVE", "CVEGEO"], validate="one_to_one")
    invalid = int((~geo.is_valid).sum())
    geo.geometry = geo.geometry.make_valid()
    # Contacto de borde o punto (vecindad reina); no se rellenan huecos ni se inventan vecinos.
    pairs = gpd.sjoin(geo[[*KEY, "geometry"]], geo[[*KEY, "geometry"]], how="inner", predicate="touches",
                      lsuffix="a", rsuffix="b")
    edges = pairs[["EDOCVE_a", "MPIOCVE_a", "EDOCVE_b", "MPIOCVE_b"]].drop_duplicates()
    save(edges.sort_values(list(edges.columns)), "p10_vecinos", out)
    # Comparar 2021 y 2024 sobre municipios comunes con cobertura >=90%, excluyendo
    # todo territorio marcado como reconstruido en 2024 (precaución con mapa de 2022).
    stable = catalog.loc[~catalog.historial_rearmado, KEY]
    observations = base[base.AELEC.isin([2021, 2024])].merge(stable, on=KEY, validate="many_to_one")
    good = observations[(observations.conocidos > 0) & (observations.pct_ns <= .1)]
    both = good.groupby(KEY).size()
    allowed = set(both[both == 2].index)
    index = {tuple(r): i for i, r in enumerate(geo[KEY].to_numpy()) if tuple(r) in allowed}
    available = [(tuple(r[:2]), tuple(r[2:])) for r in edges.to_numpy() if tuple(r[:2]) in index and tuple(r[2:]) in index]
    nodes = sorted({x for edge in available for x in edge})
    ni = {k: i for i, k in enumerate(nodes)}
    a = np.array([ni[x] for x, y in available]); b = np.array([ni[y] for x, y in available])
    weights = sparse.csr_matrix((np.ones(len(a)), (a, b)), shape=(len(nodes), len(nodes)))
    weights = sparse.diags(1/np.asarray(weights.sum(axis=1)).ravel()) @ weights
    states = np.array([k[0] for k in nodes])
    rng = np.random.default_rng(20261025)
    results, observed = [], []
    for year in [2021, 2024]:
        s = observations[observations.AELEC == year].set_index(KEY).loc[nodes]
        for adjusted in [False, True]:
            y = s.abstencion.to_numpy(dtype=float)*100
            if adjusted:
                y = y - pd.Series(y).groupby(states).transform("mean").to_numpy()
            z = y - y.mean()
            observed.extend(dict(EDOCVE=k[0], MPIOCVE=k[1], eleccion=year,
                                 comparacion="Dentro del estado" if adjusted else "Nacional",
                                 abstencion_o_diferencia_pp=float(y[i]),
                                 promedio_vecinos_pp=float((weights@y)[i])) for i, k in enumerate(nodes))
            denominator = z@z
            moran = float(z@(weights@z)/denominator)  # filas suman 1: n/S0 = 1
            simulated = []
            for _ in range(999):
                if adjusted:
                    v = z.copy()
                    for state in np.unique(states):
                        ids = np.flatnonzero(states == state)
                        v[ids] = rng.permutation(z[ids])
                else:
                    v = rng.permutation(z)
                simulated.append(float(v@(weights@v)/denominator))
            results.append(dict(eleccion=year, comparacion="Dentro del estado" if adjusted else "Nacional",
                                municipios=len(nodes), enlaces_dirigidos=len(available),
                                relacion_con_promedio_vecinos=pd.Series(y).corr(pd.Series(weights@y)),
                                indice_moran=moran, probabilidad_permutacion=(1+np.sum(np.array(simulated) >= moran))/1000))
    r = save(pd.DataFrame(results), "p10_similitud_vecinos", out)
    save(pd.DataFrame(observed), "p10_observaciones", out)
    pd.DataFrame([dict(poligonos=len(geo), geometrias_reparadas=invalid, municipios_con_cobertura_ambos=len(allowed),
                       municipios_evaluados=len(nodes), sin_vecino_evaluable=len(allowed-set(nodes)),
                       enlaces_entre_estados=int(np.sum(states[a] != states[b]))) ]).to_csv(out / "p10_cobertura.csv", index=False)
    figure(out)
    return ["## Pregunta 10. ¿Los municipios vecinos se parecen?",
            "**Respuesta:** sí, en el conjunto comparable de 1,740 municipios. La relación con el promedio "
            "de sus vecinos es 0.69 en 2021 y 0.70 en 2024; al descontar el promedio estatal permanece "
            "en 0.47 y 0.45. La similitud no se explica únicamente por pertenecer al mismo estado.",
            "Se descargó el mapa municipal de diciembre de 2022 de INEGI, publicado por CONABIO. "
            "Se unieron **2,475 de 2,477 municipios** por estado y nombre normalizado, con diez variantes de nombre "
            "explícitas y verificables. Eldorado y Juan José Ríos no tienen polígono propio en ese mapa. "
            "No se unieron directamente los números municipales del INE y del INEGI.",
            "Dos municipios se consideran vecinos si sus polígonos comparten borde o punto. "
            f"Se repararon {invalid} geometrías inválidas antes de buscar esos contactos. "
            "Se usa el mismo conjunto de municipios en 2021 y 2024, con al menos 90% de cobertura en ambos años "
            "y sin historial marcado como reconstruido en 2024. Esta restricción reduce discrepancias entre el mapa de 2022 "
            "y los territorios electorales; no demuestra equivalencia cartográfica histórica exacta.",
            markdown(r),
            f"De los {len(allowed):,} municipios que pasan los filtros de cobertura y territorio, "
            f"{len(allowed-set(nodes))} no tienen vecino que también los pase; se excluyen de este cálculo. "
            "Son resultados del conjunto seleccionado, no de todos los municipios del país.",
            "El índice de Moran resume si municipios vecinos tienen valores parecidos: un valor positivo indica "
            "agrupación de valores altos con altos y bajos con bajos. Se compara con 999 reordenamientos al azar "
            "(semilla fija 20261025). En la comparación dentro del estado se resta el promedio estatal y los valores "
            "se reordenan únicamente dentro de cada estado. La probabilidad mostrada es unilateral para similitud positiva; "
            "no mide el tamaño de la relación ni demuestra una influencia causal entre vecinos.",
            "**Decisión que apoya:** además de separar elecciones en el tiempo, evaluar el futuro modelo dejando "
            "estados o bloques geográficos completos fuera del entrenamiento. Una división municipal aleatoria puede "
            "dar resultados demasiado favorables si mezcla zonas muy relacionadas. Usar también un margen de separación "
            "espacial si se busca evaluar territorios sin vecinos conocidos. No se entrenó ningún modelo ni se añadieron "
            "polígonos como predictores.",
            "Fuente: [metadatos CONABIO](http://geoportal.conabio.gob.mx/metadatos/doc/html/mun22gw.html). "
            "El ZIP y su SHA256 se conservan en `data/external/cartografia/mun22gw/fuente.json`. "
            "Detalle: archivos `p10_*.csv`; la equivalencia es para este EDA y no sustituye la revisión cartográfica final de la Fase 6.",
            '![Similitud entre vecinos](eda_p10_vecinos.png)']

def figure(out):
    plt = plotting()
    neighbours = pd.read_csv(out / "p10_observaciones.csv")
    s = neighbours[(neighbours.eleccion == 2024) & (neighbours.comparacion == "Dentro del estado")]
    fig, ax = plt.subplots(figsize=(8, 6), layout="constrained")
    cells = ax.hexbin(s.abstencion_o_diferencia_pp, s.promedio_vecinos_pp, gridsize=28, mincnt=1, cmap="Blues")
    ax.axhline(0, color="gray", linewidth=.5)
    ax.axvline(0, color="gray", linewidth=.5)
    ax.set(title="Vecinos parecidos dentro del estado (2024)",
           xlabel="Diferencia del municipio frente al estado (puntos)",
           ylabel="Diferencia promedio de sus vecinos (puntos)")
    fig.colorbar(cells, ax=ax, label="Municipios por celda")
    fig.savefig(REPORT_DIR / "eda_p10_vecinos.png", dpi=160)
    plt.close(fig)


def main():
    run_question(10, question10, __file__)


if __name__ == "__main__":
    main()
