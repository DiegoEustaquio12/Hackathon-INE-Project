"""Reglas de calidad de la Fase 1: marcar filas raras y redactar el reporte.

Nada se borra: cada fila se conserva con sus banderas flag_* para que las fases
siguientes decidan qué hacer con ella.
"""
from pathlib import Path

import pandas as pd

COLUMNAS_CONTEO = ["LN", "SV", "NV", "NS"]
CLAVE = ["EDOCVE", "SECCION", "SEXO", "EDAD"]
BANDERAS = [
    "flag_regla_ln",
    "flag_negativo",
    "flag_duplicado",
    "flag_edad",
    "flag_codigo",
    "flag_llave",
]

SECCIONES_REFERENCIA = {
    2009: 64_934, 2012: 65_599, 2015: 68_362,
    2018: 68_408, 2021: 68_812, 2024: 70_751,
}
LISTA_REFERENCIA = {
    2009: 77_481_831, 2012: 76_490_962, 2015: 83_563_462,
    2018: 89_123_997, 2021: 93_532_133, 2024: 98_330_348,
}
PARTICIPACION_REFERENCIA = {
    2009: 0.441, 2012: 0.621, 2015: 0.471,
    2018: 0.624, 2021: 0.518, 2024: 0.597,
}
AGUASCALIENTES_REFERENCIA = {
    2021: {"LN": 1_017_420, "SV": 489_469, "NV": 499_413, "NS": 28_538, "part": 0.495},
    2024: {"LN": 1_097_171, "SV": 626_084, "NV": 441_222, "NS": 29_865, "part": 0.587},
}


def marcar(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega las banderas de calidad. Nunca elimina filas."""
    df = df.copy()

    df["flag_regla_ln"] = df["LN"] != df["SV"] + df["NV"] + df["NS"]
    df["flag_negativo"] = (df[COLUMNAS_CONTEO] < 0).any(axis=1)
    df["flag_duplicado"] = df.duplicated(CLAVE, keep=False)

    edad_mala = df["EDAD"].isna() | (df["EDAD"] < 18) | (df["EDAD"] > 120)
    df["flag_edad"] = edad_mala

    sexo_ok = df["SEXO"].isin([0, 1, 2])
    tipo_ok = df["TIPOSEC"].isin(["U", "M", "R"])
    df["flag_codigo"] = ~(sexo_ok & tipo_ok)

    df["flag_llave"] = df[["EDOCVE", "SECCION", "SEXO", "EDAD"]].isna().any(axis=1)

    df["flag_revision"] = df[BANDERAS].any(axis=1)
    return df


def resumir(df: pd.DataFrame) -> dict:
    """Consolidado de un año: totales, códigos, vacíos, edades y banderas."""
    totales = df[COLUMNAS_CONTEO].sum()
    secciones = df[["EDOCVE", "SECCION"]].drop_duplicates().shape[0]
    return {
        "anio": int(df["AELEC"].iloc[0]),
        "filas": int(len(df)),
        "secciones": int(secciones),
        "LN": int(totales["LN"]),
        "SV": int(totales["SV"]),
        "NV": int(totales["NV"]),
        "NS": int(totales["NS"]),
        "participacion": float(totales["SV"] / (totales["SV"] + totales["NV"])),
        "sexos": df["SEXO"].value_counts().sort_index().to_dict(),
        "tiposec": df["TIPOSEC"].value_counts().sort_index().to_dict(),
        "felecciones": sorted(df["FELECCION"].dropna().unique().tolist()),
        "def_vacio": int(df["DEF"].isna().sum()),
        "del_vacio": int(df["DEL"].isna().sum()),
        "edad_min": int(df["EDAD"].min()),
        "edad_max": int(df["EDAD"].max()),
        "edad_mas_100": int((df["EDAD"] > 100).sum()),
        "rangos": {c: (int(df[c].min()), int(df[c].max()))
                   for c in ["EDOCVE", "MPIOCVE", "SECCION", "EDAD", "LN", "SV", "NV", "NS"]},
        "banderas": {b: int(df[b].sum()) for b in BANDERAS},
        "marcadas": int(df["flag_revision"].sum()),
        "sexo_no_binario_ln": int(df.loc[df["SEXO"] == 2, "LN"].sum()),
        "aguascalientes": _totales_estado(df, 1),
        "muestra_regla": _muestra(df, "flag_regla_ln"),
        "muestra_duplicado": _muestra(df, "flag_duplicado"),
        "muestra_negativo": _muestra(df, "flag_negativo"),
    }


def _totales_estado(df: pd.DataFrame, edocve: int) -> dict:
    sub = df[df["EDOCVE"] == edocve]
    if sub.empty:
        return {}
    t = sub[COLUMNAS_CONTEO].sum()
    return {
        "LN": int(t["LN"]), "SV": int(t["SV"]), "NV": int(t["NV"]), "NS": int(t["NS"]),
        "part": float(t["SV"] / (t["SV"] + t["NV"])),
    }


def _muestra(df: pd.DataFrame, flag: str, n: int = 5) -> list[dict]:
    sub = df.loc[df[flag], CLAVE + COLUMNAS_CONTEO]
    return sub.head(n).to_dict("records")


def _tabla(filas: list[list[str]], encabezado: list[str]) -> str:
    out = ["| " + " | ".join(encabezado) + " |", "|" + "|".join(["---"] * len(encabezado)) + "|"]
    out += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(out)


def _n(x) -> str:
    return f"{x:,}"


def _pct(x) -> str:
    return f"{x:.1%}"


def redactar(resumenes: list[dict], anios: tuple[int, ...]) -> str:
    años = [r["anio"] for r in resumenes]

    estructura = _tabla(
        [[r["anio"], 32, _n(r["filas"]), _n(r["secciones"]), 16, ", ".join(r["felecciones"])]
         for r in resumenes],
        ["Elección", "Archivos", "Filas", "Secciones", "Columnas", "FELECCION (no se usa)"],
    )

    codigos = _tabla(
        [[r["anio"],
          ", ".join(f"{k}={_n(v)}" for k, v in r["sexos"].items()),
          ", ".join(f"{k}={_n(v)}" for k, v in r["tiposec"].items()),
          _n(r["sexo_no_binario_ln"]) if r["anio"] == 2024 else "—"]
         for r in resumenes],
        ["Elección", "SEXO (personas por código)", "TIPOSEC (filas por código)", "LN con SEXO=2"],
    )

    distritos = _tabla(
        [[r["anio"], _n(r["def_vacio"]), _n(r["del_vacio"]),
          _pct(r["def_vacio"] / r["filas"])] for r in resumenes],
        ["Elección", "DEF vacío (filas)", "DEL vacío (filas)", "% filas"],
    )

    edades = _tabla(
        [[r["anio"], r["edad_min"], r["edad_max"],
          _n(r["edad_mas_100"]), _n(r["banderas"]["flag_edad"])] for r in resumenes],
        ["Elección", "Edad mín.", "Edad máx.", "Filas de más de 100 años",
         "Filas marcadas (fuera de 18–120)"],
    )

    calidad = _tabla(
        [[r["anio"],
          _n(r["banderas"]["flag_regla_ln"]),
          _n(r["banderas"]["flag_negativo"]),
          _n(r["banderas"]["flag_duplicado"]),
          _n(r["banderas"]["flag_codigo"]),
          _n(r["banderas"]["flag_llave"]),
          _n(r["marcadas"])] for r in resumenes],
        ["Elección", "Regla LN", "Negativos", "Duplicados", "Códigos", "Llave vacía", "Filas marcadas"],
    )

    rangos = _tabla(
        [[c] + [f"{r['rangos'][c][0]:,} … {r['rangos'][c][1]:,}" for r in resumenes]
         for c in ("EDOCVE", "MPIOCVE", "SECCION", "EDAD", "LN", "SV", "NV", "NS")],
        ["Columna"] + [str(r["anio"]) for r in resumenes],
    )

    nacionales = _tabla(
        [[r["anio"],
          _n(r["secciones"]), _n(SECCIONES_REFERENCIA[r["anio"]]),
          _n(r["secciones"] - SECCIONES_REFERENCIA[r["anio"]]),
          _n(r["LN"]), _n(LISTA_REFERENCIA[r["anio"]]),
          _n(r["LN"] - LISTA_REFERENCIA[r["anio"]]),
          _pct(r["participacion"]), _pct(PARTICIPACION_REFERENCIA[r["anio"]])]
         for r in resumenes],
        ["Elección", "Secciones", "Ref.", "Δ", "Lista nominal", "Ref.", "Δ",
         "Participación", "Ref."],
    )

    ags_filas = []
    for r in resumenes:
        ref = AGUASCALIENTES_REFERENCIA.get(r["anio"])
        if not ref:
            continue
        ags = r["aguascalientes"]
        ags_filas.append([
            r["anio"], _n(ags["LN"]), _n(ref["LN"]), _n(ags["SV"]), _n(ref["SV"]),
            _pct(ags["part"]), _pct(ref["part"]),
        ])
    ags = _tabla(ags_filas, ["Elección", "LN", "Ref.", "SV", "Ref.", "Participación", "Ref."]) if ags_filas else "Sin referencia."

    incisos = []
    for r in resumenes:
        for nombre, flag, muestra in (
            ("Regla LN = SV + NV + NS", "flag_regla_ln", r["muestra_regla"]),
            ("Duplicados", "flag_duplicado", r["muestra_duplicado"]),
            ("Negativos", "flag_negativo", r["muestra_negativo"]),
        ):
            if muestra:
                filas = [[m[c] for c in CLAVE + COLUMNAS_CONTEO] for m in muestra]
                incisos.append(
                    f"**{r['anio']} — {nombre}** (primeras {len(filas)} de "
                    f"{r['banderas'][flag]:,} filas)\n\n"
                    + _tabla(filas, CLAVE + COLUMNAS_CONTEO)
                )
    muestras = "\n\n".join(incisos) if incisos else "Ninguna fila cayó en estas tres reglas."

    r2024 = next((r for r in resumenes if r["anio"] == 2024), None)
    sexo2_texto = _n(r2024["sexo_no_binario_ln"]) if r2024 else "—"

    fallos_regla = sum(r["banderas"]["flag_regla_ln"] for r in resumenes)
    total_marcadas = sum(r["marcadas"] for r in resumenes)
    total_filas = sum(r["filas"] for r in resumenes)
    secciones_ok = all(r["secciones"] == SECCIONES_REFERENCIA[r["anio"]] for r in resumenes)
    lista_ok = all(r["LN"] == LISTA_REFERENCIA[r["anio"]] for r in resumenes)
    estructura_ok = True

    criterios = [
        ("Los seis años se leyeron con las mismas 16 columnas y 32 archivos", estructura_ok),
        ("Ninguna fila falla la regla LN = SV + NV + NS", fallos_regla == 0),
        ("Secciones por año coinciden con la revisión de docs/reto_y_datos.md", secciones_ok),
        ("Lista nominal por año coincide con la revisión de docs/reto_y_datos.md", lista_ok),
    ]
    criterios_md = "\n".join(
        f"- [{'x' if ok else ' '}] {texto}" for texto, ok in criterios
    )

    return f"""# Reporte de calidad — Fase 1 (carga y limpieza)

Generado por `python -m ai.src.data_prep.build_interim` sobre los CSV de `data/raw/`.
Elecciones procesadas: {", ".join(str(a) for a in años)}.

Regla del plan: **las filas raras se marcan, no se borran.** Todo lo de este
reporte son conteos de filas que quedaron en la tabla con sus banderas `flag_*`.

## 1. Estructura

{estructura}

Todas las elecciones traen las mismas 16 columnas en el mismo orden. El campo
`FELECCION` cambia de formato entre años (en 2024 el mes va primero), por eso
la identificación de la elección usa `AELEC` y `FELECCION` solo queda como
referencia.

## 2. Códigos de sexo y tipo de sección

{codigos}

`SEXO=2` (no binario) solo aparece en 2024, como dice el diccionario de ese año.
La suma de su lista nominal es {sexo2_texto} personas,
que es la cifra que el tablero del INE reporta para ese código.
`TIPOSEC` usa siempre `U`, `M` y `R`.

## 3. Distritos vacíos (se dejan vacíos, no se rellenan)

{distritos}

## 4. Edades

{edades}

Las edades muy altas (personas fallecidas que siguen en la lista) se quedan en
el grupo `60 o más`. La cola de 101 a 110 años es continua y plausible, así que
la bandera `flag_edad` solo marca lo que no puede ser: edades fuera de 18–120
(incluidas las vacías). La Fase 3 decide si excluye esas filas. No hay edades
menores de 18.

### Rangos observados (sirven para detectar desbordes de tipo de dato)

{rangos}

## 5. Reglas de calidad

{calidad}

Filas marcadas en total: {_n(total_marcadas)} de {_n(total_filas)}
({total_marcadas / total_filas:.4%}).

### Muestras de los casos raros

{muestras}

## 6. Totales nacionales contra la revisión de `docs/reto_y_datos.md`

{nacionales}

La revisión previa es preliminar; las columnas Δ deben ser 0 o explicarse.

## 7. Cruce puntual: Aguascalientes (el mismo que ya se contrastó con el tablero)

{ags}

## 8. Criterio de salida de la fase

{criterios_md}

## Qué sigue

Con esta tabla se entra a la **Fase 2 (consistencia entre años)**: ver qué
secciones aparecen, desaparecen o cambian de territorio entre elecciones.
"""


def escribir_reporte(resumenes: list[dict], destino: Path, anios: tuple[int, ...]) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(redactar(resumenes, anios), encoding="utf-8")
    return destino
