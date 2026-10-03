## Plan de trabajo: datos, análisis y modelo

Este plan dice qué hacemos en cada fase, qué sale de ahí y cuándo se puede pasar a la siguiente. Si la condición no se cumple, nos quedamos en esa fase.

| Fase | Qué hacemos | Qué sale de ahí |
|---|---|---|
| **1. Carga y limpieza** | Juntar los archivos de las seis elecciones en una sola tabla limpia | Tabla única y reporte de calidad |
| **2. Consistencia entre años** | Comprobar que las secciones se puedan comparar de una elección a otra | Lista de secciones comparables |
| **3. Tabla de análisis** | Resumir los datos por sección y elección | Tabla de análisis y diccionario de datos |
| **4. Análisis exploratorio** | Responder preguntas concretas sobre cómo se comporta la participación | Hallazgos con su cifra |
| **5. Definiciones** | Decidir zona, riesgo, elección objetivo, semáforo e intervención | Documento de decisiones |
| **6. Mapas** | Conseguir el contorno de las secciones y unirlo a nuestra tabla | Mapa con los datos |
| **7. Modelo** | Construir y probar el modelo que estima el riesgo | Modelo, resultados de las pruebas y predicciones |
| **8. Escenarios y semáforo** | Correr los dos escenarios y clasificar las zonas | Riesgo de cada zona con y sin intervención |

**La Fase 6 no espera a la 5.** Conseguir los mapas depende del INE y puede tardar, y sin ellos no hay entregable. Se piden desde el inicio y se trabaja en paralelo.

**Sobre las cifras que ya aparecen aquí:** antes de empezar se hizo una revisión rápida de los datos, solo para corroborar lo que dice la documentación. Esa revisión no sustituye ninguna fase: sus cifras son preliminares y cada fase hace su propio trabajo.

---

### Fase 1. Carga y limpieza

**Para qué:** tener una sola tabla con las seis elecciones en la que podamos confiar.

**Qué se hace:**

1. Leer los 192 archivos (32 estados por 6 elecciones) y juntarlos en una tabla.
2. Poner todo en el mismo formato: mismos nombres y mismos códigos (por ejemplo, de sexo y de tipo de sección).
3. Agrupar las edades en las etapas de vida del INE: 18 a 24, 25 a 34, 35 a 44, 45 a 59 y 60 o más.
4. Buscar errores: filas repetidas, números negativos o filas donde no cuadre la regla `LN = SV + NV + NS`.
5. **Las filas raras se marcan, no se borran.** Cada caso se anota para decidir después.
6. Guardar la tabla y escribir un reporte de calidad con lo que se encontró.

Los detalles que el código tiene que cuidar (fechas, campos vacíos, edades muy altas) están en [reto_y_datos.md](reto_y_datos.md#cosas-a-cuidar-cuando-limpiemos).

**Qué sale:** tabla única de todos los años y `reporte_calidad.md`.

**Se pasa cuando:** todos los años tienen la misma estructura y no hay filas que fallen la regla sin explicación.

---

### Fase 2. Consistencia entre años

Esta es la fase más importante. Si falla, todo lo demás falla.

**Para qué:** saber qué historial tiene cada sección. El INE divide y redibuja secciones con el tiempo: en 2009 había 64,934 y en 2024 hay 70,751. Una sección nueva no tiene historial, y una que cambió de territorio no se puede comparar directo con su pasado.

**Qué se hace:**

1. Ver qué secciones aparecen, desaparecen o cambian entre elecciones. La revisión rápida indica que unas 2,775 secciones de 2024 son nuevas.
2. Revisar que cada sección conserve su municipio, distrito y tipo, sabiendo que en 2024 cambió el mapa de distritos (así que ahí sí se esperan cambios).
3. Medir cómo afecta a las comparaciones la exclusión de cuadernillos no disponibles en 2012, documentada por el INE.
4. Conservar la comprobación del código de sexo de 2024 (`2` = no binario) al conciliar los totales con el tablero.
5. **Comparar con las cifras oficiales:** sumar nuestros datos por estado y año y compararlos con el tablero del INE. Una persona del equipo exporta esas cifras del tablero.

**Qué sale:** reporte de consistencia y una clasificación de las secciones: con historial completo, nuevas, con cambio de territorio y sin dato en algún año.

**Se pasa cuando:** nuestros totales coinciden con el tablero y sabemos qué secciones no se pueden comparar. Si algún total no cuadra, se busca la causa antes de seguir.

---

### Fase 3. Tabla de análisis

**Para qué:** tener la tabla con la que se hace todo lo demás.

Una fila por sección y por elección, con:

- Cuántas personas había en la lista, cuántas votaron, cuántas no y de cuántas no se sabe.
- Participación y abstención, calculadas sumando primero y dividiendo después (nunca promediando porcentajes). Si una sección no tiene dato, su participación queda vacía, no en cero.
- Cómo se reparte la lista por edad y por sexo.
- Tipo de sección, distrito y municipio.
- Las marcas de la Fase 2, y una marca para secciones muy pequeñas o con muchos no especificados.

**Qué sale:** tabla de análisis y diccionario de datos (cada variable con su nombre, qué significa y de dónde sale).

**Se pasa cuando:** los totales de esta tabla coinciden con los de la Fase 2.

---

### Fase 4. Análisis exploratorio

Es revisar los datos con preguntas antes de modelar (también se le dice EDA). Se hace con preguntas, no con gráficas al azar, y cada respuesta lleva su cifra o gráfica y dice qué decisión ayuda a tomar.

| Pregunta | Para qué sirve |
|---|---|
| ¿Cuánto más baja es la participación en intermedias que en presidenciales? ¿Cambia por zona? | Justifica el mapa de brecha y usar el tipo de elección en el modelo |
| ¿Cuánto cambia el nivel general entre intermedias? (en el país dieron 44.1%, 47.1% y 51.8%) | Decide si el riesgo se mide en porcentaje o comparando secciones entre sí |
| ¿Una sección que se abstiene mucho vuelve a hacerlo en la siguiente elección? | Dice cuánto podemos predecir con el historial |
| ¿Cómo cambia la participación por tipo de sección, edad y sexo? | Ayuda a elegir qué datos usa el modelo |
| ¿Qué tan inestables son los porcentajes de las secciones muy pequeñas? | Define el tamaño mínimo de sección |
| ¿Dónde y cuándo hay más no especificados? | Dice si hay estados o años poco confiables |
| ¿Las secciones sin dato se repiten de una elección a otra? | Dice cómo estimarlas |
| ¿Las secciones vecinas se parecen entre sí? (cuando haya mapa) | Dice cómo probar el modelo |

**Qué sale:** `reporte_eda.md` con las respuestas, y cada cifra dice qué código la produjo.

**Se pasa cuando:** cada pregunta tiene respuesta.

---

### Fase 5. Definiciones (decide el equipo)

Con lo que mostró el análisis exploratorio, el equipo decide y lo deja por escrito:

- **Zona:** propuesta, la sección para el modelo y el distrito federal (mapa de 2023) para el reporte.
- **Riesgo.** Hay tres lecturas posibles, y hay que elegir una o combinarlas:
  - Abstención alta en la elección objetivo.
  - Caída de la participación respecto a la elección parecida anterior.
  - Abstención mayor a la esperada para el tipo de zona.

  También hay que decidir si se expresa en porcentaje o comparando secciones entre sí.
- **Elección objetivo:** propuesta, la intermedia de 2027.
- **Semáforo:** cuántos colores y dónde va cada corte.
- **Intervención hipotética:** a quién va dirigida, dónde se aplica y qué efecto se supone.
- **Tamaño mínimo de sección** para tomarla en cuenta.
- **Secciones sin historial o sin dato:** qué hacer con las nuevas de 2024 y con las que no tienen dato en alguna elección.
- **Los no especificados:** propuesta, dejarlos fuera (como el INE) y probar qué pasa si no. Incluye qué hacer con 2012, según lo que salga de la Fase 2.

**Qué sale:** `DECISIONES.md`, con cada decisión y su motivo.

**Se pasa cuando:** el equipo lo aprueba. **No se modela antes de esto.**

---

### Fase 6. Mapas

**Para qué:** sin mapa no hay entregable.

**No se usan datos externos** (Censo, marginación, etc.). La única excepción probable es la cartografía, porque sin ella no se pueden entregar los mapas. *Por confirmar con el INE.*

Esta fase empieza desde el inicio, en paralelo con las demás.

**Qué se hace:**

1. Conseguir el contorno de las secciones en la versión de 2023, que es la de los datos de 2024 y la que se usará en 2027. De preferencia, de la cartografía del INE; de INEGI, solo si el INE lo acepta.
2. Unirlo con nuestra tabla y contar cuántas secciones no encuentran su pareja.
3. Armar también el mapa por distrito federal, juntando las secciones de cada distrito.

**Qué sale:** archivo de mapa con nuestros datos y lista de secciones que no se pudieron unir.

**Se pasa cuando:** sabemos qué porcentaje de secciones se puede mapear y qué hacemos con las que no.

---

### Fase 7. Modelo

**Qué se predice:** la abstención de cada sección en la elección objetivo, según lo definido en la Fase 5.

**Con qué datos (propuesta):** solo del CCPC. Cómo votó la sección antes (sobre todo en la última elección del mismo tipo), su diferencia entre intermedias y presidenciales, la edad y el sexo de su lista, si es urbana o rural, y su tamaño.

**Regla clave: no hacer trampa con el futuro.** Para predecir una elección, el modelo solo puede usar elecciones anteriores a esa. Si se cuela un dato posterior, el modelo parece mejor de lo que es.

**Qué se hace:**

1. **Punto de partida:** suponer que cada sección repetirá lo de su última elección parecida. Cualquier modelo tiene que hacerlo mejor que eso.
2. Probar un modelo sencillo de explicar y uno más potente. Si el potente no es claramente mejor, nos quedamos con el sencillo.
3. **Probarlo como si estuviéramos en el pasado:** con datos hasta 2018, predecir 2021 y comparar con lo que de verdad pasó. Como 2027 es intermedia, esta es la prueba que más pesa. También se prueba dejando estados fuera, para ver si funciona en zonas que no vio.
4. Medir qué tan cerca queda de la abstención real, si ordena bien las zonas de más a menos riesgo y cuántas pone en el color correcto del semáforo.
5. Explicar qué empuja el riesgo hacia arriba o hacia abajo.
6. Darle a cada predicción un rango, no solo un número.

**Limitación que hay que declarar:** solo hay seis elecciones, de dos tipos, y el nivel general de las intermedias cambia mucho. Probablemente el modelo acierte mejor el orden de las zonas que el porcentaje exacto.

**Qué sale:** modelo guardado, resultados de las pruebas y predicciones por sección.

**Se pasa cuando:** el modelo le gana al punto de partida en las dos pruebas. Si no, se dice así y se usa el más simple.

---

### Fase 8. Escenarios y semáforo

**Qué se hace:**

1. Correr el modelo **sin intervención adicional** (las tendencias siguen igual). Esto no es "un mundo sin INE": los datos históricos ya incluyen lo que el INE hizo hasta 2024.
2. **Fijar los cortes del semáforo con este escenario** y usar los mismos en el otro. Si se recalcularan en cada uno, la intervención no cambiaría ningún color.
3. Correr el escenario **con intervención**, según lo definido en la Fase 5.
4. Calcular cuánto cambia el riesgo de cada zona y resumirlo por distrito federal para el reporte.
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
