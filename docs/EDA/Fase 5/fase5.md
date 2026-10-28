### Fase 5. Definiciones (Propuesta)

**Estado:** propuesto, pendiente de aprobación del equipo. No se modela antes de esto.

Las cifras salen de `reporte_eda.md` (la pregunta del EDA va entre paréntesis).

| # | Decisión | Definición | Motivo |
|---|---|---|---|
| 1 | **Zona** | Municipio, para el modelo, los escenarios, el semáforo, los mapas y el reporte. La sección se conserva como insumo de agregación y validación. | Acordado por el equipo. Las tablas de la Fase 3 ya están a nivel municipio. |
| 2 | **Riesgo** | Nivel de abstención municipal. No se mide como abstención por encima de lo esperado. | Decisión ya tomada. |
| 3 | **Datos** | Todos los campos del CCPC, más los ECEG 2010 y 2020 del INEGI. Para cada fila se usa el censo más reciente anterior a la elección: 2010 para 2012, 2015 y 2018; 2020 para 2021, 2024 y 2027. No se usan los Censos Económicos (los datos abiertos son solo nacionales). Los ECEG entran como bloque candidato: la Fase 7 compara el modelo con y sin ellos. Se evita duplicar información entre predictores (edad promedio y proporción de 60 o más tienen correlación cercana a 0.98; los porcentajes por edad y por tipo de sección suman uno) (P5). | La composición de la lista tiene relaciones débiles con la abstención (P5), así que conviene probar si el censo aporta más. Las filas de 2015 y 2018 usan un censo de 2010, y debe decirse en el reporte. |
| 4 | **Objetivo del modelo** | Regresión de la tasa de abstención municipal, calculada desde los conteos sumados por municipio: NV / (SV + NV). | Ya definido. |
| 5 | **Elección objetivo** | Intermedia de 2027. | Solo hay dos fotos de intermedias (P1), así que el nivel nacional de 2027 es incierto; el reporte lo dice. |
| 6 | **Semáforo** | 3 colores, cortados por orden: terciles de la predicción 2027 sin intervención. Los cortes se fijan una vez en ese escenario y se usan iguales en todas las intervenciones. El color es relativo al resto del país, y cada predicción se acompaña de su rango. | P3: por orden el rojo se mantiene más (52% de los rojos previos sigue en rojo en 2021) y no depende de acertar el nivel nacional. Aun así, entre 40% y 55% de los municipios cambia de color entre elecciones. |
| 7 | **Intervenciones** | Tres, cada una por separado: jóvenes de 18 a 34, hombres y zonas rurales (detalle abajo). | P4: los jóvenes y los hombres concentran más abstencionistas. Rural cubre el criterio territorial, con regla provisional. |
| 8 | **Mínimo de casos** | Regla base: 500 personas con dato de voto por municipio. Sensibilidad con 100 y 1,000. Los casos pequeños siguen visibles. | P6: no existe un mínimo universal. Con 500 se excluyen 70 municipios (0.03% de las personas); con 1,000, 176. |
| 9 | **Sin historial, reconstruidos o sin dato** | Los 73 registros municipio-elección sin respuesta conocida se excluyen del entrenamiento y salen en gris ("sin clasificar") en el mapa. Los municipios con historial reconstruido se conservan y se evalúan por separado. Se reporta qué porcentaje de la lista nominal queda cubierto. No se imputan. | P9: los reconstruidos tienen más error de referencia (por ejemplo 14.7 y 19.5 puntos en 2021, contra 12.4), pero son pocos casos (de 5 a 35 por foto), así que no se justifica excluirlos. |
| 10 | **No especificados (NS)** | Se dejan fuera del cálculo, como el INE. Sensibilidad: contarlos como "no votó", y limitar a municipios con máximo 10% y 20% de NS. Los 38 municipios con más de 50% de NS en 2024 se marcan como de baja confianza. | P7: el NS nacional va de 0.22% (2012) a 6.83% (2018) y varía mucho por estado. |
| 11 | **2012** | Se conserva, marcado como incompleto. No se rellena el hueco. La Fase 7 prueba un historial alternativo sin 2012. | P8: faltan 1,048 secciones; afecta a 332 municipios, de los que 66 tienen más de 10% de su lista de 2009 en esas secciones. El efecto nacional es pequeño (0.19 puntos) pero se concentra en pocos municipios. |
| 12 | **Validación** | Además de separar por tiempo, evaluar dejando estados o bloques geográficos completos fuera del entrenamiento. | P10: los vecinos se parecen (Moran de 0.52 a 0.54 a nivel nacional; 0.29 a 0.31 dentro del estado). Una división municipal aleatoria saldría demasiado optimista. |

#### Detalle de las intervenciones

Cada intervención se corre por separado: los grupos se traslapan, así que sus efectos no se suman.

| | Jóvenes de 18 a 34 | Hombres | Zonas rurales |
|---|---|---|---|
| **Acción (ejemplo hipotético)** | Campaña digital y en escuelas | Comunicación dirigida y recordatorios | Difusión y facilidades en localidades rurales |
| **A quién va** | Personas de 18 a 34 años | Hombres de la lista nominal | Personas en secciones rurales |
| **Dónde se aplica** | Solo en los municipios rojos del escenario sin intervención | Igual | Igual |
| **Efecto supuesto** | 10% de sus abstencionistas termina votando. Sensibilidad: 5% y 15% | Igual | Igual |

- **Cómo se aplica:** dentro de cada municipio rojo, una fracción *e* (10%) de los abstencionistas del grupo objetivo pasa a votar. Los municipios que no son rojos conservan su predicción. El método exacto para estimar cuántos abstencionistas del grupo hay en cada municipio se fija al construir los escenarios.
- **Por qué solo en los rojos:** el INE tiene recursos limitados; el reto busca priorizar dónde actuar. Por eso el mapa de diferencia vale cero fuera de los rojos.
- **Por qué estos grupos (P4, cifras nacionales de 2024):** 25 a 34 años tiene la mayor abstención en cinco de seis elecciones; 18 a 24 le sigue de cerca. Juntos son 17.2 millones de abstencionistas (46% del total). Los hombres son 20.0 millones (54%) y se abstienen 9.4 puntos más que las mujeres.
- **Por qué rural:** pesa menos a nivel nacional (6.4 millones, 17%), pero cubre el criterio territorial. Se justifica en el reporte como criterio distinto, no como el grupo con más abstención. "Rural" describe la sección donde vive la persona, no una característica individual.
- **Por qué no 60 o más:** es el grupo con menos abstencionistas (5.0 millones en 2024, abstención de 28.6%). Si el equipo lo quiere por equidad, puede ser una cuarta opcional.
- **Regla provisional para rural:** cuando exista la predicción 2027, contar cuántos municipios rojos tienen más de la mitad de sus abstencionistas en secciones rurales. Si son muy pocos, esta intervención se cambia por 60 o más. El cambio no afecta el semáforo, los cortes ni el efecto.
- **Aviso:** el efecto de una campaña no se puede medir con estos datos. Es un supuesto declarado, no un resultado.

**Supuestos por confirmar con el INE:** que se permiten los ECEG de INEGI (la regla general dice que no hay datos externos) y la cartografía.

**Qué sale:** estas definiciones y sus motivos, escritos aquí y en la sección 7 de `reto_y_datos.md`, manteniendo ambos documentos sincronizados.

**Se pasa cuando:** el equipo lo aprueba. No se modela antes.
