"""Conserva las respuestas públicas del tablero CCPC del INE y sus metadatos.

Uso: python scripts/descargar_evidencia_ine.py --tablero
Solo descarga información agregada del tablero; no modifica tablas de análisis.
"""
import argparse
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data/external/validacion_ine'
HOST = 'https://tableau.ine.mx'
VIZ = '/vizql/t/DECEYEC/w/Prototipo9/v/Datosgenerales'
ANIOS = (2009, 2012, 2015, 2018, 2021, 2024)
BOOT_FORM = {'sheet_id': 'Datos generales', 'clientDimension': json.dumps({'w': 1200, 'h': 900}),
             'renderMapsClientSide': 'true', 'isBrowserRendering': 'true', 'browserRenderingThreshold': '100',
             'formatDataValueLocally': 'false', 'locale': 'es_ES', 'language': 'es', 'timezoneOffset': '360'}

def descargar(url, nombre, form=None, post=False):
    if urlparse(url).hostname not in {'ine.mx', 'www.ine.mx', 'tableau.ine.mx'}:
        raise ValueError('Solo se permiten fuentes públicas del INE')
    if Path(nombre).name != nombre:
        raise ValueError('El nombre no puede contener directorios')
    DEST.mkdir(parents=True, exist_ok=True)
    body = urlencode(form).encode('utf-8') if isinstance(form, dict) else (form.encode('utf-8') if form else None)
    method = 'POST' if post or body is not None else 'GET'
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0',
        'Content-Type': 'application/x-www-form-urlencoded'}, data=body, method=method)
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
        meta = {'url': url, 'url_final': response.url, 'metodo': method, 'formulario': form,
                'consulta_utc': datetime.now(timezone.utc).isoformat(),
                'content_type': response.headers.get('Content-Type'), 'sha256': hashlib.sha256(data).hexdigest(),
                'bytes': len(data)}
    (DEST / nombre).write_bytes(data)
    (DEST / (nombre + '.meta.json')).write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'{nombre}: {len(data):,} bytes; SHA256 {meta["sha256"][:12]}', flush=True)
    return data

def tablero():
    inicio = descargar(HOST + VIZ + '/startSession/viewing?:embed=y&:showVizHome=no&:tabs=yes',
                       'captura_sesion.json', post=True)
    config = json.loads(inicio)
    sid = config['sessionid']
    descargar(HOST + VIZ + '/bootstrapSession/sessions/' + sid, 'captura_inicial.txt', BOOT_FORM)
    for anio in ANIOS:
        data = descargar(HOST + VIZ + '/sessions/' + sid + '/commands/tabdoc/set-parameter-value',
                         f'captura_{anio}.json', {'globalFieldName': '[Parameters].[Par\u00e1metro 4]',
                                                  'valueString': str(anio), 'useUsLocale': 'false'})
        result = json.loads(data)['vqlCmdResponse']['cmdResultList']
        controls = [r.get('commandReturn', {}).get('parameterControl', {}) for r in result]
        if not any(c.get('formattedValue') == str(anio) for c in controls):
            raise RuntimeError(f'El servidor no confirmó el año {anio}')
    print('Captura completa. Normalizar y comparar con scripts/comparar_totales_ine.py --normalizar', flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('url', nargs='?')
    p.add_argument('nombre', nargs='?')
    p.add_argument('--tablero', action='store_true')
    p.add_argument('--post', action='store_true')
    p.add_argument('--form')
    a = p.parse_args()
    if a.tablero:
        tablero()
    elif a.url and a.nombre:
        descargar(a.url, a.nombre, a.form, a.post)
    else:
        p.error('Usa --tablero o URL NOMBRE')

if __name__ == '__main__':
    main()
