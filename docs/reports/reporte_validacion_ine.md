# Validación de totales contra el tablero del INE (Fase 2)

**Resultado: 192 de 192 combinaciones estado–elección coinciden. Se cumple la validación externa de totales de la Fase 2.**

Consulta: 2026-10-24T23:18:29.122099+00:00 a 2026-10-24T23:18:44.725830+00:00.

## Fuente y alcance

[Página oficial del CCPC](https://ine.mx/transparencia/datos-abiertos/visualizacion-datos/conteos-censales-participacion/) y [tablero del INE, Datos generales](https://tableau.ine.mx/t/DECEYEC/views/Prototipo9/Datosgenerales?:embed=y&:showVizHome=no).

Libro **Plataforma Conteos Censales**, versión 65, publicado 2026-04-21T20:33:23.406Z.

Se extrajeron las hojas **Tabla General** (32 entidades) y **Totales Generales** para 2009, 2012, 2015, 2018, 2021 y 2024. El origen externo es el tablero publicado; no se recalcularon sus cifras desde los CSV del proyecto. Ambas publicaciones pueden compartir la misma base del INE: esto valida nuestro procesamiento contra el tablero, no constituye una auditoría independiente de la captura original del INE.

## Cómo se hizo y por qué

1. Se identificó el tablero enlazado por el INE, para comparar contra la publicación oficial correcta.
2. Se guardaron las respuestas originales con fecha, URL, formulario y SHA256, para conservar la evidencia y detectar alteraciones.
3. Se mantuvo el estrato Entidad y los filtros categóricos en (Todo), y se cambió únicamente el parámetro de año. El servidor confirmó cada año y se verificó además el año de la tabla nacional. Así se evita aceptar un filtro ignorado.
4. Se decodificaron las columnas y medidas que alimentan la tabla. La exportación CSV directa del dashboard devuelve una hoja informativa; por eso se conservaron las respuestas públicas de datos de Tableau, sin instalar librerías nuevas.
5. Se asignaron las claves estatales mediante una equivalencia explícita de abreviaturas. No se usó el orden de las filas: el tablero coloca Guerrero antes de Guanajuato y Sinaloa antes de San Luis Potosí.
6. Se comprobó que los 32 estados sumaran el total nacional publicado en los cuatro conteos, para revisar cobertura y extracción.
7. Se sumó data/interim/secciones.parquet por AELEC + EDOCVE y se compararon los cuatro conteos exactamente; los porcentajes se contrastaron con el redondeo oficial de un decimal.
8. Se guardaron las diferencias y se conectó esta validación con el generador de la Fase 2, para que el cierre se vuelva a comprobar al regenerar el reporte.

## Reglas de comparación

- LN, SV, NV y NS: igualdad exacta de enteros; diferencia = proyecto − INE. No se admite tolerancia en conteos.
- Participación = SV / (SV + NV); abstención = NV / (SV + NV); proporción NS = NS / LN. Primero se suma y después se divide.
- Los porcentajes oficiales se publican con un decimal. Se comprueba el mismo redondeo decimal (mitades hacia arriba), sin exigir igualdad contra porcentajes con mayor precisión.
- LN = SV + NV + NS debe cumplirse en ambos orígenes.
- El marco esperado son exactamente las 192 claves (seis elecciones × 32 entidades), sin duplicados ni ausencias.

## Resultados por elección

| Elección | Estados | Coinciden | Máx. diferencia LN | SV | NV | NS |
| --- | --- | --- | --- | --- | --- | --- |
| 2009 | 32 | 32 | 0 | 0 | 0 | 0 |
| 2012 | 32 | 32 | 0 | 0 | 0 | 0 |
| 2015 | 32 | 32 | 0 | 0 | 0 | 0 |
| 2018 | 32 | 32 | 0 | 0 | 0 | 0 |
| 2021 | 32 | 32 | 0 | 0 | 0 | 0 |
| 2024 | 32 | 32 | 0 | 0 | 0 | 0 |

Se comprobaron **768 conteos estatales** (192 × 4) y **576 porcentajes publicados** (participación, abstención y NS). El detalle está en `data/processed/comparacion_totales_ine.csv`.

## Diferencias y conclusión

No se encontraron diferencias en los conteos ni discrepancias de redondeo. La validación pendiente del punto 5 de la Fase 2 queda satisfecha. El catálogo y el registro de cambios territoriales ya están generados; conforme al criterio actual de PLAN.md, la Fase 2 queda cerrada.

El siguiente trabajo es la Fase 4. Las decisiones sobre el historial reconstruido y las intervenciones siguen en la Fase 5; el trabajo cartográfico de la Fase 6 continúa pendiente.

## Archivos y reproducción

- `data/external/validacion_ine/captura_*`: respuestas originales y metadatos locales; no se versionan.
- `data/processed/totales_oficiales_ine.csv`: cifras oficiales normalizadas; se versiona.
- `data/processed/fuentes_totales_ine.json`: procedencia, filtros, equivalencias, totales nacionales y huellas; se versiona.
- `data/processed/comparacion_totales_ine.csv`: valores de ambos orígenes, diferencias y verificaciones; se versiona.

```bash
# Repetir la comparación sin red (requiere la salida local de la Fase 2)
python scripts/comparar_totales_ine.py

# Reconstruir las cifras oficiales desde las capturas locales
python scripts/comparar_totales_ine.py --normalizar

# Obtener una captura nueva del sitio oficial (requiere red)
python scripts/descargar_evidencia_ine.py --tablero
python scripts/comparar_totales_ine.py --normalizar
```

## Qué afecta

Se añaden evidencia, agregados oficiales y una comprobación al reporte de la Fase 2. No se modifican datos originales, secciones, catálogo, cambios territoriales, tablas municipales, features ni respuestas del modelo. La comparación normal no accede a Internet. Una captura nueva sustituye los archivos locales `captura_*`; el manifiesto registra la versión consultada. Este reporte se genera con `scripts/comparar_totales_ine.py`.
