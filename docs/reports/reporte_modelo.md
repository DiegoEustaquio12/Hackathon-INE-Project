# Reporte del modelo municipal (Fase 7)

LightGBM supera al punto de partida en los cuatro errores exigidos.

Se entregan 2,477 municipios. Método publicado: **modelo**. Generado por `python ai/src/models/fase7.py`; tasas en [0, 1], errores y aportes en puntos porcentuales.

## Definiciones y fuentes

Azael aprobó el 29/10/2026 estos valores para modelar, y el equipo todavía puede cambiarlos: mínimo de conocidos, NS fuera, conservar 2012, excluir respuestas ausentes, incluir historial rearmado y probar estados completos. El ECEG sigue sujeto a decisión del equipo y se evalúa como bloque candidato; `--sin-censo` lo retira.

Mínimo configurado: 500. Entrenamiento sin pesos; evaluación simple y ponderada por conocidos del objetivo.

| entrenables | filas | foto | sin_respuesta |
|---|---|---|---|
| 2364 | 2458 | 2015 | 30 |
| 2378 | 2463 | 2018 | 13 |
| 2394 | 2468 | 2021 | 10 |
| 2395 | 2477 | 2024 | 12 |

| abstencion_pct | eleccion |
|---|---|
| 55.939 | 2009 |
| 37.917 | 2012 |
| 52.926 | 2015 |
| 37.635 | 2018 |
| 48.162 | 2021 |
| 40.330 | 2024 |

Las tasas nacionales se obtienen de sumas NV / (SV + NV), antes de reconstruir territorios. Los predictores excluyen claves, nombres, año objetivo, vintage censal, distrito principal, marcas de cobertura, respuestas y los conteos de elecciones previas, que delatan el año de la foto. Se conservan NaN: LightGBM los trata directamente.

## Selección congelada antes de 2021

Cinco grupos de estados en 2015/2018; se minimiza MAE de la distancia municipal al país. Primero se comparan bloques con 15 hojas, 50 filas por hoja y error cuadrado; después los 18 ajustes. Los empates conservan el primer candidato. No se usan 2021 ni 2024 para elegir columnas, ajustes o árboles. La evaluación de 2021 se ejecuta después de congelarlos.

| bloque | columnas | mae_distancia_pts |
|---|---|---|
| A | 39 | 7.452 |
| A+B | 47 | 7.454 |
| A+B+C | 75 | 7.580 |

| candidato | hojas | minimo_hoja | objetivo | mae_distancia_pts | arboles_mediana | elegido |
|---|---|---|---|---|---|---|
| 1 | 7 | 20 | regression | 7.502 | 582 | False |
| 2 | 7 | 20 | regression_l1 | 7.349 | 546 | False |
| 3 | 7 | 50 | regression | 7.505 | 493 | False |
| 4 | 7 | 50 | regression_l1 | 7.365 | 589 | False |
| 5 | 7 | 100 | regression | 7.558 | 357 | False |
| 6 | 7 | 100 | regression_l1 | 7.391 | 358 | False |
| 7 | 15 | 20 | regression | 7.446 | 237 | False |
| 8 | 15 | 20 | regression_l1 | 7.377 | 347 | False |
| 9 | 15 | 50 | regression | 7.452 | 229 | False |
| 10 | 15 | 50 | regression_l1 | 7.366 | 320 | False |
| 11 | 15 | 100 | regression | 7.524 | 234 | False |
| 12 | 15 | 100 | regression_l1 | 7.412 | 169 | False |
| 13 | 31 | 20 | regression | 7.385 | 195 | False |
| 14 | 31 | 20 | regression_l1 | 7.338 | 274 | False |
| 15 | 31 | 50 | regression | 7.432 | 166 | False |
| 16 | 31 | 50 | regression_l1 | 7.327 | 172 | True |
| 17 | 31 | 100 | regression | 7.524 | 176 | False |
| 18 | 31 | 100 | regression_l1 | 7.425 | 182 | False |

Bloque: **A**; 39 columnas; 172 árboles (mediana del paro temprano). Ajustes elegidos: `{"min_data_in_leaf": 50, "num_leaves": 31, "objective": "regression_l1"}`.

Tasa 0.03, hasta 3,000 árboles y paciencia 100, 80% de filas y columnas por árbol, cuatro hilos, semilla 2027, deterministic=True y force_row_wise=True.

## Pruebas sin información del futuro

A: ajuste 2015/2018 y prueba 2021. B: ocho grupos definidos por los municipios de 2021; se retiran esos estados de ambas fotos de entrenamiento. Oaxaca queda sola. Se reúnen las distancias de B antes de centrarlas nacionalmente; no se centra cada estado a la media del país. C: ajuste hasta 2021 y prueba presidencial 2024; no decide la adopción.

| prueba | metodo | n | mae_pts | mae_ponderado_pts | spearman | mismo_tercio_pct | rojos_detectados_pct |
|---|---|---|---|---|---|---|---|
| A_2021 | modelo | 2458 | 9.312 | 6.189 | 0.818 | 69.203 | 75.122 |
| A_2021 | punto de partida | 2458 | 12.401 | 8.456 | 0.490 | 45.037 | 51.951 |
| B_estados | modelo | 2458 | 10.270 | 6.337 | 0.705 | 59.927 | 61.829 |
| B_estados | punto de partida | 2458 | 12.401 | 8.456 | 0.490 | 45.037 | 51.951 |
| C_2024 | modelo | 2465 | 6.469 | 3.959 | 0.818 | 69.452 | 74.331 |
| C_2024 | punto de partida | 2465 | 5.703 | 3.784 | 0.838 | 72.576 | 78.224 |

El punto de partida repite la última elección del mismo tipo sin ajustarse al nivel nacional. Cada comparación usa las mismas filas con respuesta y referencia conocida, incluidos los casos pequeños. El centrado del modelo usa todos los municipios de la foto, aun sin respuesta, ponderados por conocidos_ultima. Para 2021 solo se supone el nivel nacional conocido de 2015; para 2024, el de 2018.

El acierto de color parte cada método en sus propios tercios, como el semáforo por orden: el error del nivel nacional, igual para todos, no cambia el color. rojos_detectados_pct es la parte de los rojos reales que el método también pone en rojo. Es un diagnóstico; los cortes definitivos de Fase 8 siguen pendientes.

### Municipios con cambios territoriales

Las marcas rearmado e incompleto pueden solaparse.

| foto | incompletos | incompletos_evaluables | rearmados | rearmados_evaluables |
|---|---|---|---|---|
| 2015 | 0 | 0 | 0 | 0 |
| 2018 | 0 | 0 | 0 | 0 |
| 2021 | 6 | 5 | 23 | 21 |
| 2024 | 11 | 11 | 46 | 46 |

| prueba | segmento | metodo | n | mae_pts | mae_ponderado_pts | spearman | mismo_tercio_pct | rojos_detectados_pct |
|---|---|---|---|---|---|---|---|---|
| A_2021 | rearmado | modelo | 21 | 12.280 | 6.203 | 0.756 | 57.143 | 57.143 |
| A_2021 | rearmado | punto de partida | 21 | 15.797 | 12.193 | 0.114 | 19.048 | 14.286 |
| A_2021 | incompleto | modelo | 5 | 15.807 | 18.362 | 0.700 | 40.000 | 50.000 |
| A_2021 | incompleto | punto de partida | 5 | 19.450 | 19.555 | 0.000 | 60.000 | 50.000 |
| A_2021 | sin_marcas | modelo | 2437 | 9.286 | 6.189 | 0.819 | 69.224 | 75.154 |
| A_2021 | sin_marcas | punto de partida | 2437 | 12.372 | 8.408 | 0.492 | 44.973 | 51.907 |
| B_estados | rearmado | modelo | 21 | 12.203 | 5.377 | 0.742 | 52.381 | 57.143 |
| B_estados | rearmado | punto de partida | 21 | 15.797 | 12.193 | 0.114 | 19.048 | 14.286 |
| B_estados | incompleto | modelo | 5 | 16.709 | 19.148 | 0.700 | 40.000 | 50.000 |
| B_estados | incompleto | punto de partida | 5 | 19.450 | 19.555 | 0.000 | 60.000 | 50.000 |
| B_estados | sin_marcas | modelo | 2437 | 10.253 | 6.350 | 0.705 | 59.787 | 61.747 |
| B_estados | sin_marcas | punto de partida | 2437 | 12.372 | 8.408 | 0.492 | 44.973 | 51.907 |
| C_2024 | rearmado | modelo | 46 | 6.903 | 3.398 | 0.744 | 63.043 | 75.000 |
| C_2024 | rearmado | punto de partida | 46 | 6.506 | 3.615 | 0.779 | 67.391 | 81.250 |
| C_2024 | incompleto | modelo | 11 | 7.277 | 2.061 | 0.573 | 45.455 | 50.000 |
| C_2024 | incompleto | punto de partida | 11 | 7.136 | 2.448 | 0.600 | 63.636 | 75.000 |
| C_2024 | sin_marcas | modelo | 2419 | 6.461 | 3.991 | 0.820 | 69.574 | 74.349 |
| C_2024 | sin_marcas | punto de partida | 2419 | 5.688 | 3.793 | 0.839 | 72.799 | 78.191 |

## Sensibilidades (no eligen el modelo)

Se mantienen columnas, ajustes y árboles. Mínimos 100/1,000 solo filtran entrenamiento. NS máximo 10%/20% filtra entrenamiento y evaluación por NS objetivo, con ambos métodos en la misma cohorte. NS como no voto cambia respuesta, nacional y referencia a (NV+NS)/LN, solo sin historial rearmado ni incompleto; se conserva la cohorte de A y los predictores históricos mantienen su definición base para aislar el cambio de respuesta. Sin 2012 usa las tres versiones *_sin_2012 que no son conteos y retira cambios presidenciales, distancia presidencial al país, composición, conteos y calidad que podrían incorporar 2012; estas últimas no tienen una alternativa canónica. El censo usa 2010 en 2015/2018: su antigüedad limita la extrapolación.

| prueba | metodo | n_entrenamiento | n_columnas | n | mae_pts | mae_ponderado_pts | nota |
|---|---|---|---|---|---|---|---|
| minimo_100 | modelo | 4876 | 39 | 2458 | 9.192 | 6.156 | — |
| minimo_100 | punto de partida | 4876 | 39 | 2458 | 12.401 | 8.456 | — |
| minimo_1000 | modelo | 4506 | 39 | 2458 | 9.525 | 6.215 | — |
| minimo_1000 | punto de partida | 4506 | 39 | 2458 | 12.401 | 8.456 | — |
| ns_max_10 | modelo | 3856 | 39 | 2146 | 9.346 | 5.911 | — |
| ns_max_10 | punto de partida | 3856 | 39 | 2146 | 12.183 | 8.189 | — |
| ns_max_20 | modelo | 4368 | 39 | 2336 | 9.236 | 6.093 | — |
| ns_max_20 | punto de partida | 4368 | 39 | 2336 | 12.318 | 8.430 | — |
| ns_como_no_voto | modelo | 4742 | 39 | 2437 | 10.708 | 6.661 | — |
| ns_como_no_voto | punto de partida | 4742 | 39 | 2437 | 13.227 | 8.825 | — |
| sin_2012 | modelo | 4742 | 18 | 2458 | 12.536 | 6.636 | — |
| sin_2012 | punto de partida | 4742 | 18 | 2458 | 12.401 | 8.456 | — |
| sin_censo | modelo | 4742 | 39 | 2458 | 9.312 | 6.189 | Ya excluido en la ejecución principal |
| sin_censo | punto de partida | 4742 | 39 | 2458 | 12.401 | 8.456 | Ya excluido en la ejecución principal |

## Rango empírico nominal del 80%

Se usa observado menos predicho en A, descontando lo que ya se sabe que falló el supuesto nacional de esa prueba (nivel real de 2021 menos el de 2015: -4.764 pp), con percentiles 10/90 por tercil de conocidos_ultima. Así el rango mide solo el error municipal; la incertidumbre del país va en los escenarios de la sección siguiente. Se amplía hasta incluir el punto predicho cuando ambos percentiles tienen el mismo signo; se recorta a [0, 1]. Se calibra con el método publicado, incluido el respaldo si corresponde. La cobertura se mide sobre esos mismos residuos, con la misma corrección: es aparente, no una prueba independiente ni una garantía para 2027.

| grupo | margen_max | margen_min | n | q10 | q90 |
|---|---|---|---|---|---|
| 0 | 0.114 | -0.118 | 819 | -0.118 | 0.114 |
| 1 | 0.068 | -0.158 | 819 | -0.158 | 0.068 |
| 2 | 0.055 | -0.096 | 820 | -0.096 | 0.055 |

Cortes de tamaño: [4467.0, 15828.0]. Cobertura aparente: 79.984%. Ancho medio 2027: 20.099 pp.

## Supuesto nacional y escenarios

Nivel nacional supuesto 2027: **48.16202%**, calculado con 2021 (48.16% redondeado). Para el modelo se resuelve un desplazamiento constante para que la media con pesos conocidos_ultima coincida con ese nivel, incluso tras recortar. No se utiliza el nivel real de la elección que se evalúa para corregir las predicciones.

Media ponderada publicada: **48.16202%**. Si se publica la referencia se respeta la repetición exacta: sus pesos actuales pueden cambiar la media.

| cambio_nivel_pts | nivel_supuesto_pct | abstencion_media_ponderada_pct | participacion_media_ponderada_pct |
|---|---|---|---|
| -5.000 | 43.162 | 43.162 | 56.838 |
| 0.000 | 48.162 | 48.162 | 51.838 |
| 5.000 | 53.162 | 53.162 | 46.838 |

Los escenarios ±5 pp solo cambian el supuesto nacional, sin reentrenar ni simular una intervención. El rango municipal no incluye la incertidumbre sobre ese nivel: para eso están estos escenarios.

## Explicación

Las razones municipales son los tres mayores aportes absolutos TreeSHAP del modelo final. Cada aporte suma/resta puntos de abstención a su distancia (en participación el signo se invierte); faltan la base SHAP y el desplazamiento nacional para reconstruir la predicción completa. El recorte puede reducir el efecto final. La dirección global es la correlación entre valor y aporte; no demuestra causalidad.

| columna | descripcion | aporte_absoluto_medio_pts | aporte_medio_pts | correlacion_valor_aporte | direccion |
|---|---|---|---|---|---|
| abst_ultima_presidencial | Abstención de la última presidencial antes de la elección que se predice | 3.802 | 1.208 | 0.941 | valores altos suben |
| abst_ultima_presidencial_vs_pais | La última presidencial menos la del país en esa elección | 3.237 | 0.180 | 0.989 | valores altos suben |
| es_intermedia | Si la elección objetivo es intermedia | 1.860 | -1.860 | — | relación no monotónica |
| abst_prom_presidenciales | Promedio de la abstención de todas las presidenciales anteriores | 1.546 | 0.278 | 0.968 | valores altos suben |
| abst_ultima_intermedia_vs_pais | La última intermedia menos la del país en esa elección (positivo = se abstiene más que el país) | 0.868 | -0.352 | 0.899 | valores altos suben |
| abst_18_24_ui | Abstención de las personas de 18 a 24 años | 0.713 | -0.480 | 0.888 | valores altos suben |
| cambio_intermedias | Cuánto cambió entre las dos últimas intermedias (positivo = subió). Vacío si solo hay una | 0.433 | 0.285 | -0.214 | valores altos bajan |
| pct_35_44 | Parte de la lista de 35 a 44 años | 0.385 | -0.221 | 0.780 | valores altos suben |
| secciones_ultima | Secciones que tiene | 0.261 | -0.005 | 0.073 | valores altos suben |
| abst_35_44_ui | Abstención de las personas de 35 a 44 años | 0.193 | 0.111 | -0.698 | valores altos bajan |

Base SHAP: -5.60571 pp. Desplazamiento de centrado del candidato: 0.67680 pp.

## Calidad y reproducción

| marca | municipios |
|---|---|
| pocos_casos | 82 |
| ns_alto | 38 |
| historial_rearmado | 46 |
| historial_incompleto | 11 |
| sin_censo | 9 |

pocos_casos conserva la definición de menos de 500 personas conocidas en 2024, incluso si --minimo cambia. sin_censo marca ausencia completa de cobertura; censo_utilizado indica si sus variables entraron en el método publicado. Ninguna marca borra municipios ni se imputa una respuesta real.

Limitación: cuatro fotos para ajustar y una sola intermedia para decidir; el rango y las importancias no sustituyen validación prospectiva. La adopción del ECEG y la cartografía siguen pendientes del equipo/INE.

## Carpetas y archivos

Para correr todo: `python ai/src/models/fase7.py`. Para revisarlo: `python -m unittest ai/tests/test_modelo.py`.

| Carpeta | Qué guarda |
|---|---|
| `data/processed/` | Lo que entra: las tres tablas de la Fase 3. El modelo solo las lee, y al terminar comprueba con huellas SHA256 que no cambiaron |
| `ai/src/data_prep/` | Piezas de las Fases 1 a 3 que el modelo reutiliza: rutas, listas de columnas y sus descripciones |
| `ai/src/models/` | El código de esta fase |
| `ai/tests/` | Las pruebas automáticas; `test_modelo.py` es la de esta fase |
| `ai/artifacts/` | Lo que sale: el modelo, las pruebas y las predicciones de 2027. Se versiona |
| `docs/reports/` | Este reporte, que se escribe leyendo las salidas |

**Lo que entra**, en `data/processed/`:

- `tabla_municipios_entrenamiento.parquet`: las cuatro fotos (2015, 2018, 2021 y 2024). De aquí aprende el modelo y aquí se prueba.
- `tabla_municipios_2027.parquet`: lo que se sabe hasta 2024 de cada municipio. Es la tabla que el modelo llena.
- `municipio_eleccion.parquet`: los conteos de cada municipio en cada elección. De aquí salen el nivel del país y la variante que cuenta el NS como no voto.

**El código**, en `ai/src/models/`:

- `fase7.py`: el script que se corre. Hace todo en orden y escribe las salidas y este reporte.
- `datos_modelo.py`: lee las tablas, calcula la distancia contra el país, arma los bloques de columnas y dice cuáles no pueden entrar.
- `validacion.py`: entrena LightGBM, elige columnas y ajustes con 2015 y 2018, corre las pruebas y calcula los errores y el rango.
- `explicacion.py`: calcula cuánto aporta cada columna y las tres razones de cada municipio.

**Lo que sale**, en `ai/artifacts/`:

| Archivo | Qué guarda |
|---|---|
| `predicciones_2027.parquet` y `predicciones_2027.csv` | La salida principal, una fila por municipio. Copia `tabla_municipios_2027`, llena `abstencion_objetivo` y agrega abstención y participación con su rango, las tres razones y las marcas de calidad. Es lo que usan la Fase 8 y los mapas |
| `modelo_2027.txt` | El modelo final de LightGBM, entrenado con las cuatro fotos. Se guarda aunque se publique el punto de partida |
| `modelo_config.json` | La ficha de la corrida: método publicado, columnas, ajustes, nivel del país, rango, versiones de las librerías y huellas SHA256 de las tablas, el código y las salidas |
| `seleccion_congelada.json` | Las columnas, los ajustes y los árboles elegidos con 2015 y 2018, guardados antes de mirar 2021 |
| `seleccion_columnas.csv` | El error de cada bloque de columnas y de cada ajuste probado, en cada grupo de estados |
| `validacion.csv` | Los errores del modelo y del punto de partida en las pruebas de 2021, por estados y de 2024 |
| `predicciones_pruebas.csv` | Las predicciones de esas pruebas, municipio por municipio; con ellas se recalculan los errores |
| `sensibilidades.csv` | Las mismas comparaciones de 2021 con las variantes de la Fase 5 |
| `explicacion_global.csv` | Cuánto pesa cada columna en todo el país y hacia dónde empuja |
| `escenarios_nivel.csv` | El promedio nacional de 2027 si el país queda 5 puntos arriba o abajo del supuesto |
