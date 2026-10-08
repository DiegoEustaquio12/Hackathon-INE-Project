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

Es revisar los datos con preguntas antes de modelar (también se le dice EDA). Se hace con preguntas, no con gráficas al azar, y cada respuesta lleva su cifra o gráfica y dice qué decisión ayuda a tomar.

| Pregunta | Para qué sirve |
|---|---|
| ¿Cuánto más baja es la participación en intermedias que en presidenciales? ¿Cambia por zona? | Justifica el mapa de brecha y usar el tipo de elección en el modelo |
| ¿Cuánto cambia el nivel general entre intermedias? (en el país dieron 44.1%, 47.1% y 51.8%) | Ayuda a evaluar la precisión de la regresión y la clasificación posterior del riesgo |
| ¿Un municipio que se abstiene mucho vuelve a hacerlo en la siguiente elección? | Dice cuánto podemos predecir con el historial |
| ¿Cómo cambian la participación y la abstención de cada municipio entre elecciones comparables? | Ayuda a elegir indicadores del historial electoral para el modelo |
| ¿Cómo se relaciona la abstención con edad, sexo, tipo de sección, distritos y los demás campos disponibles? | Ayuda a preparar y evaluar variables de los archivos del INE |
| ¿Qué tan inestables son los porcentajes de municipios con pocos casos conocidos? | Define el mínimo de casos conocidos para tomar un municipio en cuenta |
| ¿Dónde y cuándo hay más no especificados? | Dice si hay estados o años poco confiables |
| ¿Los municipios sin dato o con cobertura incompleta se repiten de una elección a otra? | Define cómo tratarlos |
| ¿Los municipios vecinos se parecen entre sí? (cuando haya mapa) | Dice cómo probar el modelo |

**Qué sale:** `reporte_eda.md` con las respuestas, y cada cifra dice qué código la produjo.

**Se pasa cuando:** cada pregunta tiene respuesta.

---

### Fase 5. Definiciones (decide el equipo)

Con lo que mostró el análisis exploratorio, el equipo decide y lo deja por escrito:

- **Zona:** municipio para el modelo, los escenarios, el semáforo, los mapas y el reporte, acordado por el equipo. La sección se conserva como insumo de agregación y validación.
- **Datos:** todos los campos de los archivos del CCPC del INE están disponibles para el análisis y la preparación de variables, sin fuentes externas. Falta evaluar la selección y representación de predictores después del EDA.
- **Objetivo del modelo:** regresión de la tasa de abstención municipal, ya definido. La tasa se calcula desde los conteos sumados por municipio. La clasificación del riesgo se construye a partir de la predicción; sus niveles y cortes se deciden en el semáforo.
- **Elección objetivo:** propuesta, la intermedia de 2027.
- **Semáforo:** cuántos colores y dónde va cada corte.
- **Intervención hipotética:** a quién va dirigida, dónde se aplica y qué efecto se supone.
- **Mínimo de casos conocidos por municipio** para tomarlo en cuenta.
- **Municipios sin historial, con cambios territoriales o sin dato:** cómo tratarlos y cómo evaluar la cobertura de sus secciones.
- **Los no especificados:** propuesta, dejarlos fuera (como el INE) y probar qué pasa si no. Incluye qué hacer con 2012, según lo que salga de la Fase 2.

**Qué sale:** las definiciones y sus motivos quedan en esta fase del plan y en la sección 7 de `reto_y_datos.md`, manteniendo ambos documentos sincronizados.

**Se pasa cuando:** el equipo lo aprueba. **No se modela antes de esto.**

---

### Fase 6. Mapas

**Para qué:** sin mapa no hay entregable.

**Se usan los datos de los archivos del CCPC del INE, sin incorporar fuentes externas al análisis.** La cartografía municipal se solicita al INE como soporte para los mapas; su uso y entrega siguen pendientes de confirmación.

Esta fase empieza desde el inicio, en paralelo con las demás.

**Qué se hace:**

1. Conseguir los contornos municipales de la cartografía del INE y verificar su fecha, claves y correspondencia con la tabla del CCPC. Si se construyen a partir de polígonos de secciones, verificar su cobertura y asignación municipal antes de unirlos.
2. Unirlos con nuestra tabla mediante estado + municipio y contar cuántos municipios no encuentran su pareja.
3. Presentar los escenarios y el semáforo por municipio. Usar información de distritos para preparar variables no cambia la unidad de predicción ni requiere un mapa de riesgo distrital.

**Qué sale:** archivo de mapa municipal con nuestros datos y lista de municipios que no se pudieron unir.

**Se pasa cuando:** sabemos qué porcentaje de municipios se puede mapear y qué hacemos con los que no.

---

### Fase 7. Modelo

**Qué se predice:** la tasa de abstención de cada municipio en la elección objetivo, mediante regresión. Después se clasifica el riesgo con los cortes del semáforo acordados en la Fase 5.

**Con qué datos:** todos los campos de los archivos del CCPC del INE están disponibles para preparar variables municipales. Esto incluye el historial de participación, edad, sexo, tipo de sección, distritos, tamaño de la lista y los demás campos del archivo. Su agregación, codificación y selección se documentan y evalúan después del EDA; no se incorporan fuentes externas.

**Regla clave: no hacer trampa con el futuro.** Para predecir una elección, el modelo solo puede usar elecciones anteriores a esa. Si se cuela un dato posterior, el modelo parece mejor de lo que es.

**Qué se hace:**

1. **Punto de partida:** suponer que cada municipio repetirá lo de su última elección parecida, usando únicamente historial territorial comparable. Cualquier modelo tiene que hacerlo mejor que eso.
2. Probar un modelo sencillo de explicar y uno más potente. Si el potente no es claramente mejor, nos quedamos con el sencillo.
3. **Probarlo como si estuviéramos en el pasado:** con datos hasta 2018, predecir 2021 y comparar con lo que de verdad pasó. Como 2027 es intermedia, esta es la prueba que más pesa. También se prueba dejando estados fuera, para ver si funciona en zonas que no vio.
4. Medir qué tan cerca queda de la abstención real, si ordena bien las zonas de más a menos riesgo y cuántas pone en el color correcto del semáforo.
5. Explicar qué empuja el riesgo hacia arriba o hacia abajo.
6. Darle a cada predicción un rango, no solo un número.

**Limitación que hay que declarar:** solo hay seis elecciones, de dos tipos, y el nivel general de las intermedias cambia mucho. Probablemente el modelo acierte mejor el orden de las zonas que el porcentaje exacto.

**Qué sale:** modelo guardado, resultados de las pruebas y predicciones por municipio.

**Se pasa cuando:** el modelo le gana al punto de partida en las dos pruebas. Si no, se dice así y se usa el más simple.

---

### Fase 8. Escenarios y semáforo

**Qué se hace:**

1. Correr el modelo **sin intervención adicional** (las tendencias siguen igual). Esto no es "un mundo sin INE": los datos históricos ya incluyen lo que el INE hizo hasta 2024.
2. **Fijar los cortes del semáforo con este escenario** y usar los mismos en el otro. Si se recalcularan en cada uno, la intervención no cambiaría ningún color.
3. Correr el escenario **con intervención**, según lo definido en la Fase 5.
4. Calcular cuánto cambia el riesgo de cada municipio y presentar los resultados municipales en el reporte.
5. Probar varios tamaños de efecto y ver si las conclusiones se sostienen.
6. Ordenar las zonas por riesgo y por cuánto mejoran con la intervención.

**Se pasa cuando:** cada zona tiene su riesgo con y sin intervención, y los cortes son los mismos en ambos.

> **Sobre el efecto de la intervención:** estos datos no permiten medir el efecto real de una acción. El escenario con intervención es un **supuesto declarado**, y así debe decirse en el reporte.

---

### Reglas para todas las fases

1. **Ninguna cifra se inventa:** todo número del reporte sale de un resultado guardado.
2. **Solo datos resumidos por zona**, nunca datos de personas.
3. **Modelo simple y explicable** antes que complicado.
4. **Cada decisión se anota** (qué se decidió y por qué).
5. **Todo se puede repetir:** el código corre de principio a fin y da los mismos resultados.
