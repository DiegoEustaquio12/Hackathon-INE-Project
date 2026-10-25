# Reporte del análisis exploratorio (Fase 4)

Aquí van las respuestas a las preguntas de la Fase 4 del plan. Cada una dice **qué encontramos**, **la cifra** y **qué decisión apoya**. Todo sale de `tabla_municipios_entrenamiento` y `municipio_eleccion`; las columnas se explican en `diccionario_datos.md`.

**Estado:** respondidas 1, 2 y 3. Pendientes 4 a 10.

**Cómo leerlo:** un *punto* es la diferencia entre dos porcentajes (de 40% a 45% son 5 puntos). "Error" es cuántos puntos se equivoca, en promedio, una predicción contra lo que de verdad pasó.

## Resumen

| # | Respuesta en una línea | Decisión que apoya |
|---|---|---|
| 1 | Los municipios con mucha abstención tienden a repetirla, pero la relación es moderada y se debilitó (r = 0.67 en 2015, 0.54 en 2021) | El punto de partida de la Fase 7 es débil en 2021 (error de 12.4 puntos): hay espacio para ganarle |
| 2 | En intermedias se abstienen 12 a 17 puntos más que en presidenciales, y eso cambia mucho de un estado a otro | `tipo_objetivo` entra al modelo; el historial presidencial sirve; un mapa de brecha sí mostraría algo |
| 3 | El país se mueve 3 a 5 puntos entre intermedias, pero la mitad de los municipios cambia de color con cualquier corte | Proponemos cortar el semáforo por orden (terciles de la predicción 2027), a decidir en la Fase 5 |

---

## Pregunta 1. ¿Quien se abstuvo mucho en una intermedia lo repite en la siguiente?

**Respuesta:** en parte. Es la base de la predicción, pero se equivoca bastante.

| | Foto 2015 | Foto 2021 |
|---|---|---|
| Municipios comparados | 2,421 | 2,458 |
| Correlación (1 sería idéntico) | 0.67 | 0.54 |
| Error de "repetir la última intermedia" | 9.5 puntos | 12.4 puntos |
| Lo mismo, dando más peso a los municipios grandes | 5.8 puntos | 8.5 puntos |

- **Los más altos bajan mucho.** Entre el cuarto de municipios con más abstención en 2015 (65.3% en promedio), la de 2021 fue 47.9%. Solo 47% de ellos siguió en el cuarto más alto. Los más bajos casi no se mueven (26.1% pasó a 28.5%).
- **No se debe a casos raros.** Quitar municipios con historial rearmado o incompleto, o con menos de 500 personas con dato, casi no cambia las cifras.
- **Cuidado:** solo hay dos fotos de intermedias, así que no sabemos si el debilitamiento es tendencia o casualidad.

**Decisión que apoya:** la Fase 7 tiene que ganarle a un error de 12.4 puntos en la foto 2021. Es un punto de partida débil, así que ganarle es factible.

![Dispersión](eda_p1_dispersion.png)

Código: `eda_p1_persistencia.py` y `eda_p1_grafica.py`.

---

## Pregunta 2. ¿Cuánto más se abstienen en intermedias que en presidenciales? ¿Pasa igual en todos lados?

**Respuesta:** mucho más, pero depende del estado. Casi nunca ocurre al revés.

| Brecha entre municipios (puntos) | Foto 2015 | Foto 2018 | Foto 2021 | Foto 2024 |
|---|---|---|---|---|
| Mediana | 17.3 | 14.6 | 15.7 | 12.1 |
| 10% de los municipios está por debajo de | 6.3 | 3.2 | 3.3 | 3.5 |
| 10% de los municipios está por encima de | 28.5 | 25.1 | 27.6 | 20.4 |
| Municipios con brecha negativa | 1.3% | 3.2% | 3.0% | 1.9% |

- **El estado pesa más que cualquier otra cosa.** Explica entre 47% y 58% de cómo varía la brecha. En la foto 2021 la mediana por estado va de 0.6 puntos (Sonora) a 26.5 (Ciudad de México). En 2024, Nuevo León tiene 2.1 y Ciudad de México 22.6.
- **Rural contra urbano casi no cambia.** En 2021 la mediana es de 17.1 puntos en municipios urbanos y de 15.0 en rurales. El tamaño del municipio casi no influye.
- **La historia presidencial ayuda a predecir.** En la foto 2021, predecir con la última intermedia explica 29% de cómo varía la abstención. Si se agrega la abstención presidencial anterior sube a 67%. En la foto 2015 pasa de 45% a 51%. Es un ajuste rápido sobre los mismos datos, no la prueba del modelo.
- **La brecha comparte cálculo con la última intermedia**, así que conviene incluir también por separado las columnas presidenciales (`abst_ultima_presidencial`, `abst_prom_presidenciales`).
- **Cuidado:** en la foto 2015 la brecha usa una sola elección de cada tipo (2009 y 2012), y 2012 tiene huecos, así que es más ruidosa. Hay 11 y 9 municipios sin brecha en las fotos 2015 y 2018.

**Decisión que apoya:**
- `tipo_objetivo` entra al modelo, porque cada tipo de elección tiene un nivel de abstención muy distinto.
- Las columnas presidenciales se quedan.
- El mapa de brecha sí mostraría algo que el mapa de abstención no, porque la brecha varía por estado.

Código: `eda_p2_brecha.py`.

---

## Pregunta 3. ¿Cuánto se mueve el país entre intermedias? ¿Semáforo por nivel o por orden?

**Respuesta:** el país se mueve entre 3 y 5 puntos, pero eso explica poco del error. Con cualquier corte, la mitad de los municipios cambia de color.

**Abstención nacional** (suma de todos los municipios):

| Elección | 2009 | 2015 | 2021 | 2012 | 2018 | 2024 |
|---|---|---|---|---|---|---|
| Tipo | intermedia | intermedia | intermedia | presidencial | presidencial | presidencial |
| Abstención | 55.9% | 52.9% | 48.2% | 37.9% | 37.6% | 40.3% |

Las intermedias bajaron 3.0 y luego 4.8 puntos. Son solo dos cambios, no alcanzan para proyectar 2027.

**¿Ayuda conocer el nivel del país?** Poco. Repetir el nivel del municipio se equivoca 9.5 y 12.4 puntos (fotos 2015 y 2021). Repetir su diferencia contra el país, conociendo el nivel del país de esa elección, se equivoca 8.7 y 11.9. El error viene sobre todo de lo que hace cada municipio por su cuenta (lo de la pregunta 1).

**Qué pasa con un semáforo de tres colores** (cortes de la elección previa):

| | Foto 2015 | Foto 2021 |
|---|---|---|
| Cambian de color, cortes fijos por nivel | 40% | 50% |
| Cambian de color, terciles por orden | 40% | 55% |
| Rojo previo que sigue en rojo (nivel / orden) | 40% / 60% | 30% / 52% |
| Rojos con cortes fijos (eran 33% antes) | 19% | 15% |
| Verde previo que pasa a rojo (nivel / orden) | 1.5% / 4.3% | 1.1% / 6.4% |

- **Por nivel** (un número fijo), los rojos se encogen cuando el país mejora: de 33% a 15% en 2021. Sirve para decir que el riesgo bajó, pero pierde discriminación.
- **Por orden** (terciles), el rojo siempre es un tercio y se mantiene más (52% sigue rojo), pero también cambia de color tanta gente como por nivel.
- **Pasar de verde a rojo es raro** en ambos casos.

**Decisión que apoya (propuesta; decide el equipo en la Fase 5):** cortar por orden, con terciles de la predicción 2027. Así el semáforo no depende de acertar el nivel nacional, que es lo que menos podemos predecir. Hay que decir en el reporte que el color es **relativo** al resto del país. Y como medio municipio cambia de color de una elección a otra, el rango de la predicción (Fase 7) importa tanto como el número.

Código: `eda_p3_nivel_pais_semaforo.py`.

---

## Preguntas pendientes

| # | Qué buscar | Tabla que falta |
|---|---|---|
| 4 | Qué grupos se abstienen más | `municipio_eleccion` |
| 5 | Qué rasgos de la lista van con más abstención | entrenamiento |
| 6 | Mínimo de personas con dato por municipio | `municipio_eleccion` |
| 7 | Dónde y cuándo hay mucho NS | `municipio_eleccion` |
| 8 | Cuánto se nota el hueco de 2012 | ambas |
| 9 | Municipios sin dato o con historial rearmado | ambas |
| 10 | Si los municipios vecinos se parecen | polígonos de la Fase 6 |

## Notas de calidad

- **30 municipios** de la foto 2021 no tienen dato de 2015, y su "última intermedia" es la de 2009. En la pregunta 3 se excluyen; en la 1 no cambia ninguna cifra.
- Salvo donde dice "dando más peso a los municipios grandes", las cifras cuentan a cada municipio igual, sin importar su tamaño.
- Los nacionales calculados coinciden con los del diccionario (55.9%, 37.9%, 52.9%, 37.6%, 48.2% y 40.3%).

## Cómo repetirlo

Con las tablas en `data/processed/`, desde la raíz del repositorio:

```
python ai/src/eda/eda_p1_persistencia.py data/processed
python ai/src/eda/eda_p2_brecha.py data/processed
python ai/src/eda/eda_p3_nivel_pais_semaforo.py data/processed
python ai/src/eda/eda_p1_grafica.py data/processed
```

Cada script imprime las cifras de este reporte.
