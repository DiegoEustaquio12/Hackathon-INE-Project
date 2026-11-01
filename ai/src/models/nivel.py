"""Nivel nacional: historia, backtest y escenarios para la elección objetivo.

El nivel publicado se conserva por compatibilidad con la corrida anterior. La
tendencia y el último cambio se reportan como escenarios, nunca como si fueran
observaciones de 2027.
"""
import numpy as np
import pandas as pd

TIPO = {
    2009: "intermedia",
    2012: "presidencial",
    2015: "intermedia",
    2018: "presidencial",
    2021: "intermedia",
    2024: "presidencial",
    2027: "intermedia",
}
INTERMEDIAS = (2009, 2015, 2021)
PUBLICADO = 2021


def _tendencia(serie, objetivo):
    """Ajuste lineal con los años disponibles; nunca usa el año objetivo."""
    x = np.asarray(serie.index, dtype=float)
    y = np.asarray(serie.to_numpy(), dtype=float)
    if len(x) < 2:
        return float(y[-1])
    coeficientes = np.polyfit(x, y, 1)
    return float(np.polyval(coeficientes, objetivo))


def analizar(nacional, objetivo=2027, publicado=PUBLICADO):
    """Resume nivel observado, backtest y pronósticos alternativos.

    ``nacional`` es una serie indexada por año. El backtest solo usa años
    anteriores al objetivo de cada corte. El nivel publicado no se cambia.
    """
    if not isinstance(nacional, pd.Series) or nacional.empty:
        raise ValueError("El nivel nacional debe ser una serie con datos")
    if publicado not in nacional.index:
        raise ValueError(f"Falta el nivel publicado de {publicado}")
    intermedios = [a for a in INTERMEDIAS if a in nacional.index and a < objetivo]
    if len(intermedios) < 2:
        raise ValueError("Se necesitan al menos dos intermedias anteriores al objetivo")

    serie_inter = nacional.loc[intermedios]
    tendencia = _tendencia(serie_inter, objetivo)
    ultimo = float(serie_inter.iloc[-1])
    cambio = ultimo + (float(serie_inter.iloc[-1]) - float(serie_inter.iloc[-2]))

    filas = []
    # Último valor: el backtest más simple y el que usa la corrida anterior.
    for objetivo_bt, previo in ((2015, 2009), (2021, 2015)):
        if objetivo_bt in nacional.index and previo in nacional.index:
            pred = float(nacional.loc[previo])
            real = float(nacional.loc[objetivo_bt])
            filas.append(dict(
                eleccion=objetivo_bt, tipo=TIPO.get(objetivo_bt, "?"),
                metodo="ultimo", pronostico_pct=pred * 100,
                real_pct=real * 100, error_pts=(pred - real) * 100,
            ))
    # Tendencia: solo se puede probar en 2021, porque 2015 no tiene dos previas.
    previas = [a for a in INTERMEDIAS if a in nacional.index and a < 2021]
    if len(previas) >= 2:
        pred = _tendencia(nacional.loc[previas], 2021)
        real = float(nacional.loc[2021])
        filas.append(dict(
            eleccion=2021, tipo=TIPO.get(2021, "?"),
            metodo="tendencia", pronostico_pct=pred * 100,
            real_pct=real * 100, error_pts=(pred - real) * 100,
        ))
    backtest = pd.DataFrame(filas)
    return dict(
        publicado=float(nacional.loc[publicado]),
        tendencia=tendencia,
        cambio=cambio,
        objetivo=int(objetivo),
        backtest=backtest,
        intermedios=[int(a) for a in intermedios],
    )


def tabla_nacional(nacional, info):
    """Tabla legible con observaciones, backtest y pronóstico de tendencia."""
    filas = []
    for anio, tasa in nacional.items():
        filas.append(dict(
            eleccion=int(anio), tipo=TIPO.get(int(anio), "?"),
            abstencion_pct=float(tasa) * 100, origen="observado",
            metodo="", pronostico_pct=np.nan, error_pts=np.nan,
        ))
    for fila in info["backtest"].itertuples(index=False):
        filas.append(dict(
            eleccion=int(fila.eleccion), tipo=fila.tipo,
            abstencion_pct=float(fila.real_pct), origen="backtest",
            metodo=fila.metodo, pronostico_pct=float(fila.pronostico_pct),
            error_pts=float(fila.error_pts),
        ))
    filas.append(dict(
        eleccion=info["objetivo"], tipo=TIPO.get(info["objetivo"], "?"),
        abstencion_pct=np.nan, origen="pronostico",
        metodo="tendencia_intermedias",
        pronostico_pct=float(info["tendencia"]) * 100, error_pts=np.nan,
    ))
    return pd.DataFrame(filas)


def tabla_escenarios(info):
    """Escenarios de nivel; el publicado se conserva por compatibilidad."""
    filas = [
        ("publicado_compatibilidad", "ultima_intermedia_2021", info["publicado"],
         "Valor usado en la corrida anterior y en la publicación"),
        ("tendencia_intermedias", "tendencia_intermedias", info["tendencia"],
         "Tendencia lineal de las intermedias anteriores"),
        ("ultimo_cambio", "ultimo_cambio", info["cambio"],
         "Última intermedia más el cambio de la anterior"),
    ]
    return pd.DataFrame([
        dict(escenario=nombre, metodo=metodo, nivel_pct=float(nivel) * 100,
             diferencia_vs_publicado_pts=(float(nivel) - info["publicado"]) * 100,
             nota=nota)
        for nombre, metodo, nivel, nota in filas
    ])
