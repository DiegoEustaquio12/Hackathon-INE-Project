# Propuesta de lenguaje para presentar el análisis exploratorio

Esta propuesta no modifica `reporte_eda.md`. La versión actual es accesible en gran parte, pero mezcla explicaciones cotidianas, nombres de columnas y términos estadísticos. Para una presentación conviene abrir cada pregunta con el hallazgo y su consecuencia, dejando las fórmulas y los identificadores de código en las referencias.

| Expresión actual | Propuesta para la presentación | Motivo |
| --- | --- | --- |
| EDA | Análisis exploratorio de datos; después, análisis exploratorio | Explicar la sigla la primera vez. |
| Foto 2021 | Evaluación de la elección de 2021 con información previa | Aclarar que no se trata de una fotografía ni de datos disponibles en 2027. |
| Lista nominal | Personas registradas para votar (lista nominal) | Conservar el nombre oficial y explicar su significado. |
| Conocidos / con dato | Personas cuyo registro permite saber si votaron | Evitar confundirlo con personas conocidas por el equipo. |
| NS | Registros sin información sobre si la persona votó | No confundirlos con votos nulos ni con personas que no votaron. |
| Historial rearmado | Historial reconstruido para considerar cambios de territorio municipal | Explicar por qué se recalcula el pasado. |
| Historial incompleto | Historial al que le faltan secciones por asignar | No confundirlo con cualquier dato faltante. |
| Brecha intermedia–presidencial | Diferencia de abstención entre elecciones sin y con elección presidencial | Definir primero los dos tipos de elección. |
| Mediana | Valor central: la mitad de los municipios queda por debajo y la otra mitad por encima | Conservar “mediana” en la nota técnica. |
| Terciles | Tres grupos del mismo tamaño, ordenados por abstención estimada | Explicar que el color expresa una posición relativa. Los empates pueden impedir grupos exactamente iguales. |
| Correlación / r | Qué tanto se relacionan los valores entre municipios | Conservar la cifra y explicar que no mide igualdad ni causalidad. |
| Error / MAE | Diferencia absoluta promedio entre lo estimado y lo observado, en puntos porcentuales | Distinguir error promedio, porcentaje y cambio real entre elecciones. |
| Cortes fijos | Límites de porcentaje que separan los colores | Permitir que el público entienda cómo se asigna el semáforo. |
| Pierde discriminación | Distingue menos a los municipios con mayor abstención respecto al resto | Evitar el significado social de “discriminación”. |
| `tipo_objetivo`, `abst_ultima_presidencial` | Tipo de elección y abstención presidencial anterior | Mantener los nombres de código en la documentación para reproducir el cálculo. |

## Ajustes de precisión que acompañarían el cambio de términos

- **“Correlación (1 sería idéntico)”**: cambiar por “Relación lineal entre municipios (de −1 a 1)”. Una correlación de 1 puede darse aunque todos los valores aumenten en la misma cantidad o cambien de escala; no significa abstención idéntica.
- **“El estado pesa más que cualquier otra cosa”**: cambiar por “Hay diferencias importantes entre estados; esta agrupación explica entre 47% y 58% de la variación observada”. No se compararon todas las posibles explicaciones y el cálculo no prueba una causa.
- **“Ganarle es factible”**: cambiar por “El futuro modelo deberá superar este error de referencia”. Todavía no se entrenó ni se evaluó ese modelo.
- **“La historia presidencial ayuda a predecir”**: cambiar por “Añadir el historial presidencial mejora el ajuste exploratorio sobre estos mismos datos”. El aumento de ajuste de la pregunta 2 no es una prueba de predicción en elecciones no vistas.
- **“¿Ayuda conocer el nivel del país?”**: aclarar que la pregunta 3 utiliza el nivel nacional ya observado de la elección objetivo. El ejercicio ilustra un límite de la explicación nacional, pero no es una predicción realizable antes de esa elección.
- **“Con cualquier corte, la mitad…”**: cambiar por “Con los dos esquemas de clasificación estudiados, cambia de color entre 40% y 55% de los municipios”. El análisis no ensayó todos los cortes posibles.
- **“Los más altos bajan mucho”**: cambiar por “En la comparación 2015–2021, el grupo que tenía mayor abstención en 2015 presenta una reducción importante”. No convertir una comparación histórica en una regla para el futuro.
- **“La mitad de los municipios cambia de color”**: aclarar que son clasificaciones calculadas con tasas históricas observadas. El acierto del semáforo basado en predicciones todavía debe evaluarse.

## Cómo presentaría las nuevas preguntas

Cada pregunta tendría una respuesta breve, una gráfica o tabla con unidades, una consecuencia propuesta y una limitación concreta. Por ejemplo: “Los vecinos presentan tasas parecidas, incluso descontando el promedio estatal. Por eso, la evaluación del modelo debe separar zonas geográficas completas”. El índice de Moran y la prueba de reordenamientos quedarían en una nota de respaldo.

Las relaciones entre características de municipios no se presentarían como comportamientos individuales. Tampoco se usaría un número mínimo de personas como garantía automática de calidad, ni se atribuiría a una campaña un efecto que estos datos no han medido.
