## Plan de trabajo: datos, análisis y modelo

Este plan dice qué hacemos en cada fase, qué sale de ahí y cuándo se puede pasar a la siguiente. Si la condición no se cumple, nos quedamos en esa fase.

**Objetivo definido:** predecir mediante regresión la tasa de abstención por municipio. **Ya definimos que una zona del proyecto es un municipio.** Todos los campos de los archivos del CCPC del INE están disponibles para el análisis y la preparación de variables; no se incorporan fuentes externas. Los registros por sección son el insumo para construir los agregados municipales. Siguen pendientes las demás definiciones y la aprobación de la Fase 5 para modelar.

**Trabajo inmediato:** la Fase 1 de carga y limpieza descrita abajo. La comparabilidad territorial y la tabla municipal corresponden a las fases siguientes.

| Fase | Qué hacemos | Qué sale de ahí |
|---|---|---|
| **1. Carga y limpieza** | Juntar los archivos de las seis elecciones en una sola tabla limpia | Tabla única y reporte de calidad |
| **2. Consistencia entre años** | Comprobar la comparabilidad de los municipios y la asignación de sus secciones entre elecciones | Lista de municipios comparables y reporte de cambios |
| **3. Tabla de análisis** | Resumir los datos por municipio y elección | Tabla de análisis y diccionario de datos |
| **4. Análisis exploratorio** | Responder preguntas concretas sobre cómo se comporta la participación | Hallazgos con su cifra |
| **5. Definiciones** | Completar elección objetivo, semáforo e intervención a partir del objetivo de regresión municipal ya definido | Definiciones actualizadas en este plan y en `reto_y_datos.md` |
| **6. Mapas** | Conseguir los contornos municipales y unirlos a nuestra tabla | Mapa con los datos |
| **7. Modelo** | Construir y probar el modelo que estima el riesgo | Modelo, resultados de las pruebas y predicciones |
| **8. Escenarios y semáforo** | Correr los dos escenarios y clasificar las zonas | Riesgo de cada zona con y sin intervención |

**La Fase 6 no espera a la 5.** Conseguir los mapas depende del INE y puede tardar, y sin ellos no hay entregable. Se piden desde el inicio y se trabaja en paralelo.

**Sobre las cifras que ya aparecen aquí:** antes de empezar se hizo una revisión rápida de los datos, solo para corroborar lo que dice la documentación. Esa revisión no sustituye ninguna fase: sus cifras son preliminares y cada fase hace su propio trabajo.

---

### Fase 1. Carga y limpieza

**Para qué:** tener una sola tabla con las seis elecciones en la que podamos confiar.

**Qué se hace:**

1. Leer los 192 archivos (32 estados por 6 elecciones) y juntarlos en una tabla.
2. Poner todo en el mismo formato: mismos nombres y mismos códigos (por ejemplo, de sexo y de tipo de sección), conservando todas las columnas originales.
3. Agrupar las edades en las etapas de vida del INE: 18 a 24, 25 a 34, 35 a 44, 45 a 59 y 60 o más, conservando también `EDAD` original.
4. Buscar errores: filas repetidas, números negativos o filas donde no cuadre la regla `LN = SV + NV + NS`.
5. **Las filas raras se marcan, no se borran.** Cada caso se anota para decidir después.
6. Guardar la tabla y escribir un reporte de calidad con lo que se encontró.

Los detalles que el código tiene que cuidar (fechas, campos vacíos y codificación) están en [reto_y_datos.md](reto_y_datos.md#cosas-a-cuidar-cuando-limpiemos).

**Qué sale:** tabla única de todos los años y `reporte_calidad.md`.

**Se pasa cuando:** todos los años tienen la misma estructura y no hay filas que fallen la regla sin explicación.

---

### Fase 2. Consistencia entre años

Esta es la fase más importante. Si falla, todo lo demás falla.

**Para qué:** saber qué historial municipal se puede comparar. Hay que revisar municipios nuevos, cambios de clave o límites y cambios en la asignación de sus secciones. El INE divide y redibuja secciones con el tiempo: en 2009 había 64,934 y en 2024 hay 70,751. Una sección nueva no implica por sí sola que el municipio carezca de historial; hay que comprobar que el agregado siga representando el mismo territorio.

**Qué se hace:**

1. Ver qué secciones aparecen, desaparecen o cambian entre elecciones. La revisión rápida indica que unas 2,775 secciones de 2024 son nuevas.
2. Revisar la asignación de secciones a municipios y las altas, bajas o cambios de claves y límites municipales. No asumir que una misma clave representa siempre el mismo territorio; documentar las correspondencias verificadas y marcar los casos no comparables. Un cambio de distrito, por sí solo, no invalida la comparación municipal si el territorio del municipio se conserva.
3. Medir cómo afecta a las comparaciones la exclusión de cuadernillos no disponibles en 2012, documentada por el INE.
4. Conciliar los conteos incluyendo todos los registros originales, sin filtrar por edad, sexo o tipo de sección.
5. **Comparar con las cifras oficiales:** sumar nuestros datos por estado y año y compararlos con el tablero del INE. Una persona del equipo exporta esas cifras del tablero.

**Qué sale:** reporte de consistencia, clasificación de municipios (con historial comparable, nuevos, con cambios territoriales y sin dato en algún año) y registro de cambios de sus secciones.

**Se pasa cuando:** nuestros totales coinciden con el tablero y sabemos qué municipios no se pueden comparar y por qué. Si algún total no cuadra, se busca la causa antes de seguir.

---

### Fase 3. Tabla de análisis

**Para qué:** tener la tabla con la que se hace todo lo demás.

Una fila por municipio y por elección, identificada por `EDOCVE` + `MPIOCVE` + `AELEC`, con:

- Cuántas personas había en la lista, cuántas votaron, cuántas no y de cuántas no se sabe.
- Participación y abstención, calculadas sumando primero y dividiendo después (nunca promediando porcentajes de secciones). Si la suma de `SV + NV` del municipio es cero, ambas quedan vacías, no en cero.
- Clave y nombre del estado y municipio, año y tipo de elección.
- Composición de la lista nominal por edad y sexo, y proporciones en secciones urbanas, rurales y mixtas.
- Información de secciones y distritos, cuya representación municipal se documentará sin asignar un distrito único cuando el municipio abarque varios.
- Indicadores de participación derivados de los conteos del CCPC, como la proporción de `NS` y, cuando haya historial comparable, tasas anteriores y brecha entre intermedias y presidenciales.
- Las marcas de la Fase 2 y marcas para municipios con pocos casos conocidos o muchos no especificados.

**Qué sale:** tabla de análisis y diccionario de datos (cada variable con su nombre, qué significa y de dónde sale).

Todos los campos originales están disponibles para construir esta tabla y preparar variables. La forma de resumirlos o codificarlos se documenta en el diccionario; la selección de predictores se evalúa después del EDA, respetando la disponibilidad temporal de los datos.

**Se pasa cuando:** los totales de esta tabla coinciden con los de la Fase 2.

---

### Fase 4. Análisis exploratorio

Antes de modelar, revisamos las tablas de la Fase 3 con estas preguntas (también se le dice EDA). Cada respuesta lleva su cifra o gráfica y la decisión que apoya.

Tablas: **base** = `municipio_eleccion` y **entrenamiento** = `tabla_municipios_entrenamiento`. Sus columnas se explican en `docs/reports/diccionario_datos.md`.

| # | Qué buscar | Dónde verlo | Para decidir |
|---|---|---|---|
| 1 | ¿El municipio que se abstuvo mucho en una intermedia lo vuelve a hacer en la siguiente? | Entrenamiento: `abst_ultima_intermedia` contra `abstencion_objetivo` (fotos 2015 y 2021) | Cuánto ayuda el historial y qué tan difícil es ganarle al punto de partida |
| 2 | ¿Cuánto más se abstienen en intermedias que en presidenciales? ¿Pasa igual en todos los municipios? | Entrenamiento: `brecha_intermedia_presidencial` | El mapa de brecha y si el tipo de elección entra al modelo |
| 3 | ¿Cuánto se mueve el país entre intermedias? (participación de 44.1%, 47.1% y 51.8%) | Entrenamiento: `abst_ultima_intermedia_vs_pais` | Si el semáforo se corta por nivel (%) o por orden (los más altos) |
| 4 | ¿Qué grupos se abstienen más: jóvenes, hombres, rurales…? | Base: `abst_18_24` … `abst_rural` | A quién dirigir la intervención |
| 5 | ¿Qué rasgos de la lista nominal van con más abstención? | Entrenamiento: `pct_18_24` … `pct_rural`, `ln_ultima`, `n_def` | Qué columnas entran al modelo y cuáles sobran (por ejemplo, edad promedio o % de 60 o más) |
| 6 | ¿Desde cuántas personas con dato el porcentaje deja de brincar? | Base: `conocidos` y el cambio entre elecciones | El mínimo de casos por municipio |
| 7 | ¿Dónde y cuándo hay mucho NS? | Base: `pct_ns` por estado y elección | Si hay estados o años poco confiables y qué hacer con NS |
| 8 | ¿Cuánto se nota el hueco de 2012? | Entrenamiento: `pct_hueco_2012`; base: 2012 contra 2009 y 2015 | Si 2012 entra al historial |
| 9 | ¿Los municipios sin dato o con historial rearmado se comportan distinto? | Base: `conocidos` = 0; entrenamiento: `historial_rearmado`, `historial_incompleto` | Si se quedan en el entrenamiento |
| 10 | ¿Los municipios vecinos se parecen? (cuando haya mapa) | Polígonos de la Fase 6 | Cómo probar el modelo (dejar estados fuera) |

**Qué sale:** `reporte_eda.md` con las respuestas; cada cifra dice qué código la produjo.

**Se pasa cuando:** las 10 preguntas tienen respuesta.

---

### Fase 5. Definiciones (decide el equipo)

Con lo que mostró el análisis exploratorio, el equipo decide y lo deja por escrito:

- **Zona:** municipio para el modelo, los escenarios, el semáforo, los mapas y el reporte, acordado por el equipo. La sección se conserva como insumo de agregación y validación.
- **Datos:** todos los campos de los archivos del CCPC del INE están disponibles para el análisis y la preparación de variables, sin fuentes externas. Falta evaluar la selección y representación de predictores después del EDA.
- **Objetivo del modelo:** regresión de la tasa de abstención municipal, ya definido. La tasa se calcula desde los conteos sumados por municipio. La clasificación del riesgo se construye a partir de la predicción; sus niveles y cortes se deciden en el semáforo.
- **Elección objetivo:** propuesta, la intermedia de 2027.
- **Semáforo:** cuántos colores y dónde va cada corte (por nivel de abstención o por orden de los municipios). Se fija con el escenario sin intervención y es el mismo para todas las intervenciones.
- **Intervenciones:** de 3 a 4, una por grupo (por ejemplo, jóvenes, hombres, zonas rurales o personas de 60 o más). Para cada una se decide qué acción es, a quién va, dónde se aplica y cuánto efecto se supone (por ejemplo, convencer al 10% de los que no iban a votar). La pregunta 4 del EDA dice qué grupos conviene elegir.
- **Mínimo de casos conocidos por municipio** para tomarlo en cuenta.
- **Municipios sin historial, con cambios territoriales o sin dato:** cómo tratarlos y cómo evaluar la cobertura de sus secciones.
- **Los no especificados:** propuesta, dejarlos fuera (como el INE) y probar qué pasa si no. Incluye qué hacer con 2012, según lo que salga de la Fase 2.

**Qué sale:** las definiciones y sus motivos quedan en esta fase del plan y en la sección 7 de `reto_y_datos.md`, manteniendo ambos documentos sincronizados.

**Se pasa cuando:** el equipo lo aprueba. **No se modela antes de esto.**

---

### Fase 6. Mapas

**Para qué:** sin mapa no hay entregable.

**Se usan los datos de los archivos del CCPC del INE, sin incorporar fuentes externas al análisis.** Los polígonos solo sirven para dibujar los mapas; no entran al modelo.

Esta fase empieza desde el inicio, en paralelo con las demás.

**Polígonos:** la división política municipal 2022 del INEGI, publicada por CONABIO ([metadatos y descarga](http://geoportal.conabio.gob.mx/metadatos/doc/html/mun22gw.html), acceso libre). Trae 2,475 municipios vigentes a diciembre de 2022, con sus claves (`CVE_ENT`, `CVE_MUN`) y nombres (`NOMGEO`).

**Qué se hace:**

1. Descargar los polígonos y revisar dos cosas:
   - **Las claves son del INEGI, no del INE.** Puebla, por ejemplo, es la 114 en el INEGI y la 115 en el CCPC. Hay que armar una tabla de equivalencias entre ambas y revisarla.
   - **Nuestra tabla de 2027 tiene 2,477 municipios y el mapa 2,475.** Faltan Eldorado y Juan José Ríos (Sinaloa), creados después de 2022; en el mapa su territorio sigue dentro de los municipios de los que salieron. Hay que decidir cómo mostrarlos.
2. Unirlos con nuestra tabla usando la tabla de equivalencias y contar cuántos municipios no encuentran su pareja.
3. Presentar los escenarios y el semáforo por municipio. Usar información de distritos para preparar variables no cambia la unidad de predicción ni requiere un mapa de riesgo distrital.

**Qué sale:** archivo de mapa municipal con nuestros datos y lista de municipios que no se pudieron unir.

**Se pasa cuando:** sabemos qué porcentaje de municipios se puede mapear y qué hacemos con los que no.

---

### Fase 7. Modelo

**Qué se predice:** la abstención de cada municipio en la intermedia de 2027, como un porcentaje. Con ese porcentaje se pone el color del semáforo (Fase 5).

**Con qué tablas** (salen de la Fase 3; sus columnas están en `docs/reports/diccionario_datos.md`):

| Tabla | Qué es | Para qué |
|---|---|---|
| `tabla_municipios_entrenamiento` | Cada fila es un municipio en una foto (2015, 2018, 2021 o 2024): lo que se sabía antes de esa elección y, al final, la abstención que hubo | El modelo aprende aquí |
| `tabla_municipios_2027` | Una fila por municipio con lo que se sabe hasta 2024 y la abstención de 2027 vacía | El modelo la llena |

Si el EDA (Fase 4) propone columnas nuevas, se agregan a las dos tablas por igual antes de entrenar.

**Cómo, paso a paso:**

1. **Punto de partida:** predecir que cada municipio repite su última elección del mismo tipo (para 2027, `abst_ultima_intermedia`). Cualquier modelo tiene que ganarle.
2. **Un solo modelo:** un modelo de regresión potente, de los que aprenden con ejemplos que ya traen la respuesta (aprendizaje supervisado). Cuál exactamente se propone al empezar esta fase.
3. **Prueba en el pasado (la que más pesa):** se entrena solo con las fotos de 2015 y 2018 y se predice la de 2021, que es intermedia como 2027. Luego se compara con lo que de verdad pasó.
4. **Prueba por estados:** se dejan fuera estados completos al entrenar y luego se predicen, para ver si funciona en zonas que no vio.
5. **Modelo final:** si pasa las dos pruebas, se entrena con todas las fotos (2015 a 2024) y se llena `tabla_municipios_2027`.
6. **Qué tan bien le atina:** cuántos puntos se equivoca en promedio, si ordena bien a los municipios de más a menos abstención y cuántos pone en el color correcto del semáforo.
7. **Por qué predice lo que predice:** qué columnas empujan la abstención hacia arriba o hacia abajo.
8. **Un rango, no solo un número:** por ejemplo, 52% (entre 48% y 56%).

**Reglas:**
- **Nada del futuro:** cada foto solo trae elecciones anteriores a la que predice; las tablas ya vienen así. Si se cuela un dato posterior, el modelo parece mejor de lo que es.
- Las filas sin respuesta (municipios sin dato en esa elección) no se usan para entrenar.
- Los municipios con pocas personas con dato se tratan según el mínimo que decida la Fase 5.

**Limitación que hay que declarar:** solo hay seis elecciones y el nivel del país en las intermedias cambia mucho. Probablemente el modelo atine mejor al orden de los municipios que al porcentaje exacto.

**Qué sale:** el modelo guardado, los resultados de las pruebas y `tabla_municipios_2027` con la abstención predicha y su rango (en `ai/artifacts/`).

**Se pasa cuando:** el modelo le gana al punto de partida en las dos pruebas. Si no, se dice así y se usa el punto de partida.

---

### Fase 8. Escenarios y semáforo

**Sin intervención:** es la abstención que predice el modelo para 2027 (Fase 7). No es "un mundo sin INE": los datos ya incluyen lo que el INE hizo hasta 2024.

**Con intervención:** a esa misma predicción se le resta el efecto supuesto. No se entrena otro modelo.

> Lo que baja la abstención = efecto × parte de la lista que es del grupo × abstención del grupo

Ejemplo: si una campaña convence al 10% de los jóvenes de 18 a 34 que no iban a votar, en Puebla la abstención baja unos 2.5 puntos (con sus datos de 2021).

**Qué se hace:**

1. Poner a cada municipio su color del semáforo **sin intervención**.
2. Calcular cada intervención de la Fase 5 sobre una copia de `tabla_municipios_2027`.
3. Usar **los mismos cortes** del semáforo para ver qué municipios cambian de color.
4. Probar tres tamaños de efecto (por ejemplo, 5%, 10% y 20%).
5. Comparar: qué intervención saca más municipios del rojo y dónde rinde más cada una.

**Se pasa cuando:** cada municipio tiene su abstención y su color sin intervención y con cada intervención.

> **Importante:** el efecto de una intervención no se puede medir con estos datos. Es un supuesto, y así se dice en el reporte.

---

### Reglas para todas las fases

1. **Ninguna cifra se inventa:** todo número del reporte sale de un resultado guardado.
2. **Solo datos resumidos por zona**, nunca datos de personas.
3. **El modelo se tiene que poder explicar:** qué columnas empujan la abstención hacia arriba o hacia abajo.
4. **Cada decisión se anota** (qué se decidió y por qué).
5. **Todo se puede repetir:** el código corre de principio a fin y da los mismos resultados.
