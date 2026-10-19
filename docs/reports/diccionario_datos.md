# Diccionario de datos: tablas de municipios (Fase 3)

Este documento explica qué trae cada tabla y qué significa cada columna. Lo escribe `python ai/src/data_prep/fase3.py`; no se edita a mano.

## Las tres tablas

En las tres, **cada fila es un municipio**. Están en `data/processed/`.

| Tabla | Qué trae | Para qué sirve | Filas |
|---|---|---|---|
| `municipio_eleccion` | Lo que pasó en cada municipio en cada elección, tal como viene | Revisar los datos y hacer el análisis exploratorio (Fase 4) | 14,779 |
| `tabla_municipios_entrenamiento` | Una fila por municipio y por foto (2015, 2018, 2021 y 2024): lo que se sabía antes de esa elección y, al final, la abstención que hubo | Que el modelo aprenda (Fase 7) | 9,866 |
| `tabla_municipios_2027` | Una fila por municipio: lo que se sabe hasta 2024 y, al final, la abstención de 2027 vacía | Que el modelo la llene; va a los mapas | 2,477 |

Las dos tablas de municipios tienen **las mismas columnas**. Cada tabla viene en dos archivos con el mismo contenido: `.csv` (se abre en Excel) y `.parquet` (para el código, con `pd.read_parquet`).

## Cómo leer los números

- Las columnas que empiezan con `pct_` o `abst_` son **proporciones de 0 a 1**: `0.25` quiere decir 25%.
- Las que terminan en `_vs_pais` y las de cambio o brecha son **diferencias**: `0.05` quiere decir 5 puntos más.
- **Vacío no es cero.** Una celda vacía quiere decir que no hay dato (por ejemplo, nadie con dato en el municipio), no que la abstención fue 0.
- Todos los porcentajes se calculan **sumando primero las personas y dividiendo después**, nunca promediando porcentajes de secciones.

## Qué es una foto

Para aprender, el modelo necesita ejemplos con la respuesta conocida. Una **foto** es la tabla de municipios armada como si estuviéramos justo antes de una elección: solo trae lo que se sabía hasta ese momento y, al final, la abstención que hubo.

| Foto | Usa elecciones | Última intermedia | Última presidencial | Lista nominal de | Abstención al final |
|---|---|---|---|---|---|
| 2015 | 2009 a 2012 | 2009 | 2012 | 2012 | la real |
| 2018 | 2009 a 2015 | 2015 | 2012 | 2015 | la real |
| 2021 | 2009 a 2018 | 2015 | 2018 | 2018 | la real |
| 2024 | 2009 a 2021 | 2021 | 2018 | 2021 | la real |
| 2027 | 2009 a 2024 | 2021 | 2024 | 2024 | vacía: la calcula el modelo |

Ejemplo real: **Puebla en la foto de 2021**.

| Lo que se sabía antes de 2021 | Valor |
|---|---|
| Abstención en la última intermedia (2015) | 65.6% |
| Promedio de intermedias (2009 y 2015) | 64.0% |
| Abstención en la última presidencial (2018) | 37.5% |
| Lista nominal (2018) | 1,280,498 |
| **Abstención que hubo en 2021 (la respuesta)** | **56.1%** |

El modelo practica con estas fotos («con lo que se sabía, ¿cuánto fue la abstención?») y luego llena la columna vacía de 2027.

## Municipios que cambiaron de territorio

Algunos municipios ganaron o perdieron secciones; por ejemplo, San Quintín se formó en 2024 con secciones que eran de Ensenada. Para que cada fila compare siempre el mismo territorio, **el pasado se calcula con las secciones que el municipio tiene en la elección que se predice**. San Quintín tiene historial con sus secciones de antes, y a Ensenada se le quitan de su pasado. Eso es un historial rearmado.

| Foto | Municipios | Sin respuesta | Con historial rearmado | Con historial incompleto |
|---|---|---|---|---|
| 2015 | 2,458 | 30 | 0 | 0 |
| 2018 | 2,463 | 13 | 0 | 0 |
| 2021 | 2,468 | 10 | 23 | 6 |
| 2024 | 2,477 | 12 | 46 | 11 |
| 2027 | 2,477 | todos (es 2027) | 46 | 11 |

- **Sin respuesta:** municipios donde nadie tuvo dato en esa elección. Esas filas no sirven para entrenar.
- **Historial incompleto:** a unas pocas secciones de su pasado no se les pudo encontrar dueño. En la foto de 2027 son como máximo 98,788 personas por elección, a lo mucho el 0.11% de la lista del país.

## Cuidados al usar los datos

- **Municipios sin dato:** en 73 filas no se sabe de nadie si votó (7 en 2009, 1 en 2012, 30 en 2015, 13 en 2018, 10 en 2021, 12 en 2024). Su abstención queda vacía.
- **Municipios muy chicos:** 475 filas tienen menos de 500 personas con dato. Ahí el porcentaje brinca mucho de una elección a otra. El mínimo para tomarlos en cuenta se decide después del análisis exploratorio.
- **Mucho NS:** en 206 filas no se sabe si votó más de la mitad de la lista. Ahí la abstención es menos confiable.
- **2012 está incompleto:** le faltan secciones que sí están en 2009 y 2015. La columna `pct_hueco_2012` dice cuánto le afecta a cada municipio (ver `reporte_consistencia.md`, sección 6).
- **Edad promedio y % de 60 o más dicen casi lo mismo** (correlación de 0.98, donde 1 sería que suben y bajan exactamente juntas): en el modelo conviene usar solo una.
- **El % de mujeres casi no cambia entre municipios** (casi todos están entre 46.4% y 57.0%), así que aporta poco. El % rural sí cambia mucho (de 0.0% a 93.7%).
- **La lista nominal cambia poco entre elecciones** (el % rural de 2021 y el de 2024 casi coinciden: correlación de 0.995, de un máximo de 1). Por eso cada foto usa la lista de la última elección anterior.
- **La abstención por grupo es ruidosa en municipios chicos:** con pocas personas en el grupo puede salir 0% o 100%.
- **Distritos:** de 2009 a 2021 vienen en el mapa de distritos de 2021, no en el que se usó en cada elección. Casi todos los municipios están en un solo distrito federal.

## Columnas de `municipio_eleccion`

El ejemplo es **Puebla en 2021**. La última columna dice si el dato **sirve para predecir esa misma elección**: «No» quiere decir que es parte del resultado y solo puede usarse como historial para elecciones posteriores.

**Quién es**

| Columna | Qué significa | Ejemplo | ¿Sirve para predecir? |
|---|---|---|---|
| `EDOCVE` | Número del estado (1 a 32) | 21 | Sí |
| `MPIOCVE` | Número del municipio dentro de su estado, según el INE. Ojo: no es la clave del INEGI | 115 | Sí |
| `AELEC` | Año de la elección | 2021 | Sí |
| `tipo_eleccion` | `intermedia` o `presidencial` | intermedia | Sí |
| `nombre_estado` | Nombre del estado | PUEBLA | Sí |
| `nombre_municipio` | Nombre del municipio (el de 2024, con las erratas corregidas) | Puebla | Sí |
| `situacion` | Si su territorio cambió en esa elección: `sin_cambio`, `cambio_limites` (ganó o perdió secciones), `nuevo` (primera vez que aparece) o `clave_reasignada` (su número pasó a otro territorio) | sin_cambio | Sí |

**Votos**

| Columna | Qué significa | Ejemplo | ¿Sirve para predecir? |
|---|---|---|---|
| `LN` | Lista nominal: personas registradas para votar | 1,330,685 | Sí |
| `SV` | Personas que sí votaron | 565,923 | No |
| `NV` | Personas que no votaron | 722,261 | No |
| `NS` | Personas de las que no se sabe si votaron | 42,501 | No |
| `conocidos` | Personas de las que sí se sabe si votaron (SV + NV) | 1,288,184 | No |
| `abstencion` | NV ÷ (SV + NV): de las personas con dato, cuántas no votaron. Es lo que se predice | 56.1% | No |
| `participacion` | SV ÷ (SV + NV). Es 1 menos la abstención | 43.9% | No |
| `pct_ns` | NS ÷ LN: parte de la lista de la que no se sabe si votó | 3.2% | No |

**Calidad del dato**

| Columna | Qué significa | Ejemplo | ¿Sirve para predecir? |
|---|---|---|---|
| `secciones` | Secciones que tiene el municipio | 774 | Sí |
| `secciones_sin_dato` | Secciones donde no se sabe de nadie si votó | 5 | No |
| `pct_ln_sin_dato` | Parte de la lista que vive en esas secciones sin dato | 0.2% | No |
| `pct_ln_secciones_nuevas` | Parte de la lista en secciones que aparecen por primera vez (el INE las creó dividiendo otras). En 2009 siempre es 0 | 1.6% | Sí |
| `ln_edad_marcada` | Personas registradas con más de 100 años (posible error del registro). Sí cuentan en «60 o más» | 194 | Sí |

**Cómo es su lista nominal**

| Columna | Qué significa | Ejemplo | ¿Sirve para predecir? |
|---|---|---|---|
| `pct_18_24` | Parte de la lista de 18 a 24 años | 15.2% | Sí |
| `pct_25_34` | Parte de la lista de 25 a 34 años | 23.2% | Sí |
| `pct_35_44` | Parte de la lista de 35 a 44 años | 19.8% | Sí |
| `pct_45_59` | Parte de la lista de 45 a 59 años | 24.0% | Sí |
| `pct_60_mas` | Parte de la lista de 60 o más años | 17.8% | Sí |
| `pct_mujeres` | Parte de la lista que son mujeres | 53.0% | Sí |
| `pct_no_binario` | Parte de la lista registrada como no binaria (solo existe en 2024) | 0.0% | Sí |
| `pct_urbana` | Parte de la lista en secciones urbanas | 98.3% | Sí |
| `pct_mixta` | Parte de la lista en secciones mixtas | 1.3% | Sí |
| `pct_rural` | Parte de la lista en secciones rurales | 0.4% | Sí |
| `edad_promedio` | Edad promedio de la lista | 42.7 años | Sí |

**Abstención por grupo**

| Columna | Qué significa | Ejemplo | ¿Sirve para predecir? |
|---|---|---|---|
| `abst_18_24` | Abstención de las personas de 18 a 24 años | 64.6% | No |
| `abst_25_34` | Abstención de las personas de 25 a 34 años | 69.3% | No |
| `abst_35_44` | Abstención de las personas de 35 a 44 años | 59.4% | No |
| `abst_45_59` | Abstención de las personas de 45 a 59 años | 46.9% | No |
| `abst_60_mas` | Abstención de las personas de 60 o más años | 40.2% | No |
| `abst_mujeres` | Abstención de las mujeres | 53.7% | No |
| `abst_hombres` | Abstención de los hombres | 58.7% | No |
| `abst_urbana` | Abstención en las secciones urbanas | 56.0% | No |
| `abst_mixta` | Abstención en las secciones mixtas | 64.7% | No |
| `abst_rural` | Abstención en las secciones rurales | 54.7% | No |

**Distritos**

| Columna | Qué significa | Ejemplo | ¿Sirve para predecir? |
|---|---|---|---|
| `n_def` | Cuántos distritos federales toca el municipio | 5 | Sí |
| `n_del` | Cuántos distritos locales toca el municipio | 8 | Sí |
| `def_principal` | El distrito federal donde vive la mayor parte de su lista | 9 | Sí |
| `pct_ln_def_principal` | Parte de la lista que vive en ese distrito principal | 25.4% | Sí |
| `pct_ln_sin_def` | Parte de la lista sin distrito federal (pasa en 2009 y 2012) | 0.0% | Sí |

## Columnas de `tabla_municipios_entrenamiento` y `tabla_municipios_2027`

El ejemplo es **Puebla en la foto de 2021**. Todo, menos las dos columnas del final, se calcula solo con elecciones anteriores a la que se predice, así que todo sirve para predecir. «Última» quiere decir la más reciente con dato.

**Quién es y qué se predice**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `EDOCVE` | Número del estado (1 a 32) | 21 |
| `MPIOCVE` | Número INE del municipio en la elección que se predice (para 2027, el de 2024) | 115 |
| `nombre_estado` | Nombre del estado | PUEBLA |
| `nombre_municipio` | Nombre del municipio | Puebla |
| `eleccion_objetivo` | La elección que se predice: 2015, 2018, 2021, 2024 o 2027 | 2021 |
| `tipo_objetivo` | Si esa elección es `intermedia` o `presidencial` | intermedia |

**Historial de intermedias**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `abst_ultima_intermedia` | Abstención de la última intermedia antes de la elección que se predice | 65.6% |
| `abst_prom_intermedias` | Promedio de la abstención de todas las intermedias anteriores | 64.0% |
| `cambio_intermedias` | Cuánto cambió entre las dos últimas intermedias (positivo = subió). Vacío si solo hay una | +3.2 puntos |
| `abst_ultima_intermedia_vs_pais` | La última intermedia menos la del país en esa elección (positivo = se abstiene más que el país) | +12.7 puntos |

**Historial de presidenciales**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `abst_ultima_presidencial` | Abstención de la última presidencial antes de la elección que se predice | 37.5% |
| `abst_prom_presidenciales` | Promedio de la abstención de todas las presidenciales anteriores | 37.5% |
| `abst_ultima_presidencial_vs_pais` | La última presidencial menos la del país en esa elección | -0.1 puntos |
| `brecha_intermedia_presidencial` | Cuánto más se abstiene en intermedias que en presidenciales (promedio de intermedias menos promedio de presidenciales) | +26.6 puntos |

**Abstención por grupo en la última intermedia**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `abst_18_24_ui` | Abstención de las personas de 18 a 24 años | 75.5% |
| `abst_25_34_ui` | Abstención de las personas de 25 a 34 años | 76.8% |
| `abst_35_44_ui` | Abstención de las personas de 35 a 44 años | 66.1% |
| `abst_45_59_ui` | Abstención de las personas de 45 a 59 años | 56.9% |
| `abst_60_mas_ui` | Abstención de las personas de 60 o más años | 48.8% |
| `abst_mujeres_ui` | Abstención de las mujeres | 63.2% |
| `abst_hombres_ui` | Abstención de los hombres | 68.3% |
| `abst_urbana_ui` | Abstención en las secciones urbanas | 65.7% |
| `abst_mixta_ui` | Abstención en las secciones mixtas | 66.3% |
| `abst_rural_ui` | Abstención en las secciones rurales | 43.3% |

**Cómo es su lista nominal (en la última elección antes de la que se predice)**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `ln_ultima` | Personas registradas para votar | 1,280,498 |
| `secciones_ultima` | Secciones que tiene | 768 |
| `pct_18_24` | Parte de la lista de 18 a 24 años | 16.6% |
| `pct_25_34` | Parte de la lista de 25 a 34 años | 23.1% |
| `pct_35_44` | Parte de la lista de 35 a 44 años | 20.5% |
| `pct_45_59` | Parte de la lista de 45 a 59 años | 23.2% |
| `pct_60_mas` | Parte de la lista de 60 o más años | 16.6% |
| `pct_mujeres` | Parte de la lista que son mujeres | 53.2% |
| `pct_urbana` | Parte de la lista en secciones urbanas | 98.4% |
| `pct_mixta` | Parte de la lista en secciones mixtas | 1.2% |
| `pct_rural` | Parte de la lista en secciones rurales | 0.4% |
| `edad_promedio` | Edad promedio de la lista | 41.9 años |

**Calidad del dato**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `n_intermedias_previas` | Cuántas intermedias anteriores tienen dato | 2 |
| `n_presidenciales_previas` | Cuántas presidenciales anteriores tienen dato | 2 |
| `pct_ns_ultima` | Parte de la lista sin saber si votó, en la última elección | 7.2% |
| `pct_ns_prom` | Lo mismo, en promedio de todas las elecciones anteriores | 2.8% |
| `conocidos_ultima` | Personas con dato (SV + NV) en la última elección | 1,187,774 |
| `pct_hueco_2012` | Parte de su lista de 2009 en secciones que faltan en 2012 | 0.2% |
| `historial_rearmado` | `True` si su historial se recalculó porque ganó o perdió secciones | False |
| `historial_incompleto` | `True` si alguna sección de su pasado no se pudo asignar | False |

**Distritos (en la última elección)**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `def_principal` | El distrito federal donde vive la mayor parte de su lista | 12 |
| `n_def` | Cuántos distritos federales toca | 5 |
| `n_del` | Cuántos distritos locales toca | 8 |

**La respuesta (siempre al final)**

| Columna | Qué significa | Ejemplo |
|---|---|---|
| `conocidos_objetivo` | Personas con dato en la elección que se predice; sirve para dar más peso a los municipios grandes. Vacío en 2027 | 1,288,184 |
| `abstencion_objetivo` | **La abstención de la elección que se predice.** En entrenamiento es la real; en 2027 está vacía y la llena el modelo | 56.1% |

## Revisiones que hace el script

Si alguna falla, el script se detiene y no guarda nada.

- ✅ Los totales por estado y elección son los mismos que en la Fase 2.
- ✅ La abstención nacional es la de los docs: 55.9% en 2009, 37.9% en 2012, 52.9% en 2015, 37.6% en 2018, 48.2% en 2021, 40.3% en 2024.
- ✅ Aguascalientes 2021 y 2024 coincide con el tablero del INE.
- ✅ Los grupos de edad, de sexo y de tipo de sección suman exactamente la lista nominal.
- ✅ En los municipios que no cambiaron de territorio, el historial rearmado es idéntico al original.
- ✅ Ninguna foto usa datos de la elección que predice ni de las posteriores.

## Cómo se usan después

1. **Análisis exploratorio (Fase 4):** con `municipio_eleccion` y `tabla_municipios_entrenamiento`. Las columnas nuevas que salgan de ahí se agregan a copias de las dos tablas de municipios.
2. **Modelo (Fase 7):** aprende con `tabla_municipios_entrenamiento` (la prueba clave es la foto de 2021) y llena `abstencion_objetivo` en `tabla_municipios_2027`.
3. **Escenarios (Fase 8):** se hace una copia de `tabla_municipios_2027` con la intervención supuesta. Es el mismo modelo y los mismos cortes del semáforo.


