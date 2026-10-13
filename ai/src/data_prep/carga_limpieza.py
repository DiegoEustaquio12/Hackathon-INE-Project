#!/usr/bin/env python3
"""Fase 1: carga y limpieza del CCPC con DuckDB.

Lee los CSV de data/raw/ConteosCensalesAAAA/, los unifica en una sola tabla,
agrega marcas de calidad (NO borra filas) y la guarda en data/interim/ccpc_unificado.parquet.
También escribe docs/reports/reporte_calidad.md.

Uso (desde cualquier carpeta):
    python ai/src/data_prep/fase1_carga_limpieza.py
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
OUT_PARQUET = ROOT / "data" / "interim" / "ccpc_unificado.parquet"
OUT_REPORT = ROOT / "docs" / "reports" / "reporte_calidad.md"

COLUMNAS = ["AELEC", "FELECCION", "EDOCVE", "EDONOM", "MPIOCVE", "MPIONOM",
            "SECCION", "TIPOSEC", "DEF", "DEL", "SEXO", "EDAD", "LN", "SV", "NV", "NS"]
INTERMEDIAS = (2009, 2015, 2021)

# Tipos explícitos. Con `columns` DuckDB salta la fila de encabezado y NO usa sus nombres:
# así no importa el BOM (caracteres invisibles) que traen los archivos de 2024.
# Los nombres reales ya se verifican en revisar_encabezados().
TIPOS = {"AELEC": "INTEGER", "FELECCION": "VARCHAR", "EDOCVE": "INTEGER", "EDONOM": "VARCHAR",
         "MPIOCVE": "INTEGER", "MPIONOM": "VARCHAR", "SECCION": "INTEGER", "TIPOSEC": "VARCHAR",
         "DEF": "VARCHAR", "DEL": "VARCHAR", "SEXO": "INTEGER", "EDAD": "INTEGER",
         "LN": "INTEGER", "SV": "INTEGER", "NV": "INTEGER", "NS": "INTEGER"}
assert list(TIPOS) == COLUMNAS
COLUMNAS_SQL = "{" + ", ".join(f"'{c}': '{t}'" for c, t in TIPOS.items()) + "}"

# DEF y DEL se leen como texto porque traen espacios en blanco; FELECCION no se usa
# (el formato de fecha cambia entre años, para la elección se usa AELEC).
SELECT_ARCHIVO = """
SELECT
    CAST(AELEC AS SMALLINT)                                  AS anio,
    CASE WHEN AELEC IN {intermedias} THEN 'intermedia' ELSE 'presidencial' END AS tipo_eleccion,
    CAST(EDOCVE AS SMALLINT)                                 AS edo_cve,
    TRIM(EDONOM)                                             AS edo_nom,
    CAST(MPIOCVE AS SMALLINT)                                AS mpio_cve,
    TRIM(MPIONOM)                                            AS mpio_nom,
    CAST(SECCION AS INTEGER)                                 AS seccion,
    printf('%02d-%04d', EDOCVE, SECCION)                     AS seccion_id,
    UPPER(TRIM(TIPOSEC))                                     AS tipo_sec,
    NULLIF(TRIM("DEF"), '')                                  AS dto_federal,
    NULLIF(TRIM("DEL"), '')                                  AS dto_local,
    CAST(SEXO AS SMALLINT)                                   AS sexo,
    CAST(EDAD AS SMALLINT)                                   AS edad,
    CASE WHEN EDAD < 18 THEN 'menor_18'
         WHEN EDAD <= 24 THEN '18-24'
         WHEN EDAD <= 34 THEN '25-34'
         WHEN EDAD <= 44 THEN '35-44'
         WHEN EDAD <= 59 THEN '45-59'
         ELSE '60+' END                                      AS etapa_vida,
    CAST(LN AS INTEGER) AS ln, CAST(SV AS INTEGER) AS sv,
    CAST(NV AS INTEGER) AS nv, CAST(NS AS INTEGER) AS ns,
    -- Marcas de calidad: las filas raras se marcan, no se borran
    (LN <> SV + NV + NS)                                     AS flag_regla_ln,
    (LN < 0 OR SV < 0 OR NV < 0 OR NS < 0)                   AS flag_negativo,
    (EDAD > 90)                                              AS flag_edad_alta,
    (NULLIF(TRIM("DEF"), '') IS NULL)                        AS flag_dto_federal_vacio,
    (NULLIF(TRIM("DEL"), '') IS NULL)                        AS flag_dto_local_vacio,
    '{nombre}'                                               AS archivo
FROM read_csv('{ruta}', header = true, delim = ',', quote = '"', escape = '"',
              encoding = 'utf-8', columns = {columnas})
"""


def sql_archivo(ruta: Path) -> str:
    esc = lambda t: str(t).replace("'", "''")
    return SELECT_ARCHIVO.format(intermedias=INTERMEDIAS, columnas=COLUMNAS_SQL,
                                 ruta=esc(ruta.as_posix()), nombre=esc(ruta.name))


def cargar_archivos(con):
    """Lee los CSV uno por uno (cada uno con su propia lectura) y verifica que no se pierda
    ninguna fila: filas cargadas == líneas de datos del archivo.
    Se hace así porque leer todo con un glob puede descartar archivos sin avisar."""
    archivos = sorted(RAW.glob("ConteosCensales*/*.csv"))
    revision, primero = [], True
    for i, a in enumerate(archivos, 1):
        if primero:
            con.execute(f"CREATE OR REPLACE TABLE ccpc AS {sql_archivo(a)}")
            primero = False
        else:
            con.execute(f"INSERT INTO ccpc {sql_archivo(a)}")
        cargadas = con.execute("SELECT count(*) FROM ccpc WHERE archivo = ?", [a.name]).fetchone()[0]
        with open(a, "rb") as f:
            lineas = sum(1 for linea in f if linea.strip()) - 1  # menos el encabezado
        revision.append((a.name, lineas, cargadas))
        marca = "" if lineas == cargadas else "   <-- NO COINCIDE"
        print(f"[{i}/{len(archivos)}] {a.name}: {cargadas:,} filas{marca}")
    return revision


def revisar_encabezados(con):
    """Los 16 nombres de columna deben ser los esperados en todos los archivos."""
    archivos = sorted(RAW.glob("ConteosCensales*/*.csv"))
    if not archivos:
        raise SystemExit(f"No hay CSV en {RAW}. Corre scripts/download_raw_data.py primero.")
    malos = []
    for a in archivos:
        with open(a, encoding="utf-8-sig") as f:
            if f.readline().strip().split(",") != COLUMNAS:
                malos.append(a.name)
    return len(archivos), malos


def md(df):
    """DataFrame -> tabla markdown (sin depender de tabulate)."""
    cols = list(df.columns)
    filas = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        celdas = []
        for c, v in zip(cols, r):
            if c == "anio":
                celdas.append(str(v))
            elif isinstance(v, float) and not v.is_integer():
                celdas.append(f"{v:,.2f}")
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                celdas.append(f"{int(v):,}")
            else:
                celdas.append(str(v))
        filas.append("| " + " | ".join(celdas) + " |")
    return "\n".join(filas)


def main():
    con = duckdb.connect()
    n_archivos, malos = revisar_encabezados(con)
    print(f"{n_archivos} archivos CSV; encabezados distintos a los esperados: {malos or 'ninguno'}")

    revision = cargar_archivos(con)
    desajustes = [r for r in revision if r[1] != r[2]]
    if desajustes:
        raise SystemExit(f"Filas perdidas al cargar (archivo, líneas, cargadas): {desajustes}")
    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY ccpc TO '{OUT_PARQUET.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    print(f"Guardado: {OUT_PARQUET}")

    # --- Resúmenes: aquí sí se pasa a pandas, porque son tablas chicas ---
    por_anio = con.execute("""
        SELECT anio, tipo_eleccion AS tipo, count(DISTINCT archivo) AS archivos, count(*) AS filas,
               count(DISTINCT seccion_id) AS secciones,
               sum(ln)::BIGINT AS ln, sum(sv)::BIGINT AS sv, sum(nv)::BIGINT AS nv, sum(ns)::BIGINT AS ns,
               round(100.0 * sum(sv) / sum(sv + nv), 2) AS participacion_pct,
               round(100.0 * sum(ns) / sum(ln), 2)      AS ns_pct_de_ln
        FROM ccpc GROUP BY ALL ORDER BY anio""").df()

    calidad = con.execute("""
        SELECT anio,
               sum(flag_regla_ln::INT)::BIGINT   AS falla_regla_ln,
               sum(flag_negativo::INT)::BIGINT           AS negativos,
               sum(flag_edad_alta::INT)::BIGINT          AS filas_edad_mayor_90,
               max(edad)                         AS edad_maxima,
               sum(flag_dto_federal_vacio::INT)::BIGINT  AS dto_federal_vacio,
               sum(flag_dto_local_vacio::INT)::BIGINT    AS dto_local_vacio,
               sum((sexo NOT IN (0, 1))::INT)::BIGINT AS sexo_no_0_ni_1
        FROM ccpc GROUP BY anio ORDER BY anio""").df()

    duplicados = con.execute("""
        SELECT anio, count(*) AS grupos_duplicados FROM (
            SELECT anio FROM ccpc GROUP BY anio, edo_cve, seccion, sexo, edad HAVING count(*) > 1
        ) GROUP BY anio ORDER BY anio""").df()

    sin_dato = con.execute("""
        SELECT anio, count(*) AS secciones_sin_dato FROM (
            SELECT anio, seccion_id FROM ccpc GROUP BY anio, seccion_id HAVING sum(sv + nv) = 0
        ) GROUP BY anio ORDER BY anio""").df()

    ns_estado = con.execute("""
        SELECT anio, edo_nom AS estado, round(100.0 * sum(ns) / sum(ln), 2) AS ns_pct_de_ln
        FROM ccpc GROUP BY anio, edo_nom
        QUALIFY row_number() OVER (PARTITION BY anio ORDER BY sum(ns) / sum(ln) DESC) = 1
        ORDER BY anio""").df()

    tipo_sec = con.execute("""
        SELECT anio, tipo_sec, count(*) AS filas FROM ccpc GROUP BY ALL ORDER BY anio, tipo_sec""").df()

    print(por_anio.to_string(index=False))

    reporte = f"""# Reporte de calidad (Fase 1)

Generado por `ai/src/data_prep/fase1_carga_limpieza.py`. Las cifras son las de esta corrida.

- Archivos CSV leídos: **{n_archivos}** (se esperan 192: 32 estados por 6 elecciones)
- Archivos con encabezados distintos a los 16 esperados: **{', '.join(malos) if malos else 'ninguno'}**

## Totales por elección
{md(por_anio)}

Participación = SV / (SV + NV). `ns_pct_de_ln` = NS / LN. Para cada estado y año se espera 1 archivo por estado (32 por año).

## Marcas de calidad (las filas se marcan, no se borran)
{md(calidad)}

## Grupos duplicados (año + estado + sección + sexo + edad)
{md(duplicados) if len(duplicados) else 'Ninguno.'}

## Secciones sin dato (SV + NV = 0): su participación es vacía, no cero
{md(sin_dato) if len(sin_dato) else 'Ninguna.'}

## Estado con más no especificados por año
{md(ns_estado)}

## Filas por tipo de sección
{md(tipo_sec)}
"""
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(reporte, encoding="utf-8")
    print(f"Reporte: {OUT_REPORT}")


if __name__ == "__main__":
    main()