"""Validación externa de los totales estatales de la Fase 2.

Compartida por fase2.py y scripts/comparar_totales_ine.py. No usa la red.
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

# Importar por el paquete del proyecto evita el paquete externo homónimo ccpc.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ai.src.data_prep.ccpc import ANIOS, CONTEOS, PROCESSED, RAIZ, REPORTES

OFICIALES = PROCESSED / 'totales_oficiales_ine.csv'
MANIFIESTO = PROCESSED / 'fuentes_totales_ine.json'
SECCIONES = RAIZ / 'data/interim/secciones.parquet'
LLAVE = ['AELEC', 'EDOCVE']
TASAS = {'participacion': ('SV', 'conocidos', 'participacion_publicada'),
         'abstencion': ('NV', 'conocidos', 'abstencion_publicada'),
         'pct_ns': ('NS', 'LN', 'pct_ns_publicado')}
INICIO = '<!-- inicio-validacion-ine -->'
FIN = '<!-- fin-validacion-ine -->'


def validar_claves(df):
    esperadas = {(a, e) for a in ANIOS for e in range(1, 33)}
    actuales = set(df[LLAVE].itertuples(index=False, name=None))
    if df.duplicated(LLAVE).any() or len(df) != 192 or actuales != esperadas:
        raise ValueError('Se requieren exactamente 192 claves únicas: 32 estados por seis elecciones')


def cargar_oficiales():
    fuente = json.loads(MANIFIESTO.read_text(encoding='utf-8'))
    if hashlib.sha256(OFICIALES.read_bytes()).hexdigest() != fuente['oficiales_sha256']:
        raise ValueError('El CSV oficial cambió respecto a su manifiesto; volver a normalizar la evidencia')
    df = pd.read_csv(OFICIALES, encoding='utf-8-sig')
    validar_claves(df)
    for c in CONTEOS:
        if df[c].isna().any() or (df[c] < 0).any() or (df[c] != df[c].astype('int64')).any():
            raise ValueError(f'Conteo oficial inválido: {c}')
    if not (df.LN == df.SV + df.NV + df.NS).all():
        raise ValueError('Los conteos oficiales no cumplen LN = SV + NV + NS')
    for _, _, col in TASAS.values():
        if df[col].isna().any() or not df[col].between(0, 1).all():
            raise ValueError(f'Porcentaje oficial inválido: {col}')
    for row in fuente['totales_nacionales']:
        g = df.loc[df.AELEC == row['AELEC'], CONTEOS].sum()
        if any(int(g[c]) != row[c] for c in CONTEOS):
            raise ValueError('Los estados normalizados no suman la tabla nacional oficial')
    for row in df.itertuples():
        if row.evidencia_sha256 not in {x['sha256'] for x in fuente['archivos']}:
            raise ValueError('Una fila oficial no tiene referencia de evidencia en el manifiesto')
    return df, fuente


def redondeo_publicado(numerador, denominador):
    if denominador == 0:
        raise ValueError('Un total estatal no tiene denominador conocido; requiere revisión')
    return (Decimal(int(numerador)) * 100 / Decimal(int(denominador))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def comparar(oficiales, secciones=None):
    if secciones is None:
        secciones = pd.read_parquet(SECCIONES, columns=[*LLAVE, *CONTEOS])
    proyecto = secciones.groupby(LLAVE)[CONTEOS].sum().astype('int64').reset_index()
    validar_claves(proyecto)
    validar_claves(oficiales)
    resultado = oficiales.merge(proyecto, on=LLAVE, suffixes=('_ine', '_proyecto'), validate='one_to_one')
    for c in CONTEOS:
        resultado[f'diferencia_{c}'] = resultado[f'{c}_proyecto'] - resultado[f'{c}_ine']
        resultado[f'coincide_{c}'] = resultado[f'diferencia_{c}'].eq(0)
    resultado['regla_ln_ine'] = resultado.LN_ine.eq(resultado.SV_ine + resultado.NV_ine + resultado.NS_ine)
    resultado['regla_ln_proyecto'] = resultado.LN_proyecto.eq(resultado.SV_proyecto + resultado.NV_proyecto + resultado.NS_proyecto)
    resultado['conocidos_proyecto'] = resultado.SV_proyecto + resultado.NV_proyecto
    for nombre, (num, den, publicada) in TASAS.items():
        numerador = resultado[f'{num}_proyecto']
        denominador = resultado['conocidos_proyecto'] if den == 'conocidos' else resultado[f'{den}_proyecto']
        resultado[f'{nombre}_proyecto'] = numerador / denominador
        resultado[f'diferencia_{nombre}_pp'] = 100 * (resultado[f'{nombre}_proyecto'] - resultado[publicada])
        esperado = [redondeo_publicado(n, d) for n, d in zip(numerador, denominador)]
        publicado = [(Decimal(str(x)) * 100).quantize(Decimal('0.1')) for x in resultado[publicada]]
        resultado[f'coincide_{nombre}_redondeo'] = [a == b for a, b in zip(esperado, publicado)]
    checks = [f'coincide_{c}' for c in CONTEOS] + ['regla_ln_ine', 'regla_ln_proyecto'] + [f'coincide_{t}_redondeo' for t in TASAS]
    resultado['coincide'] = resultado[checks].all(axis=1)
    resultado['estado_validacion'] = resultado['coincide'].map({True: 'coincide', False: 'revisar'})
    return resultado.sort_values(LLAVE, ignore_index=True)


def bloque_validacion_ine(resultado=None):
    try:
        if resultado is None:
            oficiales, _ = cargar_oficiales()
            resultado = comparar(oficiales)
        ok = int(resultado.coincide.sum())
        estado = (f'**Completada:** {ok}/192 combinaciones estado–elección coinciden exactamente en LN, SV, NV y NS; '
                  'participación, abstención y NS coinciden con el redondeo publicado. Se cumple el punto 5 de la Fase 2.'
                  if ok == 192 else f'**Pendiente de cierre:** {ok}/192 combinaciones coinciden; revisar las diferencias.')
    except (OSError, ValueError, KeyError) as error:
        estado = f'**Pendiente de cierre:** no hay una validación externa vigente ({error}). Ejecutar `python scripts/comparar_totales_ine.py`.'
    return '\n'.join([INICIO, '', '### Comparación con el tablero del INE', '', estado, '',
        'La comparación se calcula contra los totales actuales de `data/interim/secciones.parquet`; '
        'no se confía únicamente en un resultado anterior guardado. Fuente, método y evidencia en '
        '[reporte_validacion_ine.md](reporte_validacion_ine.md).', '', FIN])


def actualizar_reporte_consistencia(resultado):
    ruta = REPORTES / 'reporte_consistencia.md'
    texto = ruta.read_text(encoding='utf-8')
    bloque = bloque_validacion_ine(resultado)
    if INICIO in texto:
        texto = re.sub(re.escape(INICIO) + r'.*?' + re.escape(FIN) + r'\n*', lambda _: bloque + '\n\n', texto, flags=re.S)
    else:
        patron = r'- \*\*Comparar con el tablero del INE\*\*[^\n]+'
        texto, n = re.subn(patron, lambda _: bloque, texto, count=1)
        if n != 1:
            raise ValueError('No se encontró el bloque de validación del reporte de consistencia')
    texto = texto.replace('## 8. Pendiente', '## 8. Validación oficial y decisiones pendientes')
    texto = texto.replace('falta contrastar los totales con el tablero.',
                          'el contraste de totales con el tablero queda documentado en `reporte_validacion_ine.md`.')
    texto = texto.replace('Fase 3: armar la tabla de municipios con este catálogo. El nombre sale de `nombre_municipio`, y las columnas '
                          '`situacion_AAAA` dicen qué parte del historial de cada municipio se puede comparar.',
                          'La Fase 3 ya produjo las tablas municipales y su diccionario. El siguiente trabajo es el EDA de la Fase 4; '
                          'la decisión sobre el historial reconstruido sigue en la Fase 5.')
    ruta.write_text(texto, encoding='utf-8')
