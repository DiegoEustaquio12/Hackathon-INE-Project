# Reto 2 (riesgo de abstención)

Este documento explica qué nos pide el reto, cómo vamos a resolverlo y, sobre todo, **qué contienen los datos** con los que vamos a trabajar. La idea es que todo el equipo entienda lo mismo antes de meternos al modelo.

---

## 1. De qué trata el reto

**Problema.** El INE tiene recursos limitados para promover la participación en las elecciones. El reto pide anticipar en qué zonas del país podría bajar la participación, para decidir dónde actuar primero.

**Herramienta que vamos a hacer.** Un modelo de regresión que usa los datos del CCPC del INE de 2009 a 2024 para predecir la **tasa de abstención por municipio** en una elección futura. A partir de esa predicción se clasifica el riesgo con un semáforo, en dos escenarios (sin intervención y con una intervención hipotética). **Ya definimos que una zona del proyecto es un municipio. Todos los campos de los archivos del INE están disponibles para el análisis y la preparación de variables. Como fuentes externas sociodemográficas se incorporan los ECEG 2010 y 2020 del INEGI; los Censos Económicos no se usan porque sus datos abiertos son solo nacionales.** Las definiciones necesarias para modelar se aprobaron al solicitar la implementación de Fase 7; los escenarios con intervención y el semáforo por terciles ya se implementaron en la Fase 8, y la ratificación del semáforo sigue pendiente.

**Estado actual (30/10/2026).** Las fases 1 a 4 son reproducibles. Azael aprobó los valores de la sección 7 para modelar, y el modelo de la Fase 7 le gana a repetir la última elección del mismo tipo en 2021 y dejando estados fuera. La prueba secundaria de 2024 no decide y excede la tolerancia pre-registrada; el reporte recomienda evaluar una mezcla o un modelo más simple. La Fase 8 ya genera los escenarios con intervención sobre la predicción publicada, con el semáforo por terciles. El reporte y las predicciones están en `docs/reports/reporte_modelo.md`, los escenarios en `docs/reports/reporte_fase8.md` y los artefactos en `ai/artifacts/`. Siguen pendientes la cartografía y la ratificación del semáforo.

**Quién la usaría.** Las áreas del INE que planean y reparten recursos de capacitación electoral y educación cívica, como la DECEyEC y las juntas locales y distritales (por confirmar).

El público usuario describe quién consulta la herramienta; no define la zona del modelo. Aunque una junta distrital consulte los resultados, estos se estiman por municipio.

**Qué decisión apoya.** En qué territorios concentrar acciones, y de qué tipo, antes de la elección.

## 2. Cómo funciona la herramienta

Flujo: **Datos → Modelo → Escenarios → Semáforo → Mapas → Recomendaciones**

| Pieza | Qué es |
|---|---|
| **Datos** | Una tabla donde cada fila es un municipio en una elección, construida a partir de todos los campos disponibles en los archivos del INE: conteos, historial, edad, sexo, tipo de sección, información territorial y demás campos |
| **Modelo** | Predice mediante regresión la tasa de abstención de cada municipio |
| **Escenarios** | Salen de una sola predicción del modelo. Sin intervención es la predicción tal cual, que sigue las tendencias históricas. Con intervención es esa misma predicción más el efecto que suponemos que tendría una acción hipotética del INE; el modelo no se vuelve a correr. Antes de calcularlo hay que definir a quién va dirigida, dónde se aplica y qué efecto se espera |
| **Semáforo** | Clasifica cada zona por nivel de riesgo. Los cortes se fijan una vez con el escenario sin intervención y se usan iguales en el escenario con intervención, para que los colores sean comparables |
| **Mapas** | Muestran los resultados de cada escenario |
| **Recomendaciones** | Qué zonas priorizar y qué acción tomar, a partir de los mapas |

**Nota sobre "sin intervención":** los datos históricos ya incluyen todo lo que el INE hizo hasta 2024. Por eso este escenario no es "un mundo sin INE", sino lo que pasaría si todo sigue igual que hasta ahora.

## 3. Los mapas

| Orden | Mapa | Qué muestra | Colores | Estatus |
|---|---|---|---|---|
| 1 | Sin intervención | Riesgo de abstención por zona en la elección objetivo, si las tendencias siguen igual | Semáforo | Obligatorio |
| 2 | Con intervención | El mismo mapa, aplicando el supuesto de intervención hipotética | Semáforo (mismos cortes que el mapa 1) | Obligatorio |

Son dos mapas, los que pide la convocatoria. Al picarle a un municipio se abre una ventana con sus datos. Ahí se ve la **diferencia entre los dos escenarios** (cuántos puntos sube la participación al intervenir) y la brecha intermedia vs presidencial; no son mapas aparte.

En esta primera versión, la zona de los dos mapas es el municipio.

## 4. Qué tenemos que entregar

**Mínimos del Reto 2 (según la convocatoria):**

- **Reporte metodológico y preventivo:** PDF de 10 a 15 cuartillas. Debe explicar las variables usadas y contener el semáforo de riesgo (clasificación de zonas por nivel de riesgo de abstención), las recomendaciones preventivas y cómo priorizar recursos.
- **Mapa de escenarios con y sin intervención:** un archivo de mapas (SHP, GeoJSON o GPKG) o un enlace a un tablero en Power BI o Tableau, junto con la base de datos anonimizada que usamos (CSV o XLSX).

**Generales (para todos los retos):** presentación de máximo 10 diapositivas, código o enlace a un repositorio, y las cartas de cesión de derechos y de decir verdad firmadas por todas las personas del equipo.

Si falta cualquier entregable mínimo, el equipo queda descalificado.

## 5. Lo que necesitamos para cumplir los entregables

1. **El contorno de cada municipio.** Para hacer los mapas necesitamos polígonos municipales, y el CCPC no los trae: solo trae tablas. Hay que conseguirlos de la cartografía del INE y verificar su fecha y correspondencia territorial con los datos. Si se construyen a partir de contornos de secciones, hay que verificar su cobertura y asignación municipal. El uso y entrega de esa cartografía siguen pendientes de confirmación con el INE.
2. **Que los municipios de los datos y del mapa se puedan unir.** Se identifican con `EDOCVE` + `MPIOCVE`. Hay que revisar cambios de claves, límites y asignación de secciones para saber qué historial municipal es comparable (Fase 2 del plan).
3. **La base que entreguemos debe ser la que usamos.** Va agregada por zona, sin grupos muy pequeños de personas. Si usamos la cartografía, hay que revisar que se pueda entregar.
4. **Diccionario de datos desde el inicio.** El reporte exige explicar las variables, así que cada una se documenta al agregarla: nombre, definición, fuente, año y qué le hicimos.

---

## 6. Entendiendo los datos del CCPC

### ¿De dónde salen?

De la plataforma de Conteos Censales de Participación Ciudadana (CCPC) del INE:
https://ine.mx/transparencia/datos-abiertos/visualizacion-datos/conteos-censales-participacion/

Se descarga un `.zip` por cada elección:

- [2024](https://ine.mx/wp-content/uploads/2025/08/DatosAbiertos_DECEyEC_ConteosCensales2024.zip)
- [2021](https://ine.mx/wp-content/uploads/2022/04/DatosAbiertos_DECEyEC_ConteosCensales2021.zip)
- [2018](https://ine.mx/wp-content/uploads/2022/04/DatosAbiertos_DECEyEC_ConteosCensales2018.zip)
- [2015](https://ine.mx/wp-content/uploads/2022/04/DatosAbiertos_DECEyEC_ConteosCensales2015.zip)
- [2012](https://ine.mx/wp-content/uploads/2022/04/DatosAbiertos_DECEyEC_ConteosCensales2012.zip)
- [2009](https://ine.mx/wp-content/uploads/2022/04/DatosAbiertos_DECEyEC_ConteosCensales2009.zip)

Dentro de cada `.zip` hay **un archivo por estado** (32 en cada año) y un diccionario de datos. Para consultar o comparar cifras existe también el tablero interactivo en la misma página, y su manual: https://ine.mx/wp-content/uploads/2025/06/Manual-Conteos-Censales-2009-2024.pdf

Hay otros archivos en esa página (voto anticipado 2024, prisión preventiva 2024 y Poder Judicial 2025), pero quedan fuera de nuestro análisis principal.

### ¿Qué es una fila?

**Una fila no es una persona.** Es un grupo de gente que tiene en común tres cosas: la misma **sección electoral**, el mismo **sexo** y la misma **edad**. La fila nos dice cuántas personas de ese grupo estaban en la lista para votar y cuántas votaron.

Ejemplo real (Aguascalientes 2021, sección 1, hombres de 18 años):

> Había **16** personas en la lista nominal. **13** votaron, **3** no votaron y **0** quedaron sin especificar.

### ¿Qué significa cada columna?

Los archivos tienen 16 columnas, las mismas en los seis años:

| Columna | Qué es |
|---|---|
| `AELEC` | Año de la elección |
| `FELECCION` | Fecha de la elección |
| `EDOCVE` / `EDONOM` | Número y nombre del estado |
| `MPIOCVE` / `MPIONOM` | Número y nombre del municipio |
| `SECCION` | Sección electoral: la zona más pequeña en la que el INE divide el país. El número se repite entre estados, así que una sección se identifica con **estado + sección** |
| `TIPOSEC` | Tipo de sección: `U` urbana, `R` rural, `M` mixta |
| `DEF` | Distrito electoral federal |
| `DEL` | Distrito electoral local (a veces viene vacío) |
| `SEXO` | `0` = hombre, `1` = mujer, `2` = no binario (este último solo existe en 2024) |
| `EDAD` | Edad en años |
| `LN` | **Lista nominal**: cuántas personas de ese grupo están registradas para votar |
| `SV` | **Sí votaron** |
| `NV` | **No votaron** |
| `NS` | **No especificado**: no se sabe si votaron (ver más abajo) |

> **Sobre `SEXO`:** confirmamos que `0` es hombre y `1` es mujer comparando el archivo de Aguascalientes 2021 contra el tablero del INE. El diccionario de 2024 identifica `2` como no binario; el tablero y la suma de los 32 archivos de ese año coinciden en **105 personas** con ese código.

**Uso en el proyecto.** Todos los campos de esta tabla se conservan y están disponibles para el análisis y la preparación de variables. Esto incluye `SEXO`, `EDAD`, `TIPOSEC`, `DEF` y `DEL`, además de los conteos y los demás campos. La restricción es sobre las fuentes externas: solo se admiten los ECEG 2010 y 2020 del INEGI, elegidos según la fecha de la elección; no se usan los Censos Económicos porque sus datos abiertos son solo nacionales. Las variables que ya proporciona el INE no tienen restricción. Al construir la tabla municipal se documenta cómo se resume o representa cada campo; la selección de predictores se evalúa después del EDA y solo usa información disponible antes de la elección que se quiere predecir.

### La regla que siempre se cumple

**`LN = SV + NV + NS`**

Es decir, cada persona de la lista cae en una de tres cajas: votó, no votó o no se sabe. Una revisión rápida, hecha solo para corroborar, encontró que se cumple en todas las filas. La Fase 1 lo vuelve a verificar.

### ¿Cómo se calculan la participación y la abstención?

Así lo define el INE y así lo vamos a hacer nosotros:

- **Participación** = `SV / (SV + NV)`
- **Abstención** = `NV / (SV + NV)`

Fíjense que **`NS` se deja fuera** del cálculo.

**Nunca se promedian porcentajes de secciones.** Si una sección de 100 personas tiene 80% de participación y otra de 1,000 tiene 40%, el promedio simple da 60%, pero la participación real es 480 / 1,100 = 43.6%. Primero se suman las personas y después se calcula el porcentaje.

### ¿Qué es `NS` (no especificado)?

**No es voto nulo.** Es gente de la lista de la que **no se sabe si votó o no**, por ejemplo porque el cuadernillo (el cuaderno de la lista nominal donde se marca quién votó) no tenía marcas, no se pudo capturar o faltaba una página. Es un dato faltante.

- Estos datos **no dicen por quién votó la gente ni si el voto fue nulo**. Solo dicen si fue a votar o no.
- **Decisión aprobada para modelar: excluir `NS`**, igual que el INE. Más adelante probamos cuánto cambian los resultados si lo contamos como "no votó".
- Cuidado: el porcentaje de `NS` cambia mucho entre estados. En 2021 va de 1.4% en Colima a 12.7% en Chihuahua. Por eso la participación no es igual de confiable en todos lados.
- **Hay secciones donde no se sabe de nadie si votó.** Ahí la participación es desconocida (no es cero). En 2024 son unas 2,100 secciones.
- **2012 casi no tiene `NS`** (0.2%) y su lista nominal es menor que la de 2009. Un [manual del INE](https://www.ine.mx/wp-content/uploads/2019/12/DECEyEC-manualConteosCensales.pdf) explica que en 2012 se excluyeron los cuadernillos no disponibles, a diferencia de las otras elecciones. En la Fase 2 se evalúa cómo afecta esto a las comparaciones entre años.

### Ejemplo: Aguascalientes completo

Sumando todas las filas del estado:

| | 2021 (intermedia) | 2024 (presidencial) |
|---|---|---|
| Lista nominal | 1,017,420 | 1,097,171 |
| Sí votaron | 489,469 | 626,084 |
| No votaron | 499,413 | 441,222 |
| No especificado | 28,538 | 29,865 |
| **Participación** | **49.5%** | **58.7%** |

Estas cifras salen de sumar los archivos. Las contrastamos con el tablero del INE para ambos sexos juntos en 2021 y 2024, y coinciden.

Se ve la diferencia entre una elección intermedia y una presidencial: la gente participa bastante más cuando hay presidenciales.

### Panorama nacional

Sumando los 32 estados (revisión rápida, hecha solo para corroborar; las cifras se confirman en la Fase 1):

| Elección | Tipo | Secciones | Lista nominal | Participación |
|---|---|---|---|---|
| 2009 | Intermedia | 64,934 | 77,481,831 | 44.1% |
| 2012 | Presidencial | 65,599 | 76,490,962 | 62.1% |
| 2015 | Intermedia | 68,362 | 83,563,462 | 47.1% |
| 2018 | Presidencial | 68,408 | 89,123,997 | 62.4% |
| 2021 | Intermedia | 68,812 | 93,532,133 | 51.8% |
| 2024 | Presidencial | 70,751 | 98,330,348 | 59.7% |

Lo que salta a la vista:

- Las presidenciales se parecen entre sí (alrededor de 60%), pero las **intermedias cambian mucho de una a otra** (de 44% a 52%). Adivinar el porcentaje exacto de 2027 va a ser difícil. En el EDA se comprobará si el historial municipal permite ordenar mejor los municipios de más a menos riesgo que estimar su porcentaje exacto.
- **El número de secciones crece:** de 64,934 en 2009 a 70,751 en 2024.

### Lo que cambia con el tiempo

- **Las secciones cambian.** El INE divide y redibuja secciones cuando crecen mucho (reseccionamiento). Por eso hay secciones nuevas que no tienen historial: en 2024 son 2,775. Antes de usar el historial de una sección hay que confirmar que sigue siendo la misma zona (Fase 2 del plan).
- **Los distritos cambiaron en 2023** (redistritación). El distrito de una sección en 2024 puede ser distinto al que tenía en 2021. Un cambio de distrito por sí solo no cambia el agregado municipal si la sección sigue en el mismo municipio y este conserva su territorio. Las predicciones y el reporte serán municipales.
- **La comparabilidad municipal también se verifica.** Hay que revisar municipios nuevos, cambios de clave o límites y cambios en la asignación de secciones. El reseccionamiento dentro de un mismo municipio no implica por sí solo que este pierda su historial, pero tampoco garantiza que el territorio municipal siga siendo comparable.

### Niveles de análisis

Como cada fila trae estado, municipio, distrito y sección, podemos sumar a cualquier nivel. La sección es la unidad más pequeña y todo lo demás son sumas de secciones. Los niveles no están anidados entre sí (un municipio no necesariamente cae en un solo distrito), así que siempre se suma desde la sección.

**En el proyecto, una zona es un municipio.** Después de unir los archivos y verificar la comparabilidad, se agrega por municipio y elección con la clave `EDOCVE` + `MPIOCVE` + `AELEC`. Se suman `LN`, `SV`, `NV` y `NS`, y luego se calculan las tasas. También se resume la composición por edad, sexo y tipo de sección, y se prepara la información territorial y los demás campos disponibles para el análisis municipal.

Los distritos federales (`DEF`) y locales (`DEL`) están disponibles para el análisis y la preparación de variables. Como un municipio puede abarcar varios distritos, hay que documentar cómo se representa esa relación sin asignarle arbitrariamente uno solo. Utilizar información distrital no cambia la unidad municipal de la predicción ni convierte el resultado en una estimación por distrito o sección.

### ¿Qué NO trae esta base?

- Ingreso, marginación ni condición de actividad económica detallada. La escolaridad y otras características sociodemográficas se toman de los ECEG 2010 y 2020 (ver abajo).
- Si la persona es indígena o afromexicana: el CCPC no lo trae, pero el ECEG 2020 sí incluye lengua indígena y población afromexicana agregadas por sección.
- Mapas o coordenadas (los contornos municipales para nuestros mapas hay que conseguirlos aparte).
- Voto nulo ni por quién se votó.
- Votos en casillas especiales ni de personas que viven en el extranjero. Además, la sección es la del domicilio de la credencial. Por eso las cifras no cuadran exacto con los cómputos distritales, y hay que aclararlo en el reporte.

### Fuentes externas: ECEG 2010 y 2020

Para complementar el CCPC se usan los **ECEG (Entorno para la Construcción de Escenarios Geoelectorales)** del INEGI, derivados de los Censos de Población y Vivienda 2010 y 2020. Vienen a nivel de sección y se agregan a municipio con la misma lógica del CCPC: se suman los conteos y las tasas se calculan como `suma(numerador) / suma(denominador)`; los promedios se ponderan por su denominador.

- **2010:** 32 archivos estatales; `CLAVEGEO` de 13 dígitos; el municipio se obtiene con los dígitos `[0:2]` (entidad) y `[5:8]` (municipio). Cubre 2,447 municipios.
- **2020:** un archivo nacional de secciones con `ENTIDAD`, `MUNICIPIO` y `SECCION`. Cubre 2,468 municipios.
- **Vintage:** para cada fila se usa el censo más reciente **anterior** a la elección objetivo: 2010 para 2015 y 2018; 2020 para 2021, 2024 y 2027. Así no se usa información posterior a la elección que se quiere predecir.
- **Variables:** el set curado cubre educación, empleo, vivienda y servicios, lengua indígena, migración, limitaciones, jefatura femenina, tamaño del hogar y dependencia. El detalle y las reglas de agregación están en `docs/reports/reporte_externos.md`.
- **Limpieza:** el ECEG 2010 de Chiapas trae `GRAPROES` escalado por 100; se corrige dividiendo entre 100 y se descartan los valores resultantes mayores a 30 años. También se tratan como faltantes los valores negativos (centinela `-6` en seis secciones de 2020).
- **Cobertura:** los municipios creados después del censo quedan sin dato: 11 en 2015 y 16 en 2018 con ECEG 2010; 9 en 2024 y 9 en 2027 con ECEG 2020. En 2021 el ECEG 2020 cubre todos los municipios. Se conservan con `NaN` y una marca de cobertura; no se imputan en este paso.
- **Censos Económicos:** no se usan. Los conjuntos de datos abiertos descargados (2024, 2014 y 2000) son solo nacionales y no permiten un cruce municipal.

El cruce forma parte de las tablas canónicas `tabla_municipios_entrenamiento` y `tabla_municipios_2027`: cada una suma 31 columnas externas (`censo_fuente`, `tiene_eceg_2010`, `tiene_eceg_2020` y 28 `ext_*`). `fase3.py` hace la unión al construir las tablas; `scripts/features_externas_municipio.py` permite reconstruir el caché y actualizar las tablas existentes sin volver a correr las Fases 1 y 2. Las dos columnas de respuesta (`conocidos_objetivo` y `abstencion_objetivo`) se conservan sin cambios.

### Cosas a cuidar cuando limpiemos

- **La fecha viene escrita distinto según el año** (en 2024 el mes va primero). Para saber de qué elección es cada fila usamos el año (`AELEC`), no la fecha.
- **Algunos distritos vienen vacíos** (aparecen como un espacio en blanco): el local en varios años y el federal en 2009 y 2012. Ese vacío no debe eliminar registros ni sus conteos al unir la tabla o agregar por municipio.
- **Hay edades de hasta 140 años.** Se marcan para revisión sin borrar sus conteos y se incluyen en el grupo de 60 o más. Se conserva la edad original junto con el grupo de edad.
- **Los archivos de 2024 traen unos caracteres invisibles al inicio.** Hay que leerlos con `encoding="utf-8-sig"`; si no, el nombre de la primera columna sale mal.
- **Si una sección no tiene dato, su participación queda vacía, no en cero.** Lo mismo aplica al municipio cuando la suma de `SV + NV` es cero. Si solo algunas secciones carecen de dato, se conserva el agregado y se documenta su cobertura mediante las marcas de calidad y `NS`.

### Lo que falta verificar

- [x] Contrastar `LN`, `SV`, `NV` y `NS` de los 32 estados en las seis elecciones con el tablero oficial. *192/192 combinaciones coinciden; también los porcentajes al redondeo publicado. [Evidencia reproducible](reports/reporte_validacion_ine.md), 24/10/2026.*
- [x] Que los seis años tengan las mismas columnas. *Sí.*
- [x] Ver si hay un diccionario de datos dentro de los `.zip`. *Sí, uno por año.*
- [x] Confirmar el código de `SEXO` en 2024 contra el tablero. *El código `2` corresponde a no binario; son 105 personas.*
- [x] Saber qué municipios se pueden comparar entre elecciones y revisar los cambios de sus secciones (Fase 2). *El catálogo y el reporte documentan 46 municipios con cambios territoriales y 254 secciones que cambian de municipio; su historial reconstruido se conserva y se evalúa por separado en Fase 7.*
- [x] Contrastar con el tablero la participación de Aguascalientes con ambos sexos juntos. *Coincide en 2021 y 2024.*
- [x] Averiguar por qué 2012 casi no tiene `NS`. *El INE documenta que se excluyeron cuadernillos no disponibles. La Fase 2 identificó 1,048 secciones ausentes que reaparecen en 2015; en 66 municipios representan más del 10% de su lista. Se conserva en el historial y se evalúa una variante sin 2012 en Fase 7.*
- [ ] Conseguir contornos municipales, verificar su correspondencia con los datos y confirmar con el INE que se pueden usar.

---

## 7. Definiciones aprobadas y pendientes

**Aprobación para modelar (29/10/2026).** Azael aprobó estos valores de la propuesta de Diego para modelar; el equipo todavía puede cambiarlos. Las intervenciones también van como las propuso Diego, en dos mapas: sin y con intervención. El semáforo por terciles se implementó en la Fase 8 y sigue pendiente de ratificación; el uso definitivo del ECEG sigue pendiente.

| Definición | Regla aprobada para Fase 7 |
|---|---|
| Elección objetivo | Intermedia de 2027; regresión municipal de NV / (SV + NV) |
| Mínimo de conocidos | 500 en la respuesta de entrenamiento; sensibilidad con 100 y 1,000. Se predicen todos los municipios. `--minimo` cambia el filtro de entrenamiento |
| NS | Fuera del denominador. Sensibilidades con máximo 10%/20% y NS como no voto. Más de 50% en 2024 se marca como baja confianza |
| 2012 | Se conserva sin rellenar huecos; sensibilidad con historial sin 2012 |
| Sin respuesta | Se excluye del entrenamiento; no se inventa una observación real |
| Historial rearmado e incompleto | Se incluye, se marca y se evalúa por separado |
| Validación | Selección solo en 2015/2018, prueba temporal en 2021 y prueba adicional dejando estados completos fuera. 2024 es secundaria, con tolerancia pre-registrada de 0.3 puntos |
| Calibración | Recta robusta sobre la distancia municipal con predicciones fuera de fold: 2015/2018 para A y B, 2015/2018/2021 para C y las cuatro fotos para la corrida final |
| ECEG | Bloque candidato; solo se retiene si mejora la selección previa a 2021. Pendiente de decisión del equipo; `--sin-censo` lo excluye |
| Modelo y pesos | Un LightGBM de distancia municipal al país, sin pesos al entrenar; comparación exclusiva contra repetir la última elección del mismo tipo |
| Nivel nacional 2027 | Publicado: tasa nacional de 2021 (48.16% redondeado). Escenarios: ±5 puntos, tendencia de las intermedias y último cambio |

**Intervenciones:** implementadas en la Fase 8 como las propuso Diego en `docs/EDA/Fase 5/fase5.md`: tres por separado (jóvenes de 18 a 34, hombres y zonas rurales), solo en los municipios rojos del escenario sin intervención y con un efecto supuesto de 10% (se prueban también 5% y 15%). Se ven en dos mapas: sin y con intervención.

**Semáforo implementado (Fase 8):** tres colores por orden, terciles de la abstención predicha sin intervención. Cortes actuales: rojo ≥ 49.318%, amarillo ≥ 36.933% y verde por debajo de ese corte; los 12 municipios sin personas con dato quedan en gris. Los cortes se fijan una sola vez y se conservan para todos los escenarios. La propuesta sigue pendiente de ratificación del equipo.

**Datos y mapa:** todos los campos del CCPC siguen disponibles y se conservan. El ECEG 2010/2020 ya preparado se prueba como bloque candidato, sin añadir otras fuentes externas; su adopción sigue pendiente del equipo. La cartografía y su entrega requieren confirmación con el INE y revisión de equivalencias territoriales. Las definiciones se mantienen sincronizadas con Fase 5 de [PLAN.md](PLAN.md).

---

## Glosario

### Términos electorales

- **CCPC:** Conteos Censales de Participación Ciudadana, la base de datos del INE que usamos.
- **DECEyEC:** Dirección Ejecutiva de Capacitación Electoral y Educación Cívica, el área del INE que lanzó el concurso.
- **Sección electoral:** la zona más pequeña en la que el INE divide el país. Un municipio tiene varias.
- **Zona del proyecto:** un municipio, identificado por estado + clave municipal. Es la unidad de predicción, escenarios, semáforo, mapas y reporte.
- **Distrito electoral federal (`DEF`):** división territorial para elegir una diputación federal por mayoría relativa. Es uno de los campos disponibles para el análisis.
- **Distrito electoral local (`DEL`):** división territorial para elegir una diputación del Congreso de la entidad por mayoría relativa. Es uno de los campos disponibles para el análisis.
- **Lista nominal:** las personas con credencial para votar vigente que pueden votar.
- **Elección intermedia:** elección federal donde no se elige presidente (en nuestros datos: 2009, 2015 y 2021).
- **Elección presidencial:** elección federal donde sí se elige presidente (2012, 2018 y 2024).
- **Abstención:** que una persona de la lista nominal no vote.
- **Regresión:** modelo que predice un valor numérico; en este proyecto, la tasa de abstención de cada municipio.
- **Etapas de vida:** los grupos de edad que usa el INE: 18 a 24, 25 a 34, 35 a 44, 45 a 59 y 60 o más.
- **Escenario:** el resultado de la predicción bajo ciertos supuestos. Sin intervención es la predicción del modelo tal cual; con intervención es esa misma predicción más el efecto supuesto.
- **Semáforo:** clasificación de las zonas en niveles de riesgo (verde, amarillo y rojo; gris si no hay personas con dato). En la Fase 8 se usan terciles por orden de la abstención predicha.
- **Reseccionamiento:** cuando el INE divide o redibuja secciones, por ejemplo porque crecieron mucho. Por eso el número de secciones cambia entre elecciones.
- **Redistritación:** cuando el INE redibuja los distritos electorales. La última fue en 2023 y se usó en 2024.
- **Casilla especial:** casilla para personas que el día de la elección están fuera de su sección. Sus votos no aparecen en el CCPC.
- **Cuadernillo:** el cuaderno de la lista nominal que hay en cada casilla, donde se marca quién votó. De ahí salen los datos del CCPC.
- **Tablero del INE:** la página interactiva del CCPC donde se consultan y descargan cifras. La usamos para comprobar que nuestras sumas coinciden con las oficiales.
- **Brecha intermedia vs presidencial:** cuánto más se abstiene una zona en las intermedias que en las presidenciales.
- **Intervención hipotética:** una acción supuesta del INE (por ejemplo, una campaña de promoción de participación en municipios priorizados). Su efecto no se puede medir con estos datos, así que lo declaramos como supuesto.

### Términos del análisis

- **LightGBM:** modelo de árboles que aprende corrigiendo errores de árboles anteriores. En Fase 7 estima la distancia municipal al país.
- **Distancia contra el país:** abstención del municipio menos la nacional de esa elección. Para 2027 se suma a un nivel nacional supuesto; no es una predicción del nivel nacional.
- **Aporte de una columna (TreeSHAP):** cuántos puntos suma o resta una variable a la salida del modelo, junto con una base. Explica asociaciones del modelo, no efectos causales de una intervención.
- **Rango empírico nominal del 80%:** margen que sale de cuánto se equivocó el modelo con cada municipio en 2021, por tamaño de municipio, sin contar lo que falló el supuesto del nivel del país. Se suma a la predicción de 2027. No garantiza que 2027 caiga dentro: solo dice cuánto nos equivocamos en 2021. Lo que no sabemos del nivel del país va aparte, en escenarios de ±5 puntos.

- **EDA (análisis exploratorio):** revisar los datos con preguntas y gráficas antes de modelar, para entender cómo se comportan.
- **Polígono (contorno):** la forma de un territorio (por ejemplo, un municipio) en un mapa. SHP, GeoJSON y GPKG son formatos de archivo que guardan contornos.
- **Punto de partida (o referencia simple):** la predicción más obvia, por ejemplo "cada municipio repetirá lo de la última elección parecida". Un modelo que no la supera no sirve.
- **Información del futuro:** cuando, sin querer, el modelo usa datos de la elección que intenta predecir o de una posterior. Los resultados se ven muy buenos, pero son falsos.
- **Cortes del semáforo:** los valores de riesgo en los que una zona pasa de un color a otro (por ejemplo, de verde a amarillo).

---

## Fase final opcional: aplicación web para presentar los mapas

Esta fase llega **solo después** de terminar todo lo de datos, análisis, modelo y escenarios, cuando ya toca "pintar" los resultados.

### Qué es obligatorio y qué es opcional

**Obligatorio.** Se entrega siempre lo que pide la convocatoria, haya o no aplicación (ver la sección 4).

**Opcional.** La aplicación web. La convocatoria no la pide. Sirve para presentar mejor los resultados y para mostrar que el INE podría usar la herramienta, pero **no sustituye ningún entregable**.

### Qué se podría hacer

Una página web que muestre los **dos mapas** de la sección 3, con su leyenda y una ventana con los datos de cada zona, y que permita cambiar de un mapa a otro. Conviene que se puedan ver lado a lado, para comparar el antes y el después.

Tendría dos partes: un servidor que entrega los resultados ya calculados (backend, con FastAPI) y la página que pinta los mapas (frontend). La aplicación solo **muestra** resultados; no vuelve a correr el modelo.

Si el tiempo no alcanza, hay una versión más sencilla: una página que lee los resultados de un archivo, sin servidor. Y el plan B que la propia convocatoria acepta es un tablero en Power BI o Tableau.

### Reglas para esta fase

1. **No se empieza hasta tener listo el mínimo obligatorio** (reporte, mapas de escenario y base).
2. **Si el tiempo aprieta, se descarta.** No debe poner en riesgo ningún entregable.
3. **Solo datos agregados**, nunca datos de personas.
4. **Mostrar el riesgo por municipio**, con su leyenda y marcas de calidad. El mapa representa predicciones municipales; no se requieren vistas de riesgo por distrito o sección.
5. **Si la mencionamos en el reporte,** debe quedar disponible mientras dure la evaluación, o incluir capturas en la presentación.

### Cómo empezar sin frenar el análisis

Quien haga la aplicación puede avanzar con datos de ejemplo. La tabla de escenarios es el acuerdo entre quien analiza y quien construye la interfaz: `ai/artifacts/fase8/escenarios_municipio.parquet` (una fila por municipio) y `escenarios_detalle.csv` (una fila por municipio, intervención y efecto). Sus columnas:

- Identificador de la zona (`EDOCVE` + `MPIOCVE`), estado y municipio
- Marcas de calidad y comparabilidad de los datos de participación
- Riesgo y semáforo sin intervención: la abstención predicha, su rango y la participación (100% menos la abstención)
- Riesgo y semáforo con intervención, uno por cada intervención de la Fase 5, con su reducción en puntos y el cambio de color
- Diferencia entre ambos (cuántos puntos sube la participación al intervenir)
- Brecha intermedia vs presidencial (abstención en intermedias menos abstención en presidenciales)
- Lista nominal (para mostrar el tamaño de la zona)
- Participación de cada elección de 2009 a 2024, total y por grupos de edad, sexo y tipo de sección
- Lo que más pesa en la predicción: las columnas que más la suben o la bajan
