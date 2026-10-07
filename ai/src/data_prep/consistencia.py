"""Fase 2 del plan: consistencia entre años.

Compara secciones a través de las 6 elecciones (2009-2024), las clasifica
por historial, detecta cambios de territorio entre años consecutivos, mide
el efecto de la exclusión de cuadernillos en 2012 y verifica totales contra
las referencias de Fase 1.
"""
from pathlib import Path
import sys

import pandas as pd
import numpy as np

RAIZ = Path(__file__).resolve().parents[3]
INTERIM = RAIZ / "data" / "interim" / "ccpc_limpio"
HISTORIAL_OUT = RAIZ / "data" / "interim" / "historial_secciones.parquet"
REPORTE_OUT = RAIZ / "docs" / "reports" / "reporte_consistencia.md"

ANIOS = (2009, 2012, 2015, 2018, 2021, 2024)

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


def leer_un_anio(anio: int) -> pd.DataFrame:
    ruta = INTERIM / f"AELEC={anio}" / "part-0.parquet"
    df = pd.read_parquet(ruta)
    grp = df.groupby(["EDOCVE", "SECCION"], as_index=False)
    res = grp.agg(
        EDONOM=("EDONOM", "first"),
        MPIOCVE=("MPIOCVE", "first"),
        MPIONOM=("MPIONOM", "first"),
        TIPOSEC=("TIPOSEC", "first"),
        DEF=("DEF", "first"),
        DEL=("DEL", "first"),
        LN=("LN", "sum"),
        SV=("SV", "sum"),
        NV=("NV", "sum"),
        NS=("NS", "sum"),
        filas=("LN", "count"),
        filas_marcadas=("flag_revision", "sum"),
        filas_regla_ln=("flag_regla_ln", "sum"),
        filas_negativo=("flag_negativo", "sum"),
        filas_duplicado=("flag_duplicado", "sum"),
        filas_edad=("flag_edad", "sum"),
        filas_codigo=("flag_codigo", "sum"),
        filas_llave=("flag_llave", "sum"),
    )
    # Validar nunique <= 1
    for c in ("MPIOCVE", "TIPOSEC", "DEF", "DEL"):
        g2 = df.groupby(["EDOCVE", "SECCION"], as_index=False)[c].nunique()
        if g2[c].max() > 1:
            raise ValueError(f"{anio}: {c} no único por (estado,sección)")
    res["anio_eleccion"] = anio
    return res


def clasificar(secciones_df: pd.DataFrame) -> pd.DataFrame:
    pres = secciones_df.pivot(index=["EDOCVE", "SECCION"], columns="anio_eleccion", values="LN")
    pres = pres.notna() & (pres.fillna(0) >= 0)
    pres = pres.reindex(columns=ANIOS).fillna(False)

    out = pres.reset_index()
    for a in ANIOS:
        out[f"presente_{a}"] = pres[a].values

    def primer_ultimo(row):
        p = [a for a in ANIOS if row[f"presente_{a}"]]
        if not p:
            return pd.Series([np.nan, np.nan, 0])
        return pd.Series([p[0], p[-1], len(p)])

    out[["primera_eleccion", "ultima_eleccion", "n_anios_presente"]] = out.apply(primer_ultimo, axis=1)

    def clasif(row):
        n = int(row["n_anios_presente"])
        if n == 0:
            return "sin_dato"
        if n == 6:
            return "historial_completo"
        p = row["primera_eleccion"]
        u = row["ultima_eleccion"]
        if p > 2009:
            return "nueva"
        if u < 2024:
            return "desaparecida"
        if p == 2009 and u == 2024 and n < 6:
            return "con_huecos"
        if p == 2024:
            return "nueva"
        return "otro"

    out["clasificacion"] = out.apply(clasif, axis=1)
    out["es_nueva_2024"] = (out["clasificacion"] == "nueva") & (out["primera_eleccion"] == 2024)
    out = out[["EDOCVE", "SECCION", "primera_eleccion", "ultima_eleccion", "n_anios_presente",
               "clasificacion", "es_nueva_2024"] + [f"presente_{a}" for a in ANIOS]]
    return out

def cambios(secciones_df: pd.DataFrame, hist: pd.DataFrame) -> pd.DataFrame:
    # Pivot por campo y año
    def pivot_campo(campo):
        p = secciones_df.pivot(index=["EDOCVE", "SECCION"], columns="anio_eleccion", values=campo)
        return p.reindex(columns=ANIOS)

    piv_mun = pivot_campo("MPIOCVE")
    piv_tip = pivot_campo("TIPOSEC")
    piv_def = pivot_campo("DEF")
    piv_del = pivot_campo("DEL")

    res = pd.DataFrame(index=piv_mun.index)
    res["cambio_municipio"] = False
    res["anio_cambio_municipio"] = pd.NA
    res["cambio_tipo"] = False
    res["anio_cambio_tipo"] = pd.NA
    res["cambio_distrito_federal"] = False
    res["anio_cambio_distrito_federal"] = pd.NA
    res["cambio_distrito_local"] = False
    res["anio_cambio_distrito_local"] = pd.NA

    pairs = [(2009, 2012), (2012, 2015), (2015, 2018), (2018, 2021), (2021, 2024)]
    for a, b in pairs:
        for campo, outflag, outanio in [
            ("MPIOCVE", "cambio_municipio", "anio_cambio_municipio"),
            ("TIPOSEC", "cambio_tipo", "anio_cambio_tipo"),
            ("DEF", "cambio_distrito_federal", "anio_cambio_distrito_federal"),
            ("DEL", "cambio_distrito_local", "anio_cambio_distrito_local"),
        ]:
            if campo == "MPIOCVE":
                p = piv_mun
            elif campo == "TIPOSEC":
                p = piv_tip
            elif campo == "DEF":
                p = piv_def
            else:
                p = piv_del
            mask = p[a].notna() & p[b].notna() & (p[a] != p[b])
            idx = mask[mask].index
            if len(idx) == 0:
                continue
            res.loc[idx, outflag] = True
            # solo marcar si aún no hay año (primer cambio)
            res.loc[idx, outanio] = res.loc[idx, outanio].fillna(b)
    res = res.reset_index()
    return res

def _pct(x: float) -> str:
    return f"{x:.1%}"


def redactar_reporte(df_all: pd.DataFrame, hist: pd.DataFrame, cam: pd.DataFrame, anios: tuple[int, ...]) -> str:
    resumen_filas = []
    for a in anios:
        sub = df_all[df_all["anio_eleccion"] == a]
        ln = int(sub["LN"].sum())
        sv = int(sub["SV"].sum())
        nv = int(sub["NV"].sum())
        ns = int(sub["NS"].sum())
        part = sv / (sv + nv) if (sv + nv) > 0 else 0
        part_ref = PARTICIPACION_REFERENCIA[a]
        ln_ref = LISTA_REFERENCIA[a]
        secc_ref = SECCIONES_REFERENCIA[a]
        secc_obs = int(sub[["EDOCVE", "SECCION"]].drop_duplicates().shape[0])
        resumen_filas.append([
            a, _pct(part), _pct(part_ref), f"{ln - ln_ref:+,}",
            _pct(ns / ln if ln > 0 else 0), secc_obs, secc_ref,
        ])
    resumen_tab = "\n".join(
        "| " + " | ".join(map(str, f)) + " |"
        for f in [
            ["Año", "Part. obs.", "Part. ref.", "Δ LN", "NS/LN", "Secciones", "Secciones ref."],
            ["---"] * 7,
        ] + resumen_filas
    )

    # clasificacion
    c = hist["clasificacion"].value_counts()
    clas_tab = "\n".join(
        "| " + " | ".join(map(str, f)) + " |"
        for f in [
            ["Clasificación", "Secciones"], ["---"] * 2,
        ] + sorted(c.items(), key=lambda x: x[0])
    )
    nuevas24 = int(hist["es_nueva_2024"].sum())

    # cambios
    cambios_sum = {
        "municipio": int(cam["cambio_municipio"].sum()),
        "tipo": int(cam["cambio_tipo"].sum()),
        "def": int(cam["cambio_distrito_federal"].sum()),
        "del": int(cam["cambio_distrito_local"].sum()),
    }
    cam_tab = "\n".join(
        "| " + " | ".join(map(str, f)) + " |"
        for f in [
            ["Cambio", "Secciones afectadas"], ["---"] * 2,
        ] + list(cambios_sum.items())
    )

    # 2012 effect
    efecto = []
    for a in anios:
        sub = df_all[df_all["anio_eleccion"] == a]
        ln = sub["LN"].sum()
        sv = sub["SV"].sum()
        nv = sub["NV"].sum()
        ns = sub["NS"].sum()
        efecto.append([
            a, int(ln), int(ns), f"{ns/ln:.2%}" if ln > 0 else "0.0%",
            f"{sv/(sv+nv):.2%}" if (sv+nv) > 0 else "N/A",
            f"{sv/(sv+nv+ns):.2%}" if (sv+nv+ns) > 0 else "N/A",
            int(((sub["SV"] + sub["NV"]) == 0).sum()),
        ])
    ef_tab = "\n".join(
        "| " + " | ".join(map(str, f)) + " |"
        for f in [
            ["Año", "LN", "NS", "NS/LN", "SV/(SV+NV)", "SV/(SV+NV+NS)", "Secciones SV+NV==0"],
            ["---"] * 7,
        ] + efecto
    )

    regla_ok = (df_all["filas_regla_ln"].sum() == 0)
    secciones_ok = all(len(df_all[df_all["anio_eleccion"] == a][["EDOCVE", "SECCION"]].drop_duplicates()) == SECCIONES_REFERENCIA[a] for a in anios)
    ln_ok = all(df_all[df_all["anio_eleccion"] == a]["LN"].sum() == LISTA_REFERENCIA[a] for a in anios)

    criterios = "\n".join([
        "- [" + ("x" if regla_ok else " ") + "] Ninguna fila falla LN = SV+NV+NS (a nivel agregado por sección)",
        "- [" + ("x" if secciones_ok else " ") + "] Secciones por año coinciden con las referencias",
        "- [" + ("x" if ln_ok else " ") + "] Lista nominal por año coinciden con las referencias",
        "- [x] Clasificación de historial construida (con huecos, nuevas y desaparecidas)",
        "- [x] Cambios de territorio detectados entre años consecutivos",
        "- [x] Se reporta efecto de NS y secciones sin dato",
    ])

    texto = f"""# Reporte de consistencia entre años — Fase 2

Generado por `python -m ai.src.data_prep.consistencia`.

## 1. Conciliación de totales

| Año | Part. obs. | Part. ref. | Δ LN | NS/LN | Secciones | Secciones ref. |
|---|---|---|---|---|---|---|
{resumen_tab.splitlines()[2]}

## 2. Clasificación de secciones por historial (llave (EDOCVE, SECCION))

| Clasificación | Secciones |
|---|---|
{clas_tab.splitlines()[2] if len(clas_tab.splitlines()) > 2 else clas_tab.splitlines()[-1]}

- Nuevas en 2024 (primer año == 2024): {nuevas24:,} (≊ 2,775 según reto)

## 3. Cambios de territorio entre años consecutivos

| Cambio | Secciones afectadas |
|---|---|
{cam_tab.splitlines()[2]}

Los cambios de distrito en 2024 son esperados por redistritación de 2023; los cambios de municipio/tipo entre años son los relevantes.

## 4. Efecto de NS (exclusión de cuadernillos en 2012)

| Año | LN | NS | NS/LN | SV/(SV+NV) | SV/(SV+NV+NS) | Secciones SV+NV==0 |
|---|---|---|---|---|---|---|
{ef_tab.splitlines()[2]}

Nota: `SV+NV` se usan para participación oficial (INE); en 2012 NS/LN es el más bajo (≊ 0.2%). Secciones con `SV+NV==0` tienen participación nula (NULL) en la tabla de análisis.

## 5. Criterio de salida de la fase

{criterios}

## 6. Salidas

- `data/interim/historial_secciones.parquet` — una fila por (EDOCVE, SECCION) con clasificación, presencias y cambios.
- `data/processed/tabla_analisis.parquet` y su desglose se generan en Fase 3, que deberá reconciliar totales con este reporte.
"""
    return texto

def procesar():
    df_all = []
    for a in ANIOS:
        df_all.append(leer_un_anio(a))
    df_all = pd.concat(df_all, ignore_index=True)

    hist = clasificar(df_all)
    cam = cambios(df_all, hist)

    hist_c = hist.merge(cam, on=["EDOCVE", "SECCION"], how="left")

    HISTORIAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    hist_c.to_parquet(HISTORIAL_OUT, index=False, compression="zstd")

    REPORTE_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORTE_OUT.write_text(redactar_reporte(df_all, hist, cam, ANIOS), encoding="utf-8")
    return df_all, hist_c


def main(argv=None):
    procesar()
    print(f"Historial: {HISTORIAL_OUT}")
    print(f"Reporte:   {REPORTE_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
