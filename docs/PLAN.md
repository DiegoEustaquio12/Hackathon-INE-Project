## Plan técnico: datos, análisis y modelo

Este plan cubre solo el trabajo con los datos: limpieza, análisis, modelo de ML y escenarios. Cada fase dice qué se hace, qué archivo o resultado sale de ahí y cuándo se puede pasar a la siguiente. Si la condición no se cumple, nos quedamos en esa fase.

| Fase | Qué hacemos | Qué sale de ahí |
|---|---|---|
| **1. Carga y limpieza** | Juntar los archivos de las seis elecciones en una sola tabla, con las mismas columnas y tipos | Tabla única y reporte de calidad |
| **2. Consistencia entre años** | Comprobar que las secciones y los datos se puedan comparar de un año a otro | Lista de secciones comparables |
| **3. Tabla de análisis** | Resumir por sección y año | Tabla de análisis y diccionario de datos |
| **4. Análisis exploratorio (EDA)** | Responder preguntas concretas sobre cómo se comporta la participación | Hallazgos con su cifra |
| **5. Definiciones** | Decidir zona, riesgo, elección objetivo, semáforo e intervención | Documento de decisiones |
| **6. Mapas y datos externos** | Polígonos de secciones y, si el INE lo permite, datos del Censo | Mapa unido a los datos |
| **7. Modelo de ML** | Construir y validar el modelo | Modelo, métricas y predicciones |
| **8. Escenarios y semáforo** | Correr los dos escenarios y clasificar las zonas | Riesgo de cada zona con y sin intervención |

---

### Fase 1. Carga y limpieza

**Qué se hace:**

1. Leer los archivos de los seis años con la codificación correcta (UTF-8) y los tipos de dato definidos a mano, no adivinados.
2. Comparar las columnas de cada año. Hoy solo hemos visto 2021 y 2024, y tienen las mismas 16.
3. Unificar nombres, orden y tipos.
4. Convertir `FELECCION` a fecha (mes/día/año). Para identificar la elección se usa `AELEC`, que es más seguro.
5. Pasar `TIPOSEC` a `U`, `R` y `M` (urbana, rural, mixta), sin espacios ni minúsculas.
6. Recodificar `SEXO`: `0` = hombre, `1` = mujer, `2` = no binario. Se confirma el código en cada año antes de recodificar.
7. Dejar `DEL` vacío donde venga vacío. No se rellena, y para agrupar por distrito usamos `DEF`.
8. Agrupar la edad en las **etapas de vida** que usa el INE: 18 a 24, 25 a 34, 35 a 44, 45 a 59 y 60 o más. Las edades muy altas (hay hasta 111) quedan dentro de la última etapa.
9. Revisar duplicados, valores negativos y vacíos en `LN`, `SV`, `NV` y `NS`.
10. Verificar fila por fila que **`LN = SV + NV + NS`**.
11. **Las filas raras se marcan, no se borran.** Cada caso se anota para decidir después.
12. Guardar todo en un solo archivo (Parquet) y escribir un reporte con lo que se encontró.

**Qué sale:** tabla única de todos los años y `reporte_calidad.md`.

**Se pasa cuando:** todos los años tienen la misma estructura (o documentamos qué cambió) y no hay filas que incumplan `LN = SV + NV + NS` sin explicación.

---

### Fase 2. Consistencia entre años

Esta es la fase más importante. Si falla, todo lo demás falla.

**Qué se hace:**

1. Contar cuántas secciones hay en cada año, y cuáles aparecen o desaparecen.
2. Comprobar que una misma sección tenga el mismo distrito federal, municipio y tipo en todos los años.
3. Detectar saltos raros en la lista nominal de una sección entre elecciones.
4. Confirmar el código de sexo de cada año contra el tablero del INE.
5. **Conciliar con el tablero:** sumar nuestros datos por estado y año, y compararlos con las cifras del tablero (lista nominal, sí votaron, no votaron, no especificados). Las cifras del tablero las exporta una persona del equipo (menú Descargar, "Tabla cruzada").

**Qué sale:** reporte de consistencia y lista de secciones comparables entre años.

**Se pasa cuando:** los totales coinciden con el tablero y sabemos exactamente qué secciones no se pueden comparar. Si algún total no cuadra, se busca la causa antes de seguir.

---

### Fase 3. Tabla de análisis

Una fila por sección y por elección, con:

- Lista nominal, sí votaron, no votaron y no especificados.
- **Participación** = `SV / (SV + NV)` y **abstención** = `NV / (SV + NV)`. Se calculan desde las sumas, nunca promediando porcentajes.
- Porcentaje de no especificados (`NS / LN`).
- Cómo se reparte la lista por etapa de vida y por sexo, y el índice de masculinidad.
- Tipo de sección, distrito federal y municipio.
- Una marca si la sección es muy pequeña o tiene muchos no especificados (el umbral se decide con el EDA).

**Qué sale:** tabla de análisis por sección y año, y el diccionario de datos (cada variable con su nombre, definición y fuente).

**Se pasa cuando:** los totales de esta tabla coinciden con los de la Fase 2.

---

### Fase 4. Análisis exploratorio (EDA)

Se hace con preguntas, no con gráficas al azar. Cada respuesta lleva su cifra o gráfica y dice qué decisión informa.

| Pregunta | Para qué sirve |
|---|---|
| ¿Cuánto más baja es la participación en intermedias que en presidenciales? ¿Cambia por zona? | Justifica usar el tipo de elección como variable y el mapa de brecha |
| ¿Una sección que se abstiene mucho vuelve a hacerlo en la siguiente elección? | Mide cuánto se puede predecir con el historial |
| ¿Cómo cambia la participación por tipo de sección, etapa de vida y sexo? | Elige las variables del modelo |
| ¿Cuántas secciones son muy pequeñas y qué tan inestables son sus porcentajes? | Define el tamaño mínimo y si hay que suavizar |
| ¿Cómo se reparten los no especificados por estado y año? | Decide si hay estados o años poco confiables |
| ¿Las secciones vecinas se parecen entre sí? (cuando haya mapa) | Decide si la validación debe dejar zonas enteras fuera |

**Qué sale:** `reporte_eda.md` con las respuestas, y cada cifra apunta al código que la produjo.

**Se pasa cuando:** cada pregunta tiene respuesta.

---

### Fase 5. Definiciones (decide el equipo)

Con lo que mostró el EDA, el equipo decide y lo deja por escrito:

- **Zona:** propuesta, la sección para el modelo y el distrito federal para el reporte.
- **Riesgo.** Hay tres lecturas posibles y hay que elegir una o combinarlas:
  - Abstención alta en la elección objetivo.
  - Caída de la participación respecto a la elección comparable anterior.
  - Abstención mayor a la esperada para el perfil de la zona.
- **Elección objetivo:** propuesta, la intermedia de 2027.
- **Semáforo:** cuántos niveles y cómo se fijan los cortes.
- **Intervención hipotética:** a quién va dirigida, dónde se aplica y qué efecto se supone.
- **Tamaño mínimo de sección** para tomarla en cuenta.
- **Los `NS`:** propuesta, excluirlos (como el INE) y probar qué pasa si no.

**Qué sale:** `DECISIONES.md`, con cada decisión y su motivo.

**Se pasa cuando:** el equipo lo aprueba. **No se modela antes de esto.**

---

### Fase 6. Mapas y datos externos

**Qué se hace:**

1. Conseguir los polígonos de las secciones (cartografía electoral del INE o Marco Geoestadístico de INEGI).
2. Unirlos con nuestra tabla por estado y sección, y ver cuántas secciones no cruzan.
3. Si el INE autoriza datos externos, sumar variables del Censo 2020 por sección (escolaridad, internet, población indígena, etc.). Los cortes de cartografía son distintos (CCPC: mayo de 2023; Censo geoelectoral: enero de 2021), así que hay que medir cuántas secciones no coinciden.
4. Escoger **pocas** variables externas con sentido. Con demasiadas, el modelo se confunde y se vuelve difícil de explicar.

**Qué sale:** archivo de mapa unido a los datos y lista de secciones que no cruzaron.

**Se pasa cuando:** sabemos qué porcentaje de secciones se puede mapear y qué hacemos con las que no.

---

### Fase 7. Modelo de ML

**Qué se predice:** la abstención de cada sección en una elección futura, según lo definido en la Fase 5.

**Variables del modelo (propuesta):** abstención de elecciones anteriores (la última del mismo tipo y la última de cualquier tipo), la brecha entre intermedias y presidenciales, la estructura de la lista por etapa de vida y sexo, el tipo de sección, el tamaño de la lista y, si se permiten, las variables externas.

**Regla clave: no usar información del futuro.** Para predecir una elección, el modelo solo puede ver datos de elecciones anteriores a esa. Si se cuela un dato posterior, las métricas salen infladas sin que se note.

**Qué se hace:**

1. **Referencia simple:** predecir que cada sección repetirá lo de la última elección parecida. Todo modelo debe superarla.
2. **Modelo fácil de explicar** (por ejemplo, una regresión) y **modelo más potente** (por ejemplo, boosting de árboles). Se comparan.
3. **Validación en dos formas:**
   - *En el tiempo:* con datos hasta 2018 predecir 2021, y con datos hasta 2021 predecir 2024.
   - *En el espacio:* dejar estados completos fuera del entrenamiento y ver si el modelo funciona en zonas que no vio.
4. **Métricas:** error promedio de la abstención, si ordena bien las zonas de más a menos riesgo, y cuántas zonas cae en el nivel correcto del semáforo.
5. **Explicar** qué variables empujan el riesgo y en qué dirección.
6. **Incertidumbre:** darle a cada predicción un rango y no solo un número.
7. **Elegir el modelo.** Si el potente no mejora de forma clara al simple, nos quedamos con el simple.

**Limitación que hay que declarar:** solo hay seis elecciones, de dos tipos, así que el modelo aprende de pocos puntos en el tiempo.

**Qué sale:** modelo guardado, tabla de métricas y predicciones por sección.

**Se pasa cuando:** el modelo supera la referencia simple en la validación en el tiempo y en la del espacio. Si no, se dice así y se usa el más simple.

---

### Fase 8. Escenarios y semáforo

**Qué se hace:**

1. Correr el modelo **sin intervención adicional** (las tendencias siguen igual). Esto no es "un mundo sin INE": los datos históricos ya incluyen lo que el INE hizo hasta 2024.
2. **Fijar los cortes del semáforo con este escenario** y reutilizar los mismos en el otro. Si se recalcularan en cada uno, la intervención no cambiaría ningún color.
3. Correr el escenario **con intervención**, según lo definido en la Fase 5.
4. Calcular cuánto cambia el riesgo de cada zona y sumar por distrito federal para el reporte.
5. Probar varios tamaños de efecto y ver qué tan sensibles son las conclusiones.
6. Ordenar las zonas por riesgo y por cuánto mejoran con la intervención.

**Se pasa cuando:** cada zona tiene su riesgo con y sin intervención, los cortes son los mismos en ambos y los totales cuadran con el escenario sin intervención.

> **Sobre el efecto de la intervención:** estos datos no permiten estimar el efecto real de una acción. El escenario con intervención es un **supuesto declarado**, y así debe decirse en el reporte.

---

### Reglas para todas las fases

1. **Ninguna cifra se inventa:** todo número del reporte sale de un resultado guardado.
2. **Solo datos agregados**, nunca datos de personas.
3. **Modelo simple y explicable** antes que complicado.
4. **Cada decisión se anota** (qué se decidió y por qué).
5. **Todo se puede repetir:** el código corre de principio a fin y da los mismos resultados.