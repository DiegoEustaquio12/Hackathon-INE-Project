# Mapa de escenarios con y sin intervención

Reto 2, Hackathon INE. Generado por `ai/src/geo/entregable_mapa.py` el 31/10/2026.

## Qué hay en esta carpeta

| Archivo | Qué es |
|---|---|
| `mapa_escenarios.gpkg` | **El mapa.** Capas `mapa_1_sin_intervencion`, `mapa_2_con_jovenes`, `mapa_2_con_hombres`, `mapa_2_con_rural`, `estados` y la tabla `escenarios_detalle`. Trae los colores del semáforo incluidos |
| `escenarios_municipios.geojson` | Los mismos datos en una sola capa, para cualquier programa (geojson.io, Power BI, Python) |
| `comparacion_sin_con.pdf` | Los mapas 1 y 2 lado a lado, una página por intervención |
| `comparacion_sin_con_<grupo>.png` | Lo mismo en imagen, una por intervención |
| `base_datos_escenarios.xlsx` | Resultados, detalle y diccionario en Excel |
| `escenarios_municipios.csv` | Una fila por municipio: sin intervención y las tres intervenciones con efecto de 10% |
| `escenarios_detalle.csv` | Los 9 escenarios por municipio (3 grupos × efecto de 5, 10 y 15%) |
| `base_modelo_entrenamiento.csv`, `base_modelo_2027.csv` | Las tablas municipales con las que se entrenó el modelo y se predijo 2027 |
| `diccionario_datos.csv` | Qué significa cada columna de cada archivo |
| `verificacion.txt` | Las comprobaciones que hizo el script |

## Cómo abrir el mapa en QGIS (3 pasos)

1. Arrastra `mapa_escenarios.gpkg` a QGIS (o *Capa → Añadir capa → Vectorial*).
2. Elige las capas `mapa_1_sin_intervencion` y una `mapa_2_con_...`. Aparecen ya coloreadas.
3. Enciende y apaga las capas para comparar. La capa `estados` ayuda a ubicarse.

En ArcGIS o en otros programas el color se arma con el campo `semaforo_sin` o `semaforo_con_<grupo>`.

## Cómo leerlo

- **Qué se predice:** el porcentaje de la lista nominal que no votaría en la elección intermedia de 2027.
- **Semáforo:** terciles del escenario sin intervención. Rojo (alta): 49.32% o más. Amarillo (media): 36.93% a 49.32%. Verde (baja): menos de 36.93%. Los mismos cortes se usan con intervención, para que los colores se puedan comparar.
- **Intervención:** hipotética. Se aplica solo en municipios en rojo y supone que una parte (10% en el caso base) de quienes no votan en el grupo elegido sí vota. **Su efecto es un supuesto, no una medición.**
- **Puntos:** diferencia entre dos porcentajes. 1 punto = 1 de cada 100 personas de la lista nominal.

## Cobertura

- Municipios con datos: 2,477. Con polígono: 2,475.
- Sin polígono: Eldorado (Sinaloa), Juan José Ríos (Sinaloa). Se crearon en 2021 y la cartografía es de 2022; su territorio aparece dentro de los municipios de los que salieron. Sus datos están en los CSV y en el Excel.
- Se corrigió la pareja de claves de San Pedro Mixtepec (Oaxaca): 20316 -> 20318, 20317 -> 20319 (INE → INEGI), confirmada con el nombre del polígono (-DTO. 22- y -DTO. 26-).

## Datos anonimizados

Todo está agregado por municipio: conteos y porcentajes. No hay datos de personas ni de secciones electorales.

## Fuentes

- Conteos Censales de Participación Ciudadana (CCPC) del INE, 2009–2024.
- Censo de Población y Vivienda (ECEG) del INEGI, 2010 y 2020, como variables del modelo.
- Polígonos: división política municipal 2022 del INEGI, publicada por CONABIO (acceso libre), simplificados a 200 m sin abrir huecos entre municipios. Coordenadas en EPSG:4326.
