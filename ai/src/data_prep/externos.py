"""Features sociodemográficas externas por municipio (ECEG 2010 y 2020).

Este módulo concentra la lectura de los ECEG del INEGI, la agregación de sección a
municipio y la unión con las tablas canónicas de la Fase 3. No escribe las tablas
canónicas: `fase3.py` lo usa para agregar las columnas `ext_*` a
`tabla_municipios_entrenamiento` y `tabla_municipios_2027`.

Regla de vintage: cada fila usa el censo más reciente ANTERIOR a su elección
objetivo. 2015 y 2018 usan ECEG 2010; 2021, 2024 y 2027 usan ECEG 2020.

Reglas de agregación:
- Los conteos se suman por municipio.
- Las tasas se calculan después de sumar: suma(numerador) / suma(denominador).
- Los promedios se ponderan por su denominador (GRAPROES por P_15YMAS; PROM_OCUP
  por VIVPAR_HAB).
- Las tasas de vivienda usan el universo de las variables VPH_*: VIVPAR_HAB en
  2010 y VIVPARH_CV (viviendas con características captadas) en 2020.
- Un denominador en cero produce NaN, no cero.
- Los valores negativos (el centinela -6 de 2020 en vivienda) se tratan como
  faltantes.
- En el ECEG 2010 de Chiapas (07), GRAPROES viene escalado por 100; se corrige y
  se descartan los valores resultantes mayores a 30 años.
- Los municipios creados después del censo quedan sin dato y se marcan con
  tiene_eceg_2010 / tiene_eceg_2020; no se imputan aquí.

Los Censos Económicos no se usan: los conjuntos de datos abiertos descargados
(2024, 2014 y 2000) son solo nacionales y no permiten un cruce municipal.
"""
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[3]
EXTERNOS = RAIZ / "data" / "external" / "sociodemografico"
SALIDA_EXTERNOS = RAIZ / "data" / "interim" / "externos"
PROCESADOS = RAIZ / "data" / "processed"

LLAVE = ["EDOCVE", "MPIOCVE"]

# Conteos que se suman por municipio. No incluye GRAPROES ni PROM_OCUP porque son
# promedios y se manejan aparte, ponderados.
COLUMNAS_SUMA = [
    "P15YM_AN", "P15YM_SE", "P_15YMAS", "P15PRI_IN", "P15SEC_IN", "P18YM_PB", "P_18YMAS",
    "PEA", "PDESOCUP", "PEA_F", "P_12YMAS", "P_12YMAS_F", "POCUPADA",
    "VPH_S_ELEC", "VPH_AGUAFV", "VPH_NODREN", "VPH_PISOTI", "VPH_INTER", "VPH_PC",
    "VPH_CEL", "VPH_REFRI", "VPH_AUTOM", "VIVPAR_HAB",
    "PCLIM_VIS", "PCLIM_MOT2", "POBTOT", "P3YM_HLI", "P_3YMAS", "PNACOE",
    "PHOGJEF_F", "POBHOG", "TOTHOG", "POB0_14", "POB15_64", "POB65_MAS",
    "POBMAS", "POBFEM",
]
COLUMNAS_DATOS = COLUMNAS_SUMA + ["GRAPROES", "PROM_OCUP"]
# Denominador de las tasas de vivienda en 2020. En 2010 se usa VIVPAR_HAB, que
# ya está en COLUMNAS_SUMA. VIVPARH_CV solo existe en la base de 2020.
COLUMNAS_EXTRA = ["VIVPARH_CV"]

# Nombre de la feature -> definición y fórmula para el diccionario y el reporte.
DICCIONARIO_EXTERNOS = [
    ("pct_analfabeta", "Población de 15 años y más analfabeta", "P15YM_AN / P_15YMAS"),
    ("pct_sin_escolaridad", "Población de 15 años y más sin escolaridad", "P15YM_SE / P_15YMAS"),
    ("escolaridad_promedio", "Grado promedio de escolaridad (ponderado por población de 15+)",
     "suma(GRAPROES × P_15YMAS) / suma(P_15YMAS)"),
    ("pct_primaria_incompleta", "Población de 15 años y más con primaria incompleta",
     "P15PRI_IN / P_15YMAS"),
    ("pct_secundaria_incompleta", "Población de 15 años y más con secundaria incompleta",
     "P15SEC_IN / P_15YMAS"),
    ("pct_posbasica", "Población de 18 años y más con educación posbásica", "P18YM_PB / P_18YMAS"),
    ("tasa_participacion", "Población de 12 años y más económicamente activa", "PEA / P_12YMAS"),
    ("tasa_desocupacion", "Población de 12 años y más desocupada", "PDESOCUP / PEA"),
    ("tasa_participacion_femenina", "Mujeres de 12 años y más económicamente activas",
     "PEA_F / P_12YMAS_F"),
    ("tasa_ocupacion", "Población de 12 años y más ocupada", "POCUPADA / PEA"),
    ("pct_sin_electricidad", "Viviendas habitadas sin energía eléctrica", "VPH_S_ELEC / VIVPAR_HAB*"),
    ("pct_sin_agua_entubada", "Viviendas habitadas sin agua entubada en la vivienda",
     "VPH_AGUAFV / VIVPAR_HAB*"),
    ("pct_sin_drenaje", "Viviendas habitadas sin drenaje", "VPH_NODREN / VIVPAR_HAB*"),
    ("pct_piso_tierra", "Viviendas habitadas con piso de tierra", "VPH_PISOTI / VIVPAR_HAB*"),
    ("pct_con_internet", "Viviendas habitadas con internet", "VPH_INTER / VIVPAR_HAB*"),
    ("pct_con_computadora", "Viviendas habitadas con computadora, laptop o tablet",
     "VPH_PC / VIVPAR_HAB*"),
    ("pct_con_celular", "Viviendas habitadas con teléfono celular", "VPH_CEL / VIVPAR_HAB*"),
    ("pct_con_refrigerador", "Viviendas habitadas con refrigerador", "VPH_REFRI / VIVPAR_HAB*"),
    ("pct_con_automovil", "Viviendas habitadas con automóvil o camioneta", "VPH_AUTOM / VIVPAR_HAB*"),
    ("promedio_ocupantes", "Promedio de ocupantes por vivienda (ponderado)",
     "suma(PROM_OCUP × VIVPAR_HAB) / suma(VIVPAR_HAB)"),
    ("pct_limitacion_visual", "Población con limitación para ver, aun usando lentes",
     "PCLIM_VIS / POBTOT"),
    ("pct_limitacion_motriz", "Población con limitación para vestirse, bañarse o comer",
     "PCLIM_MOT2 / POBTOT"),
    ("pct_lengua_indigena", "Población de 3 años y más que habla alguna lengua indígena",
     "P3YM_HLI / P_3YMAS"),
    ("pct_nacido_otra_entidad", "Población nacida en otra entidad", "PNACOE / POBTOT"),
    ("pct_jefatura_femenina", "Población en hogares con persona de referencia mujer",
     "PHOGJEF_F / POBHOG"),
    ("promedio_hogar", "Promedio de personas por hogar censal", "POBHOG / TOTHOG"),
    ("razon_dependencia", "Razón de dependencia demográfica", "(POB0_14 + POB65_MAS) / POB15_64"),
    ("relacion_hombres_mujeres", "Hombres por cada mujer", "POBMAS / POBFEM"),
]
FEATURES = [nombre for nombre, _, _ in DICCIONARIO_EXTERNOS]

# Features que deben quedar entre 0 y 1. Las demás son promedios o razones.
FEATURES_TASA = [f for f in FEATURES if f.startswith(("pct_", "tasa_"))]

# Columnas que se agregan a las tablas canónicas. El orden importa para el
# diccionario de datos.
COLUMNAS_METADATA = ["censo_fuente", "tiene_eceg_2010", "tiene_eceg_2020"]
COLUMNAS_EXTERNAS = [*COLUMNAS_METADATA, *(f"ext_{f}" for f in FEATURES)]


def columnas_externas() -> list[str]:
    """Columnas que `unir_externos` agrega, en el orden del diccionario."""
    return list(COLUMNAS_EXTERNAS)


def leer_csv(ruta: Path) -> pd.DataFrame:
    """Lee un CSV del INEGI probando UTF-8 y Latin-1."""
    for codificacion in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(ruta, dtype=str, encoding=codificacion)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"No se pudo leer {ruta} con UTF-8 ni Latin-1")


def a_numero(serie: pd.Series) -> pd.Series:
    """Convierte a número y trata los negativos (centinela -6) como faltantes."""
    texto = serie.astype(str).str.replace(",", "", regex=False).str.strip()
    numero = pd.to_numeric(texto, errors="coerce")
    return numero.mask(numero < 0)


def buscar_archivo(carpeta: Path, token: str) -> Path:
    """Encuentra un CSV cuyo nombre contiene `token`, sin distinguir mayúsculas."""
    encontrados = [
        p for p in carpeta.rglob("*")
        if p.is_file() and p.suffix.lower() == ".csv" and token in p.name.lower()
    ]
    if len(encontrados) != 1:
        raise FileNotFoundError(f"Se esperaba un CSV con '{token}' en {carpeta}; hay {len(encontrados)}")
    return encontrados[0]


def leer_eceg2010() -> pd.DataFrame:
    """Concatena las 32 bases estatales de secciones de 2010.

    El archivo de Chiapas (07) trae GRAPROES escalado por 100; se corrige para
    que su media ponderada quede en ~6.7, comparable con los demás estados. Los
    valores resultantes mayores a 30 años se tratan como faltantes.
    """
    carpetas = sorted(EXTERNOS.joinpath("eceg_2010").glob("ECEG_*_2010"))
    if len(carpetas) != 32:
        raise FileNotFoundError(f"Se esperaban 32 carpetas ECEG 2010; hay {len(carpetas)}")

    partes = []
    for carpeta in carpetas:
        ruta = buscar_archivo(carpeta / "conjunto_de_datos", "secciones")
        df = leer_csv(ruta)
        df.columns = [c.strip().upper() for c in df.columns]
        df = df.drop_duplicates()

        faltantes = set(COLUMNAS_DATOS) - set(df.columns)
        if faltantes:
            raise KeyError(f"Faltan columnas en {ruta.name}: {sorted(faltantes)}")
        extra = [c for c in COLUMNAS_EXTRA if c in df.columns]

        df["CLAVEGEO"] = df["CLAVEGEO"].astype(str).str.replace(r"\D", "", regex=True)
        if df["CLAVEGEO"].str.len().ne(13).any():
            raise ValueError(f"{ruta.name}: hay CLAVEGEO que no tienen 13 dígitos")
        if df["CLAVEGEO"].duplicated().any():
            raise ValueError(f"{ruta.name}: CLAVEGEO duplicado después de quitar filas idénticas")

        df["EDOCVE"] = df["CLAVEGEO"].str[:2].astype(int)
        df["MPIOCVE"] = df["CLAVEGEO"].str[5:8].astype(int)
        entidad = df["ENTIDAD"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(2)
        if entidad.ne(df["CLAVEGEO"].str[:2]).any():
            raise ValueError(f"{ruta.name}: la entidad del CLAVEGEO no coincide con ENTIDAD")

        for columna in COLUMNAS_DATOS + extra:
            df[columna] = a_numero(df[columna])
        partes.append(df[LLAVE + COLUMNAS_DATOS + extra])

    resultado = pd.concat(partes, ignore_index=True)
    chiapaneco = resultado["EDOCVE"] == 7
    resultado.loc[chiapaneco, "GRAPROES"] = resultado.loc[chiapaneco, "GRAPROES"] / 100
    resultado.loc[resultado["GRAPROES"] > 30, "GRAPROES"] = np.nan
    return resultado


def leer_eceg2020() -> pd.DataFrame:
    """Lee la base nacional de secciones de 2020."""
    ruta = EXTERNOS / "eceg_2020" / "conjunto_de_datos" / "INE_SECCION_2020.csv"
    df = leer_csv(ruta)
    df.columns = [c.strip().upper() for c in df.columns]

    faltantes = set(COLUMNAS_DATOS + COLUMNAS_EXTRA) - set(df.columns)
    if faltantes:
        raise KeyError(f"Faltan columnas en {ruta.name}: {sorted(faltantes)}")
    if df.duplicated(["ENTIDAD", "MUNICIPIO", "SECCION"]).any():
        raise ValueError(f"{ruta.name}: llave ENTIDAD+MUNICIPIO+SECCION duplicada")

    df["EDOCVE"] = df["ENTIDAD"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(2).astype(int)
    df["MPIOCVE"] = df["MUNICIPIO"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(3).astype(int)

    for columna in COLUMNAS_DATOS + COLUMNAS_EXTRA:
        df[columna] = a_numero(df[columna])
    return df[LLAVE + COLUMNAS_DATOS + COLUMNAS_EXTRA]


def agregar_municipio(df: pd.DataFrame, prefijo: str, denominador: str) -> pd.DataFrame:
    """Agrega las secciones a municipio y calcula el set curado de features.

    `denominador` es el universo de las variables VPH_*: VIVPAR_HAB en 2010 y
    VIVPARH_CV en 2020.
    """
    if denominador not in df.columns:
        raise KeyError(f"Falta el denominador de vivienda {denominador}")
    df = df.copy()
    # Productos para promedios ponderados; el denominador excluye los NaN del valor.
    df["_w_graph"] = df["GRAPROES"] * df["P_15YMAS"]
    df["_w_graph_den"] = df["P_15YMAS"].where(df["GRAPROES"].notna())
    df["_w_ocup"] = df["PROM_OCUP"] * df["VIVPAR_HAB"]
    df["_w_ocup_den"] = df["VIVPAR_HAB"].where(df["PROM_OCUP"].notna())

    columnas = list(dict.fromkeys(
        [c for c in COLUMNAS_SUMA + [denominador] if c in df.columns]
        + ["_w_graph", "_w_graph_den", "_w_ocup", "_w_ocup_den"]
    ))
    sumas = df.groupby(LLAVE, sort=False)[columnas].sum()

    def tasa(numerador: str, den: str) -> pd.Series:
        return (sumas[numerador] / sumas[den]).where(sumas[den] > 0)

    salida = pd.DataFrame(index=sumas.index)
    salida[f"{prefijo}pct_analfabeta"] = tasa("P15YM_AN", "P_15YMAS")
    salida[f"{prefijo}pct_sin_escolaridad"] = tasa("P15YM_SE", "P_15YMAS")
    salida[f"{prefijo}escolaridad_promedio"] = (
        sumas["_w_graph"] / sumas["_w_graph_den"]
    ).where(sumas["_w_graph_den"] > 0)
    salida[f"{prefijo}pct_primaria_incompleta"] = tasa("P15PRI_IN", "P_15YMAS")
    salida[f"{prefijo}pct_secundaria_incompleta"] = tasa("P15SEC_IN", "P_15YMAS")
    salida[f"{prefijo}pct_posbasica"] = tasa("P18YM_PB", "P_18YMAS")
    salida[f"{prefijo}tasa_participacion"] = tasa("PEA", "P_12YMAS")
    salida[f"{prefijo}tasa_desocupacion"] = tasa("PDESOCUP", "PEA")
    salida[f"{prefijo}tasa_participacion_femenina"] = tasa("PEA_F", "P_12YMAS_F")
    salida[f"{prefijo}tasa_ocupacion"] = tasa("POCUPADA", "PEA")
    salida[f"{prefijo}pct_sin_electricidad"] = tasa("VPH_S_ELEC", denominador)
    salida[f"{prefijo}pct_sin_agua_entubada"] = tasa("VPH_AGUAFV", denominador)
    salida[f"{prefijo}pct_sin_drenaje"] = tasa("VPH_NODREN", denominador)
    salida[f"{prefijo}pct_piso_tierra"] = tasa("VPH_PISOTI", denominador)
    salida[f"{prefijo}pct_con_internet"] = tasa("VPH_INTER", denominador)
    salida[f"{prefijo}pct_con_computadora"] = tasa("VPH_PC", denominador)
    salida[f"{prefijo}pct_con_celular"] = tasa("VPH_CEL", denominador)
    salida[f"{prefijo}pct_con_refrigerador"] = tasa("VPH_REFRI", denominador)
    salida[f"{prefijo}pct_con_automovil"] = tasa("VPH_AUTOM", denominador)
    salida[f"{prefijo}promedio_ocupantes"] = (
        sumas["_w_ocup"] / sumas["_w_ocup_den"]
    ).where(sumas["_w_ocup_den"] > 0)
    salida[f"{prefijo}pct_limitacion_visual"] = tasa("PCLIM_VIS", "POBTOT")
    salida[f"{prefijo}pct_limitacion_motriz"] = tasa("PCLIM_MOT2", "POBTOT")
    salida[f"{prefijo}pct_lengua_indigena"] = tasa("P3YM_HLI", "P_3YMAS")
    salida[f"{prefijo}pct_nacido_otra_entidad"] = tasa("PNACOE", "POBTOT")
    salida[f"{prefijo}pct_jefatura_femenina"] = tasa("PHOGJEF_F", "POBHOG")
    salida[f"{prefijo}promedio_hogar"] = tasa("POBHOG", "TOTHOG")
    dependencia = sumas["POB0_14"] + sumas["POB65_MAS"]
    salida[f"{prefijo}razon_dependencia"] = (dependencia / sumas["POB15_64"]).where(
        sumas["POB15_64"] > 0
    )
    salida[f"{prefijo}relacion_hombres_mujeres"] = tasa("POBMAS", "POBFEM")

    return salida.reset_index()


def claves(df: pd.DataFrame) -> set:
    return set(map(tuple, df[LLAVE].itertuples(index=False, name=None)))


def construir_agregados() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee los ECEG, agrega a municipio y cachea los dos Parquet intermedios."""
    ext2010 = agregar_municipio(leer_eceg2010(), "eceg2010_", "VIVPAR_HAB")
    ext2020 = agregar_municipio(leer_eceg2020(), "eceg2020_", "VIVPARH_CV")
    SALIDA_EXTERNOS.mkdir(parents=True, exist_ok=True)
    ext2010.to_parquet(SALIDA_EXTERNOS / "eceg_2010_municipio.parquet", index=False)
    ext2020.to_parquet(SALIDA_EXTERNOS / "eceg_2020_municipio.parquet", index=False)
    return ext2010, ext2020


def cargar_agregados() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lee los agregados cacheados; falla con una instrucción si no existen."""
    rutas = {
        "ext2010": SALIDA_EXTERNOS / "eceg_2010_municipio.parquet",
        "ext2020": SALIDA_EXTERNOS / "eceg_2020_municipio.parquet",
    }
    faltan = [ruta for ruta in rutas.values() if not ruta.exists()]
    if faltan:
        raise FileNotFoundError(
            "Faltan los agregados externos. Corre: python scripts/features_externas_municipio.py"
        )
    return pd.read_parquet(rutas["ext2010"]), pd.read_parquet(rutas["ext2020"])


def cargar_o_construir_agregados() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Usa el caché si existe; si no, construye los agregados desde los ECEG."""
    try:
        return cargar_agregados()
    except FileNotFoundError:
        return construir_agregados()


def unir_externos(tabla: pd.DataFrame, ext2010: pd.DataFrame | None = None,
                  ext2020: pd.DataFrame | None = None) -> pd.DataFrame:
    """Une las features externas con la regla de vintage y conserva todas las filas.

    No toca las columnas originales ni las columnas vacías que llena el modelo
    (`conocidos_objetivo`, `abstencion_objetivo`). El resultado incluye
    `censo_fuente`, las marcas de cobertura y las 28 columnas `ext_*`.
    """
    if "eleccion_objetivo" not in tabla.columns:
        raise KeyError("La tabla no tiene eleccion_objetivo")
    if ext2010 is None or ext2020 is None:
        ext2010, ext2020 = cargar_o_construir_agregados()

    salida = tabla.copy()
    if salida["eleccion_objetivo"].isna().any():
        raise ValueError("Hay filas sin eleccion_objetivo")

    salida["censo_fuente"] = np.where(
        salida["eleccion_objetivo"] <= 2018, 2010, 2020
    ).astype(int)
    salida["_orden"] = salida.index
    claves10, claves20 = claves(ext2010), claves(ext2020)
    llaves = list(map(tuple, salida[LLAVE].itertuples(index=False, name=None)))
    salida["tiene_eceg_2010"] = [int(k in claves10) for k in llaves]
    salida["tiene_eceg_2020"] = [int(k in claves20) for k in llaves]

    renombres = {f"eceg2010_{f}": f"ext_{f}" for f in FEATURES}
    renombres.update({f"eceg2020_{f}": f"ext_{f}" for f in FEATURES})
    fuentes = {
        2010: ext2010.rename(columns=renombres),
        2020: ext2020.rename(columns=renombres),
    }

    partes = []
    for anio, fuente in fuentes.items():
        sub = salida[salida["censo_fuente"] == anio].copy()
        partes.append(sub.merge(fuente, on=LLAVE, how="left", validate="many_to_one"))
    unida = pd.concat(partes).sort_values("_orden").set_index("_orden")
    unida.index.name = tabla.index.name
    return unida


def validar_externos(original: pd.DataFrame, salida: pd.DataFrame) -> list[str]:
    """Comprueba que la unión no cambió filas, llaves ni las columnas vacías."""
    if len(salida) != len(original):
        raise AssertionError(f"Se perdieron filas: {len(original)} -> {len(salida)}")
    if not salida.index.equals(original.index):
        raise AssertionError("El índice de la tabla cambió de orden")
    if salida.columns.duplicated().any():
        raise AssertionError(f"Columnas duplicadas: {salida.columns[salida.columns.duplicated()].tolist()}")

    pd.testing.assert_frame_equal(
        salida[list(original.columns)], original, check_dtype=False
    )
    for columna in ("conocidos_objetivo", "abstencion_objetivo"):
        if columna in original.columns:
            if salida[columna].isna().sum() != original[columna].isna().sum():
                raise AssertionError(f"Cambió el número de nulos en {columna}")

    if not salida["censo_fuente"].isin([2010, 2020]).all():
        raise AssertionError("censo_fuente solo puede ser 2010 o 2020")
    esperado = np.where(original["eleccion_objetivo"] <= 2018, 2010, 2020)
    if not np.array_equal(salida["censo_fuente"].to_numpy(), esperado):
        raise AssertionError("censo_fuente no sigue la regla de vintage")
    posteriores = salida["censo_fuente"] >= salida["eleccion_objetivo"]
    if posteriores.any():
        raise AssertionError(f"Hay censos posteriores a la elección en {posteriores.sum()} filas")
    for columna in ("tiene_eceg_2010", "tiene_eceg_2020"):
        if not salida[columna].isin([0, 1]).all():
            raise AssertionError(f"{columna} solo puede ser 0 o 1")

    faltantes = [f"ext_{f}" for f in FEATURES if f"ext_{f}" not in salida.columns]
    if faltantes:
        raise AssertionError(f"Faltan features en la salida: {faltantes}")

    avisos = []
    for feature in FEATURES_TASA:
        serie = salida[f"ext_{feature}"].dropna()
        if serie.empty:
            avisos.append(f"{feature}: toda nula")
            continue
        if serie.lt(-1e-9).any() or serie.gt(1 + 1e-9).any():
            avisos.append(
                f"{feature}: fuera de [0, 1] (min={serie.min():.6f}, max={serie.max():.6f})"
            )
    return avisos
