"""Normaliza evidencia de Tableau y contrasta los 192 totales estatales del CCPC.

Sin --normalizar usa los agregados oficiales versionados y no requiere red.
Con --normalizar reconstruye esos agregados desde las capturas originales.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'ai/src/data_prep'))
from validacion_ine import ANIOS, CONTEOS, OFICIALES, MANIFIESTO, comparar, cargar_oficiales

RAW = RAIZ / 'data/external/validacion_ine'
SALIDA = RAIZ / 'data/processed/comparacion_totales_ine.csv'
REPORTE = RAIZ / 'docs/reports/reporte_validacion_ine.md'
PAGINA = 'https://ine.mx/transparencia/datos-abiertos/visualizacion-datos/conteos-censales-participacion/'
TABLERO = 'https://tableau.ine.mx/t/DECEYEC/views/Prototipo9/Datosgenerales?:embed=y&:showVizHome=no'
# Equivalencia explícita, no por orden de filas: el tablero ordena GRO antes de GTO y SIN antes de SLP.
ESTADOS = {'AGS': 1, 'BC': 2, 'BCS': 3, 'CAMP': 4, 'COAH': 5, 'COL': 6, 'CHIS': 7, 'CHIH': 8,
           'CDMX': 9, 'DGO': 10, 'GTO': 11, 'GRO': 12, 'HGO': 13, 'JAL': 14, 'MEX': 15,
           'MICH': 16, 'MOR': 17, 'NAY': 18, 'NL': 19, 'OAX': 20, 'PUE': 21, 'QRO': 22,
           'QROO': 23, 'SLP': 24, 'SIN': 25, 'SON': 26, 'TAB': 27, 'TAMPS': 28, 'TLAX': 29,
           'VER': 30, 'YUC': 31, 'ZAC': 32}
MEDIDAS = {'Lista nominal': 'LN', 'Sí votaron': 'SV', 'No votaron': 'NV', 'Votos no esp.': 'NS'}


def leer_evidencia(nombre):
    ruta = RAW / nombre
    datos = ruta.read_bytes()
    meta = json.loads(ruta.with_name(nombre + '.meta.json').read_text(encoding='utf-8'))
    if hashlib.sha256(datos).hexdigest() != meta['sha256']:
        raise ValueError(f'La captura {nombre} no coincide con su SHA256')
    return datos.decode('utf-8'), {'archivo': str(ruta.relative_to(RAIZ)).replace('\\', '/'), **meta}


def bloques_bootstrap(texto):
    dec = json.JSONDecoder()
    partes = []
    while texto.strip():
        texto = texto.lstrip()
        prefijo = re.match(r'\d+;', texto)
        if prefijo:
            texto = texto[prefijo.end():]
        objeto, fin = dec.raw_decode(texto)
        partes.append(objeto)
        texto = texto[fin:]
    return partes


def actualizar_segmentos(segmentos, cambio):
    for clave, valor in cambio.get('dataSegments', {}).items():
        if valor is None:
            segmentos.pop(clave, None)
        else:
            segmentos[clave] = valor


def diccionario(segmentos):
    valores = defaultdict(list)
    for _, segmento in sorted(segmentos.items(), key=lambda kv: int(kv[0])):
        for columna in segmento['dataColumns']:
            valores[columna['dataType']].extend(columna['dataValues'])
    return valores


def leer_tabla(pane, valores):
    if len(pane['paneColumnsList']) != 1:
        raise ValueError('Cambió la estructura de la tabla de Tableau: se esperaba un solo panel')
    columnas = {}
    for col in pane['vizDataColumns']:
        nombre = col.get('fieldCaption')
        if not nombre:
            continue
        vector = pane['paneColumnsList'][0]['vizPaneColumns'][col['columnIndices'][0]]
        columnas[nombre] = [valores['cstring'][-i - 1] if i < 0 else valores[col['dataType']][i]
                            for i in vector['aliasIndices']]
    return pd.DataFrame(columnas)


def validar_filtros(zonas):
    filtros = {}
    for zona in zonas.values():
        holder = zona.get('presModelHolder', {})
        control = holder.get('parameterControl')
        if control and control['fieldCaption'] == 'Estrato Tabla General':
            if control['formattedValue'] != 'Entidad':
                raise ValueError('El estrato oficial no es Entidad')
            filtros['estrato'] = 'Entidad'
        q = holder.get('quickFilterDisplay', {}).get('quickFilter')
        if not q:
            continue
        nombre = ', '.join(q.get('columnFullNames', []))
        if q.get('quickFilterType') == 'categorical':
            if not q['categoricalFilter'].get('allSelected'):
                raise ValueError(f'Hay un filtro categórico activo: {nombre}')
            filtros[nombre] = '(Todo)'
        else:
            if q.get('included') != 'include-all' or q.get('valueMin') != q.get('rangeMin') or q.get('valueMax') != q.get('rangeMax'):
                raise ValueError(f'Hay un filtro cuantitativo activo: {nombre}')
            # Se conserva el control completo para auditar sus límites y el universo consultado.
            filtros[nombre] = q
    return filtros


def pivotar(tabla, indice):
    if tabla.duplicated([*indice, 'Nombres de medidas']).any():
        raise ValueError('Medidas repetidas en la respuesta oficial')
    return tabla.pivot(index=indice, columns='Nombres de medidas', values='Valores de medidas').reset_index()


def conteo(texto):
    if not re.fullmatch(r'\d{1,3}(,\d{3})*|\d+', str(texto)):
        raise ValueError(f'Conteo oficial inesperado: {texto!r}')
    return int(str(texto).replace(',', ''))


def porcentaje(texto):
    if not re.fullmatch(r'\d+\.\d%', str(texto)):
        raise ValueError(f'Porcentaje oficial inesperado (se esperaba un decimal): {texto!r}')
    return float(Decimal(str(texto)[:-1]) / 100)


def normalizar():
    texto, meta = leer_evidencia('captura_inicial.txt')
    partes = bloques_bootstrap(texto)
    sec = partes[1]['secondaryInfo']['presModelMap']
    segmentos = {}
    actualizar_segmentos(segmentos, sec['dataDictionary']['presModelHolder']['genDataDictionaryPresModel'])
    zonas = partes[0]['worldUpdate']['applicationPresModel']['workbookPresModel']['dashboardPresModel']['zones']
    filtros = validar_filtros(zonas)
    if filtros.get('estrato') != 'Entidad':
        raise ValueError('No se encontró el control de estrato Entidad')
    evidencias = [meta]
    texto_sesion, meta_sesion = leer_evidencia('captura_sesion.json')
    config = json.loads(texto_sesion)
    evidencias.insert(0, meta_sesion)
    filas = []
    nacionales = []
    for anio in ANIOS:
        texto, meta = leer_evidencia(f'captura_{anio}.json')
        evidencias.append(meta)
        respuesta = json.loads(texto)['vqlCmdResponse']
        controles = [x.get('commandReturn', {}).get('parameterControl', {}) for x in respuesta['cmdResultList']]
        if not any(x.get('formattedValue') == str(anio) for x in controles):
            raise ValueError(f'El servidor no confirmó el parámetro del año {anio}')
        app = respuesta['layoutStatus']['applicationPresModel']
        actualizar_segmentos(segmentos, app['dataDictionary'])
        valores = diccionario(segmentos)
        cambio_zonas = app['workbookPresModel']['dashboardPresModel']['zones']
        zonas.update(cambio_zonas)
        tablas = {}
        for zona in cambio_zonas.values():
            pane = zona.get('presModelHolder', {}).get('visual', {}).get('vizData', {}).get('paneColumnsData')
            if pane:
                caps = {x.get('fieldCaption') for x in pane['vizDataColumns']}
                if {'Nombre', 'Ent.', 'Valores de medidas'} <= caps:
                    tablas['estatal'] = leer_tabla(pane, valores)
                elif {'Año', 'Caja 1', 'Valores de medidas'} <= caps:
                    tablas['nacional'] = leer_tabla(pane, valores)
        nacional = pivotar(tablas['nacional'], ['Año'])
        if list(nacional['Año']) != [anio]:
            raise ValueError(f'La tabla nacional no corresponde a {anio}')
        estatal = pivotar(tablas['estatal'], ['Nombre', 'Ent.'])
        if len(estatal) != 32 or set(estatal['Ent.']) != set(ESTADOS):
            raise ValueError(f'Cobertura estatal incompleta en {anio}')
        suma = {c: 0 for c in CONTEOS}
        for _, row in estatal.iterrows():
            registro = {'AELEC': anio, 'EDOCVE': ESTADOS[row['Ent.']], 'estado_oficial': row['Nombre'],
                        'abreviatura_oficial': row['Ent.']}
            for medida, codigo in MEDIDAS.items():
                registro[codigo] = conteo(row[medida])
                suma[codigo] += registro[codigo]
            for medida, codigo in [('% Participación', 'participacion_publicada'),
                                   ('% Abstención', 'abstencion_publicada'), ('% Votos no esp.', 'pct_ns_publicado')]:
                registro[codigo] = porcentaje(row[medida])
            registro.update({'fuente_url': TABLERO, 'consulta_utc': meta['consulta_utc'],
                             'evidencia_archivo': meta['archivo'], 'evidencia_sha256': meta['sha256']})
            filas.append(registro)
        for medida, codigo in MEDIDAS.items():
            if suma[codigo] != conteo(nacional.iloc[0][medida]):
                raise ValueError(f'Los 32 estados no suman el total oficial nacional {codigo}, {anio}')
        nacionales.append({'AELEC': anio, **suma, 'participacion_publicada': porcentaje(nacional.iloc[0]['% Participación'])})
        validar_filtros(zonas)
    df = pd.DataFrame(filas).sort_values(['AELEC', 'EDOCVE'], ignore_index=True)
    OFICIALES.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OFICIALES, index=False, encoding='utf-8-sig')
    manifest = {'pagina_fuente': PAGINA, 'tablero': TABLERO, 'libro': config['workbookName'],
                'version_libro': config['workbookContentVersion'], 'publicado_utc': config['workbookLastPublishedAt'],
                'parametro_anio': '[Parameters].[Parámetro 4]', 'filtros_iniciales': filtros,
                'equivalencia_estados': ESTADOS, 'archivos': evidencias, 'totales_nacionales': nacionales,
                'oficiales_sha256': hashlib.sha256(OFICIALES.read_bytes()).hexdigest(),
                'metodo': 'Respuestas públicas de Tableau: Tabla General y Totales Generales. Sin CSV originales del proyecto.'}
    MANIFIESTO.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return df, manifest


def tabla_md(headers, filas):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |',
                      *['| ' + ' | '.join(map(str, row)) + ' |' for row in filas]])


def escribir_reporte(resultado, fuentes):
    completos = bool(resultado['coincide'].all())
    lineas = ['# Validación de totales contra el tablero del INE (Fase 2)', '',
        '**Resultado: ' + ('192 de 192 combinaciones estado–elección coinciden. Se cumple la validación externa de totales de la Fase 2.**' if completos else
                           'hay diferencias o datos faltantes. La Fase 2 no se puede cerrar.**'), '',
        f"Consulta: {min(x['consulta_utc'] for x in fuentes['archivos'])} a {max(x['consulta_utc'] for x in fuentes['archivos'])}.", '',
        '## Fuente y alcance', '',
        f'[Página oficial del CCPC]({PAGINA}) y [tablero del INE, Datos generales]({TABLERO}).', '',
        f"Libro **{fuentes['libro']}**, versión {fuentes['version_libro']}, publicado {fuentes['publicado_utc']}.", '',
        'Se extrajeron las hojas **Tabla General** (32 entidades) y **Totales Generales** para 2009, 2012, 2015, '
        '2018, 2021 y 2024. El origen externo es el tablero publicado; no se recalcularon sus cifras desde los CSV del proyecto. '
        'Ambas publicaciones pueden compartir la misma base del INE: esto valida nuestro procesamiento contra el tablero, '
        'no constituye una auditoría independiente de la captura original del INE.', '',
        '## Cómo se hizo y por qué', '',
        '1. Se identificó el tablero enlazado por el INE, para comparar contra la publicación oficial correcta.',
        '2. Se guardaron las respuestas originales con fecha, URL, formulario y SHA256, para conservar la evidencia y detectar alteraciones.',
        '3. Se mantuvo el estrato Entidad y los filtros categóricos en (Todo), y se cambió únicamente el parámetro de año. '
        'El servidor confirmó cada año y se verificó además el año de la tabla nacional. Así se evita aceptar un filtro ignorado.',
        '4. Se decodificaron las columnas y medidas que alimentan la tabla. La exportación CSV directa del dashboard devuelve una hoja '
        'informativa; por eso se conservaron las respuestas públicas de datos de Tableau, sin instalar librerías nuevas.',
        '5. Se asignaron las claves estatales mediante una equivalencia explícita de abreviaturas. No se usó el orden de las filas: '
        'el tablero coloca Guerrero antes de Guanajuato y Sinaloa antes de San Luis Potosí.',
        '6. Se comprobó que los 32 estados sumaran el total nacional publicado en los cuatro conteos, para revisar cobertura y extracción.',
        '7. Se sumó data/interim/secciones.parquet por AELEC + EDOCVE y se compararon los cuatro conteos exactamente; '
        'los porcentajes se contrastaron con el redondeo oficial de un decimal.',
        '8. Se guardaron las diferencias y se conectó esta validación con el generador de la Fase 2, para que el cierre '
        'se vuelva a comprobar al regenerar el reporte.', '',
        '## Reglas de comparación', '',
        '- LN, SV, NV y NS: igualdad exacta de enteros; diferencia = proyecto − INE. No se admite tolerancia en conteos.',
        '- Participación = SV / (SV + NV); abstención = NV / (SV + NV); proporción NS = NS / LN. Primero se suma y después se divide.',
        '- Los porcentajes oficiales se publican con un decimal. Se comprueba el mismo redondeo decimal (mitades hacia arriba), '
        'sin exigir igualdad contra porcentajes con mayor precisión.',
        '- LN = SV + NV + NS debe cumplirse en ambos orígenes.',
        '- El marco esperado son exactamente las 192 claves (seis elecciones × 32 entidades), sin duplicados ni ausencias.', '',
        '## Resultados por elección', '']
    filas = []
    for anio, g in resultado.groupby('AELEC'):
        filas.append([anio, len(g), int(g['coincide'].sum()), *[int(g[f'diferencia_{c}'].abs().max()) for c in CONTEOS]])
    lineas += [tabla_md(['Elección', 'Estados', 'Coinciden', 'Máx. diferencia LN', 'SV', 'NV', 'NS'], filas), '',
               'Se comprobaron **768 conteos estatales** (192 × 4) y **576 porcentajes publicados** '
               '(participación, abstención y NS). El detalle está en `data/processed/comparacion_totales_ine.csv`.', '',
               '## Diferencias y conclusión', '']
    if completos:
        lineas += ['No se encontraron diferencias en los conteos ni discrepancias de redondeo. '
                   'La validación pendiente del punto 5 de la Fase 2 queda satisfecha. El catálogo y el registro de cambios '
                   'territoriales ya están generados; conforme al criterio actual de PLAN.md, la Fase 2 queda cerrada.', '',
                   'El siguiente trabajo es la Fase 4. Las decisiones sobre el historial reconstruido y las intervenciones '
                   'siguen en la Fase 5; el trabajo cartográfico de la Fase 6 continúa pendiente.']
    else:
        lineas += ['No se declara el cierre. Revisar las filas con `coincide = False` en el CSV de comparación.']
    lineas += ['', '## Archivos y reproducción', '',
        '- `data/external/validacion_ine/captura_*`: respuestas originales y metadatos locales; no se versionan.',
        '- `data/processed/totales_oficiales_ine.csv`: cifras oficiales normalizadas; se versiona.',
        '- `data/processed/fuentes_totales_ine.json`: procedencia, filtros, equivalencias, totales nacionales y huellas; se versiona.',
        '- `data/processed/comparacion_totales_ine.csv`: valores de ambos orígenes, diferencias y verificaciones; se versiona.', '',
        '```bash', '# Repetir la comparación sin red (requiere la salida local de la Fase 2)',
        'python scripts/comparar_totales_ine.py', '', '# Reconstruir las cifras oficiales desde las capturas locales',
        'python scripts/comparar_totales_ine.py --normalizar', '', '# Obtener una captura nueva del sitio oficial (requiere red)',
        'python scripts/descargar_evidencia_ine.py --tablero', 'python scripts/comparar_totales_ine.py --normalizar', '```', '',
        '## Qué afecta', '',
        'Se añaden evidencia, agregados oficiales y una comprobación al reporte de la Fase 2. '
        'No se modifican datos originales, secciones, catálogo, cambios territoriales, tablas municipales, features ni respuestas del modelo. '
        'La comparación normal no accede a Internet. Una captura nueva sustituye los archivos locales `captura_*`; '
        'el manifiesto registra la versión consultada. Este reporte se genera con `scripts/comparar_totales_ine.py`.', '']
    REPORTE.write_text('\n'.join(lineas), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--normalizar', action='store_true')
    args = parser.parse_args(argv)
    if args.normalizar:
        normalizar()
    oficiales, fuentes = cargar_oficiales()
    resultado = comparar(oficiales)
    resultado.to_csv(SALIDA, index=False, encoding='utf-8-sig')
    escribir_reporte(resultado, fuentes)
    # Actualiza solo el bloque generado, sin volver a ejecutar ni sobrescribir los datos de las fases anteriores.
    from validacion_ine import actualizar_reporte_consistencia
    actualizar_reporte_consistencia(resultado)
    print(f'Validación INE: {int(resultado.coincide.sum())}/{len(resultado)} estados-elección coinciden')
    print(f'Reporte: {REPORTE.relative_to(RAIZ)}')
    return 0 if resultado.coincide.all() else 1

if __name__ == '__main__':
    raise SystemExit(main())
