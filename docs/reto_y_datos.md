# Reto 2 (riesgo de abstención)

Este documento explica qué nos pide el reto, cómo vamos a resolverlo y, sobre todo, **qué contienen los datos** con los que vamos a trabajar. La idea es que todo el equipo entienda lo mismo antes de meternos al modelo.

**Fase actual:** entender los datos del CCPC.

## Fechas clave

- **Registro del equipo:** hasta el 15 de octubre de 2026.
- **Entrega del proyecto:** hasta las 23:59 del 31 de octubre de 2026, en una carpeta `.zip` enviada por correo a los contactos del INE.

---

## 1. De qué trata el reto

**Problema.** El INE tiene recursos limitados para promover la participación en las elecciones. El reto pide anticipar en qué zonas del país podría bajar la participación, para decidir dónde actuar primero.

**Herramienta que vamos a hacer.** Un modelo que usa el historial de participación de 2009 a 2024 (datos del CCPC) para estimar su **riesgo de abstención** en una elección futura. Lo calcula en dos escenarios (sin intervención y con una intervención hipotética) y compara los resultados.

**Quién la usaría.** Las áreas del INE que planean y reparten recursos de capacitación electoral y educación cívica, como la DECEyEC y las juntas locales y distritales (por confirmar).

**Qué decisión apoya.** En qué territorios concentrar acciones, y de qué tipo, antes de la elección.

## 2. Cómo funciona la herramienta

Flujo: **Datos → Modelo → Escenarios → Semáforo → Mapas → Recomendaciones**

| Pieza | Qué es |
|---|---|
| **Datos** | Una tabla donde cada fila es una zona en una elección, con su participación histórica y variables sociodemográficas del CCPC |
| **Modelo** | Calcula el riesgo de abstención de cada zona. De aquí salen todos los números |
| **Escenarios** | Dos corridas del mismo modelo. La primera sigue las tendencias históricas (sin intervención adicional). La segunda cambia una variable según un supuesto de intervención. Antes de simular hay que definir a quién va dirigida la intervención, dónde se aplica y qué efecto se espera |
| **Semáforo** | Clasifica cada zona por nivel de riesgo. Los cortes se fijan una vez con el escenario sin intervención y se usan iguales en el escenario con intervención, para que los colores sean comparables |
| **Mapas** | Muestran los resultados de cada escenario |
| **Recomendaciones** | Qué zonas priorizar y qué acción tomar, a partir de los mapas |

**Nota sobre "sin intervención":** los datos históricos ya incluyen todo lo que el INE hizo hasta 2024. Por eso este escenario no es "un mundo sin INE", sino lo que pasaría si todo sigue igual que hasta ahora.

## 3. Los mapas

| Orden | Mapa | Qué muestra | Colores | Estatus |
|---|---|---|---|---|
| 1 | Sin intervención | Riesgo de abstención por zona en la elección objetivo, si las tendencias siguen igual | Semáforo | Obligatorio |
| 2 | Con intervención | El mismo mapa, aplicando el supuesto de intervención hipotética | Semáforo (mismos cortes que el mapa 1) | Obligatorio |
| 3 | Diferencia entre escenarios | Cuánto cambia el riesgo de cada zona al intervenir, para ver dónde rinde más la acción | Escala de cambio | Propuesta del equipo |
| 4 | Brecha intermedia vs presidencial | Diferencia de abstención por zona entre elecciones intermedias y presidenciales, para ver qué zonas se desentienden más cuando no hay presidente en juego | Escala de diferencia | Propuesta del equipo |

Solo los mapas 1 y 2 los exige la convocatoria. Los mapas 3 y 4 se agregan si el modelo y los datos quedan sólidos.

## 4. Qué tenemos que entregar

**Mínimos del Reto 2 (según la convocatoria):**

- **Reporte metodológico y preventivo:** PDF de 10 a 15 cuartillas. Debe explicar las variables usadas y contener el semáforo de riesgo (clasificación de zonas por nivel de riesgo de abstención), las recomendaciones preventivas y cómo priorizar recursos.
- **Mapa de escenarios con y sin intervención:** un archivo de mapas (SHP, GeoJSON o GPKG) o un enlace a un tablero en Power BI o Tableau, junto con la base de datos anonimizada que usamos (CSV o XLSX).

**Generales (para todos los retos):** presentación de máximo 10 diapositivas, código o enlace a un repositorio, y las cartas de cesión de derechos y de decir verdad firmadas por todas las personas del equipo.

Si falta cualquier entregable mínimo, el equipo queda descalificado.

## 5. Requisitos técnicos que se desprenden de los entregables

1. **Necesitamos los mapas de las zonas.** Los formatos SHP, GeoJSON y GPKG necesitan polígonos. Los archivos del CCPC traen solo tablas (no coordenadas), así que habrá que conseguirlos de la cartografía electoral del INE o del Marco Geoestadístico de INEGI, con fecha compatible con el CCPC (mayo de 2023). *Por verificar.*
2. **Las zonas deben tener el mismo identificador en datos y mapa.** La clave de estado y sección del CCPC tiene que coincidir con la del mapa y mantenerse igual en las seis elecciones. *Por verificar.*
3. **La base que entreguemos debe ser la que usamos.** Si usamos datos de otras fuentes, también deben poder entregarse (revisar licencia). La base va agregada por zona, sin grupos muy pequeños de personas.
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

Dentro de cada `.zip` hay **un CSV por estado** (en 2024 son 32 archivos). Para consultar o comparar cifras existe también el tablero interactivo en la misma página, y su manual: https://ine.mx/wp-content/uploads/2025/06/Manual-Conteos-Censales-2009-2024.pdf

Hay otros archivos en esa página (voto anticipado 2024, prisión preventiva 2024 y Poder Judicial 2025), pero quedan fuera de nuestro análisis principal.

### ¿Qué es una fila?

**Una fila no es una persona.** Es un grupo de gente que tiene en común tres cosas: la misma **sección electoral**, el mismo **sexo** y la misma **edad**. La fila nos dice cuántas personas de ese grupo estaban en la lista para votar y cuántas votaron.

Ejemplo real (Aguascalientes 2021, sección 1, hombres de 18 años):

> Había **16** personas en la lista nominal. **13** votaron, **3** no votaron y **0** quedaron sin especificar.

### ¿Qué significa cada columna?

Los archivos tienen 16 columnas:

| Columna | Qué es |
|---|---|
| `AELEC` | Año de la elección |
| `FELECCION` | Fecha de la elección (mes/día/año) |
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

> **Sobre `SEXO`:** confirmamos que `0` es hombre y `1` es mujer comparando el archivo de Aguascalientes 2021 contra el tablero del INE (los números coinciden exactamente). En 2024 esperamos lo mismo y el código `2` es nuevo, pero **falta confirmarlo contra el tablero**.

### La regla que siempre se cumple

**`LN = SV + NV + NS`**

En Aguascalientes 2024 se cumple en todas las filas. En 2021 cuadra en los totales (falta revisarlo fila por fila).

### ¿Cómo se calculan la participación y la abstención?

Así lo define el INE y así lo vamos a hacer nosotros:

- **Participación** = `SV / (SV + NV)`
- **Abstención** = `NV / (SV + NV)`

Fíjense que **`NS` se deja fuera** del cálculo.

### ¿Qué es `NS` (no especificado)?

**No es voto nulo.** Es gente de la lista de la que **no se sabe si votó o no**, por ejemplo porque el cuadernillo (el cuaderno de la lista nominal donde se marca quién votó) no tenía marcas, no se pudo capturar o faltaba una página. Es un dato faltante.

- Estos datos **no dicen por quién votó la gente ni si el voto fue nulo**. Solo dicen si fue a votar o no.
- **Decisión propuesta: excluir `NS`**, igual que el INE. Más adelante probamos cuánto cambian los resultados si lo contamos como "no votó".
- Cuidado: el porcentaje de `NS` cambia mucho entre estados. En hombres, 2021, va de 1.4% en Colima a 12.7% en Chihuahua. Por eso la participación no es igual de confiable en todos lados.

### Ejemplo: Aguascalientes completo

Sumando todas las filas del estado:

| | 2021 (intermedia) | 2024 (presidencial) |
|---|---|---|
| Lista nominal | 1,017,420 | 1,097,171 |
| Sí votaron | 489,469 | 626,084 |
| No votaron | 499,413 | 441,222 |
| No especificado | 28,538 | 29,865 |
| **Participación** | **49.5%** | **58.7%** |

Estas cifras salen de sumar los archivos. Para hombres en 2021 ya las contrastamos con el tablero y coinciden.

Se ve la diferencia entre una elección intermedia y una presidencial: la gente participa bastante más cuando hay presidenciales.

### Niveles de análisis (estado, municipio, distrito, sección)

Como cada fila trae estado, municipio, distrito federal, distrito local y sección, podemos sumar a cualquier nivel con un `groupby`. La sección es la unidad más pequeña y todo lo demás son sumas de secciones.

```python
def agrega(df, claves):
    t = df.groupby(claves, as_index=False, dropna=False)[['LN', 'SV', 'NV', 'NS']].sum()
    t['participacion'] = t.SV / (t.SV + t.NV)
    t['abstencion'] = t.NV / (t.SV + t.NV)
    return t

estado    = agrega(df, ['EDOCVE'])
municipio = agrega(df, ['EDOCVE', 'MPIOCVE'])
dist_fed  = agrega(df, ['EDOCVE', 'DEF'])
seccion   = agrega(df, ['EDOCVE', 'SECCION'])
```

Dos cuidados:

- **Nunca promedies porcentajes de secciones.** Si una sección de 100 personas tiene 80% de participación y otra de 1,000 tiene 40%, el promedio simple da 60%, pero la participación real es 480 / 1,100 = 43.6%. Primero se suman `SV` y `NV`, y después se calcula el porcentaje.
- **`DEL` tiene vacíos.** Por eso se usa `dropna=False` al agrupar. Si no, pandas descarta esas filas sin avisar y los totales no cuadran.

Además, los niveles no están anidados entre sí (un municipio no necesariamente cae en un solo distrito), así que siempre se suma desde la sección.

### ¿Qué NO trae esta base?

- Escolaridad, ingreso o nivel de marginación.
- Si la persona es indígena o afromexicana (el tablero tiene ese filtro, pero esa variable no aparece en los archivos que revisamos).
- Mapas o coordenadas (los polígonos de las secciones hay que conseguirlos aparte).
- Voto nulo ni por quién se votó.

### Cosas a vigilar cuando limpiemos

- `DEL` viene vacío en algunas filas (en Aguascalientes 2024, 615 de 91,826).
- `FELECCION` cambia de formato entre años (`06/02/2024` contra `6/6/2021`). Para identificar la elección es más seguro usar `AELEC`.
- Hay edades hasta 111 y grupos muy pequeños en edades altas.
- El código de sexo `2` tiene solo 3 personas en Aguascalientes 2024.
- El porcentaje de `NS` varía mucho entre estados.
- Hay que revisar que una misma sección tenga el mismo distrito federal, municipio y tipo en todos los años.

### Lo que falta verificar

- [ ] Que los archivos de 2018, 2015, 2012 y 2009 tengan las mismas 16 columnas.
- [ ] Confirmar el código de `SEXO` en 2024 contra el tablero.
- [ ] Revisar que las secciones crucen bien entre años.
- [ ] Ver si hay un diccionario de datos dentro de los `.zip`.
- [ ] Contrastar con el tablero la participación de Aguascalientes con ambos sexos juntos.

---

## 7. Pendiente por decidir

Estas decisiones las tomamos después de entender los datos:

1. **¿Qué es una "zona"?** Propuesta: la sección para el modelo y el distrito federal para el reporte.
2. **¿Qué es "riesgo"?** Puede ser abstención alta, caída de participación respecto a la elección comparable, o abstención mayor a la esperada para el perfil de la zona.
3. **Elección objetivo.** Candidata natural: la intermedia de 2027.
4. **Cuántos niveles tiene el semáforo y dónde van los cortes.**
5. **La intervención hipotética:** a quién se dirige, dónde se aplica y qué efecto se supone.
6. **Tratamiento de `NS`:** propuesta de excluirlo, y probar cuánto cambia el resultado si no se excluye.
7. **Datos externos** (Censo, marginación): preguntar al INE si se pueden usar además del CCPC.

---

## Glosario

- **CCPC:** Conteos Censales de Participación Ciudadana, la base de datos del INE que usamos.
- **DECEyEC:** Dirección Ejecutiva de Capacitación Electoral y Educación Cívica, el área del INE que lanzó el concurso.
- **Sección electoral:** la zona más pequeña en la que el INE divide el país. Un municipio tiene varias.
- **Lista nominal:** las personas con credencial para votar vigente que pueden votar.
- **Elección intermedia:** elección federal donde no se elige presidente (en nuestros datos: 2009, 2015 y 2021).
- **Elección presidencial:** elección federal donde sí se elige presidente (2012, 2018 y 2024).
- **Abstención:** que una persona de la lista nominal no vote.
- **IML (índice de masculinidad en lista nominal):** hombres entre mujeres de la lista nominal, por cien. Si es 93.7, hay 93.7 hombres por cada 100 mujeres.
- **IMV (índice de masculinidad en sí votaron):** igual, pero con las personas que votaron.
- **Escenario:** una corrida del modelo bajo ciertos supuestos (por ejemplo, con o sin intervención).
- **Semáforo:** clasificación de las zonas en niveles de riesgo (por ejemplo verde, amarillo y rojo).

## Fase final opcional: aplicación web para presentar los mapas

Esta fase llega **solo después** de terminar todo lo de datos, análisis, modelo y escenarios, cuando ya toca "pintar" los resultados.

### Qué es obligatorio y qué es opcional

**Obligatorio.** Se entrega siempre lo que pide la convocatoria, haya o no aplicación:

- Reporte metodológico y preventivo (PDF de 10 a 15 cuartillas).
- Mapa de escenarios con y sin intervención (SHP, GeoJSON o GPKG, o enlace a un tablero), junto con la base de datos anonimizada.
- Presentación de máximo 10 diapositivas.
- Código o enlace al repositorio.
- Cartas de cesión de derechos y de decir verdad, firmadas por todo el equipo.

**Opcional.** La aplicación web. La convocatoria no la pide. Sirve para presentar mejor los resultados y para mostrar que el INE podría usar la herramienta, pero **no sustituye ningún entregable**.

### Qué se podría hacer

Sí es posible armar un **backend con FastAPI** y una interfaz web que muestre los mapas:

| Parte | Qué hace |
|---|---|
| **Backend (FastAPI)** | Entrega los resultados ya calculados: zonas, riesgo sin y con intervención, y la diferencia entre ambos |
| **Frontend** | Pinta los **cuatro mapas propuestos** (ver abajo), con su leyenda y una ventana con los datos de cada zona. Permite cambiar de un mapa a otro |

Como los resultados se calculan una sola vez en el análisis, la aplicación solo los **muestra**. No vuelve a correr el modelo.

### Los cuatro mapas que debe pintar

| Orden | Mapa | Colores | Datos que necesita |
|---|---|---|---|
| 1 | Sin intervención | Semáforo | Riesgo y semáforo sin intervención |
| 2 | Con intervención | Semáforo (mismos cortes que el mapa 1) | Riesgo y semáforo con intervención |
| 3 | Diferencia entre escenarios | Escala de cambio | Diferencia entre ambos escenarios |
| 4 | Brecha intermedia vs presidencial | Escala de diferencia | Abstención en intermedias menos abstención en presidenciales |

Los mapas 1 y 2 son el mapa de escenarios que exige la convocatoria. Los mapas 3 y 4 son propuestas del equipo, pero la aplicación debe poder pintar los cuatro. Conviene que el mapa 1 y el 2 se puedan ver lado a lado, para comparar el antes y el después.

El mapa 4 se calcula directamente de los datos históricos y no depende del modelo ni de la intervención.

Si el tiempo no alcanza para el backend, hay una versión más sencilla: una página estática que carga los resultados desde un archivo, sin servidor. Y el plan B que la propia convocatoria acepta es un tablero en Power BI o Tableau.

### Reglas para esta fase

1. **No se empieza hasta tener listo el mínimo obligatorio** (reporte, mapas de escenario y base).
2. **Si el tiempo aprieta, se descarta.** No debe poner en riesgo ningún entregable.
3. **Solo datos agregados**, nunca datos de personas.
4. **El mapa nacional por sección es pesado** (hay del orden de 70 mil secciones). Conviene mostrar primero el distrito federal y dejar la sección para cuando se acerca el zoom.
5. **Si la mencionamos en el reporte,** debe quedar disponible mientras dure la evaluación, o incluir capturas en la presentación.

### Cómo empezar sin frenar el análisis

Quien haga la aplicación puede avanzar con datos de ejemplo. La tabla de escenarios es el acuerdo entre quien analiza y quien construye la interfaz. Sus columnas:

- Identificador de la zona (estado + sección), estado, municipio, distrito federal y tipo de sección
- Riesgo y semáforo sin intervención
- Riesgo y semáforo con intervención
- Diferencia entre ambos
- Brecha intermedia vs presidencial (abstención en intermedias menos abstención en presidenciales)
- Lista nominal (para mostrar el tamaño de la zona)