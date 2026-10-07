# Reporte de análisis exploratorio — Fase 4

Generado por `python -m ai.src.eda`.

**Pregunta 1 (brecha intermedia vs presidencial)**

- Participación nacional por año: 2009=44.1%, 2012=62.1%, 2015=47.1%, 2018=62.4%, 2021=51.8%, 2024=59.7%.
- En secciones presentes en ambas de cada par: media (pp): 2009->2012: +17.9pp, 2015->2018: +14.6pp, 2021->2024: +6.7pp; mediana (pp): 2009->2012: +18.2pp, 2015->2018: +15.6pp, 2021->2024: +7.2pp.
- Figura: `figs/fig_p1_participacion_nacional.png`.

**Decisión que ayuda a tomar:** justifica el mapa de brecha intermedia vs presidencial (mapa 4) y el uso de `tipo_eleccion` en el modelo (Fases 5–7).


**Pregunta 2 (variación entre intermedias)**
- Participación intermedias: 2009=44.1%, 2015=47.1%, 2021=51.8% (rango 7.8 pp).
- Correlación de rangos (Spearman) de abstención entre intermedias (secciones comunes): 56.9% (promedio).

**Decisión que ayuda a tomar:** el nivel cambia mucho entre intermedias (7.7 pp) → conviene usar **posición relativa** (percentiles/rangos) más que porcentaje absoluto para clasificar riesgo (Fase 5).


**Pregunta 3 (persistencia de abstención entre elecciones del mismo tipo)**
- Spearman entre pares del mismo tipo (promedio): 71.0% (rango ~+estable según magnitud).
- Persistencia de secciones en **top decil** de abstención al siguiente ciclo del mismo tipo (promedio): 51.8% permanecen en top decil.

**Decisión que ayuda a tomar:** hay persistencia moderada-alta en el orden de secciones → base razonable para “repetir lo de la última elección parecida” (punto de partida Fase 7). El orden es más predecible que el porcentaje.


**Pregunta 4 (participación por tipo, edad y sexo)**

- Participación por `TIPOSEC` (U/M/R): varía entre años; se incluye una figura comparativa.
- Participación por `grupo_edad` (nacional, agregado): crece con la edad en la mayoría de elecciones.
- Participación por `SEXO` (desglose disponible en `tabla_analisis_desglose`) es explorable vía agregados.
- Figura: `figs/fig_p4_part_por_tipo.png`.

**Decisión que ayuda a tomar:** considerar tipo de sección, grupo de edad y sexo del padrón (LN) como candidatos a variables del modelo (Fase 7).


**Pregunta 5 (estabilidad de secciones pequeñas)**
- Desviación absoluta mediana (pp) entre elecciones del mismo tipo, por rango de LN promedio:
  0-99: 9.9 pp, 100-299: 7.1 pp, 300-999: 4.6 pp, 1000-10^7: - pp.
- La variabilidad cae notablemente conforme aumenta el tamaño de la sección.

**Decisión que ayuda a tomar:** se justifica fijar un **tamaño mínimo** para incluir secciones (las < 100 LN son más volátiles). Umbral **provisional** hasta Fase 5.


**Pregunta 6 (dónde/cuándo hay más NS)**
- NS/LN nacional (%): 2009=2.4%, 2012=0.2%, 2015=6.1%, 2018=6.8%, 2021=4.3%, 2024=6.4%.
- 2012 destaca por el menor NS/LN (efecto de exclusión de cuadernillos). Secciones con `SV+NV==0` (sin dato): 2009 1004, 2012 82, 2015 2042, 2018 2517, 2021 1693, 2024 2100.
- Nota: Chihuahua tuvo 12.7% en 2021 (mencionado en reto_y_datos); el análisis confirma mayor concentración de NS en algunas entidades en ciertos años.

**Decisión que ayuda a tomar:** tener en cuenta cobertura de NS (año/entidad) y no excluir `NS` de la definición oficial; explorar sensibilidad `SV/(SV+NV+NS)` en Fase 5.


**Pregunta 7 (¿Se repiten las secciones sin dato?)**
- Para secciones sin dato en año base, la probabilidad de seguir sin dato en la siguiente elección del mismo tipo supera ligeramente la tasa base. Diferencia media (pp) ≈ +2.4 pp.

**Decisión que ayuda a tomar:** no ignorar su recurrencia; al estimar para secciones nuevas/sin dato se debe considerar persistencia (Fase 5).


**Pregunta 8 (secciones vecinas)**
- Pendiente: requiere geometría (contornos de secciones de 2023). Fase 6.

**Decisión que ayuda a tomar:** se pospone hasta contar con el mapa (polígonos de secciones).


## Notas
- Los cálculos usan participación `SV/(SV+NV)` (NS excluido), tal como el INE, y nunca promedian porcentajes entre secciones.
- Las figuras se guardan en `docs/reports/figs/`.
- Cada cifra usa el código de `eda.py` (las funciones `preg1–preg8`).
