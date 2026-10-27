"""Features temporales candidatas; su mejora se evalúa en la Fase 7."""
import pandas as pd

DESCRIPCIONES = [
    ("cambio_presidenciales", "Última abstención presidencial menos la penúltima con dato; vacío si hay menos de dos"),
    ("anios_desde_ultima_intermedia", "Años entre el objetivo y la última intermedia con abstención conocida; vacío sin historial"),
    ("anios_desde_ultima_presidencial", "Años entre el objetivo y la última presidencial con abstención conocida; vacío sin historial"),
    ("abst_ultima_presidencial_sin_2012", "Última abstención presidencial conocida excluyendo 2012; vacío sin antecedentes"),
    ("abst_prom_presidenciales_sin_2012", "Promedio simple de tasas presidenciales conocidas excluyendo 2012; vacío sin antecedentes"),
    ("brecha_intermedia_presidencial_sin_2012", "Promedio de intermedias conocidas menos promedio de presidenciales conocidas sin 2012; vacío si falta uno de los dos tipos"),
    ("n_presidenciales_previas_sin_2012", "Número de presidenciales anteriores con tasa conocida excluyendo 2012; cero sin presidenciales y vacío si no hay ningún historial territorial asignado"),
    ("cambio_intermedias_vs_pais", "Cambio entre las dos últimas intermedias conocidas de (abstención municipal menos abstención nacional de cada elección); vacío con menos de dos"),
    ("cambio_presidenciales_vs_pais", "Cambio entre las dos últimas presidenciales conocidas de (abstención municipal menos abstención nacional de cada elección); vacío con menos de dos"),
]
COLUMNAS = [nombre for nombre, _ in DESCRIPCIONES]
LLAVE = ["EDOCVE", "MPIOCVE"]


def calcular_features_temporales(hist: pd.DataFrame, objetivo: int, nacional: pd.Series) -> pd.DataFrame:
    """Recibe historial ya reconstruido al territorio de la foto; rechaza el futuro.

    No usa groupby.last(), que podría mezclar valores de distintas elecciones.
    Las elecciones sin tasa no cuentan como antecedentes conocidos.
    nacional contiene NV nacional / (SV + NV nacional), calculado antes de reconstruir
    territorios. Solo se consultan años presentes en el historial anterior al objetivo.
    """
    if hist["AELEC"].ge(objetivo).any():
        raise ValueError("El historial debe contener solo elecciones anteriores al objetivo")
    if hist.duplicated([*LLAVE, "AELEC"]).any():
        raise ValueError("Historial municipal duplicado")
    conocidos = hist.loc[hist["abstencion"].notna()].sort_values([*LLAVE, "AELEC"])
    if not nacional.index.is_unique or conocidos["AELEC"].map(nacional).isna().any():
        raise ValueError("Falta una tasa nacional histórica o hay años nacionales duplicados")
    resultado = pd.DataFrame(index=hist.groupby(LLAVE).size().index)
    for tipo in ("intermedia", "presidencial"):
        h = conocidos.loc[conocidos["tipo"] == tipo].copy()
        h["anterior"] = h.groupby(LLAVE)["abstencion"].shift()
        h["vs_pais"] = h["abstencion"] - h["AELEC"].map(nacional)
        h["cambio_vs_pais"] = h.groupby(LLAVE)["vs_pais"].diff()
        ultima = h.groupby(LLAVE).tail(1).set_index(LLAVE)
        resultado[f"cambio_{'intermedias' if tipo == 'intermedia' else 'presidenciales'}_vs_pais"] = ultima["cambio_vs_pais"]
        resultado[f"anios_desde_ultima_{tipo}"] = objetivo - ultima["AELEC"]
        if tipo == "presidencial":
            resultado["cambio_presidenciales"] = ultima["abstencion"] - ultima["anterior"]
    sin_2012 = conocidos.loc[(conocidos["tipo"] == "presidencial") & conocidos["AELEC"].ne(2012)]
    g = sin_2012.groupby(LLAVE)
    resultado["abst_ultima_presidencial_sin_2012"] = g.tail(1).set_index(LLAVE)["abstencion"]
    resultado["abst_prom_presidenciales_sin_2012"] = g["abstencion"].mean()
    resultado["n_presidenciales_previas_sin_2012"] = g.size().reindex(resultado.index).fillna(0).astype("int64")
    prom_intermedias = conocidos.loc[conocidos["tipo"] == "intermedia"].groupby(LLAVE)["abstencion"].mean()
    resultado["brecha_intermedia_presidencial_sin_2012"] = prom_intermedias - resultado["abst_prom_presidenciales_sin_2012"]
    return resultado[COLUMNAS]
