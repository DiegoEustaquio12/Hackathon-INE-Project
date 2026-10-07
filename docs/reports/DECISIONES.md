# Documento de decisiones — Fase 5

Generado con base en los hallazgos de Fases 1–4.

## 1. Zona (unidad de análisis)

- **Modelo:** Sección electoral (`EDOCVE`, `SECCION`) — es la unidad más pequeña con los datos históricos y es la que el plan propone para el modelo.
- **Reporte y mapas:** Distrito federal (mapa de 2023) — se usará para el reporte, agregando secciones de cada distrito. Esto cumple: "la sección para el modelo y el distrito federal (de 2023) para el reporte".

## 2. Elección objetivo

**Intermedia 2027**. Justificación: el reto pide anticipar riesgo para decisiones antes de la elección objetivo; es natural elegir la siguiente intermedia (2027), dado que el EDA muestra comportamiento diferenciado entre intermedias/presidenciales.

## 3. Definición de riesgo

Con base en el EDA (variación entre intermedias, persistencia de orden, brecha intermedia vs presidencial):

- **Riesgo base:** Abstención alta en la elección objetivo. Pero el nivel de intermedias varía mucho (44.1% → 47.1% → 51.8%, rango 7.8 pp), por lo que comparar contra un porcentaje fijo es poco robusto.
- **Propuesta (recomendada):** Clasificar secciones por **posición relativa** dentro de la elección objetivo (percentil/rango de `abstencion = NV/(SV+NV)`). También considerar **caída de participación** respecto a la última elección del mismo tipo, y **brecha intermedia vs presidencial** cuando corresponda.
- **Para el semáforo:** Usar **cuartiles/deciles** o cortes por percentil fijados con el **escenario sin intervención** (tal como pide el plan). De este modo los colores son comparables entre escenarios.

## 4. Semáforo (niveles y cortes)

- **Colores:** 4 niveles (muy bajo/bajo/medio/alto) o 3. Propuesta: 4 niveles con semáforo intuitivo (verde/amarillo/naranja/rojo).
- **Cortes provisionales (basados en distribución por sección, escenario sin intervención):** 
  - Riesgo **bajo**: < P25 de `abstencion` (percentil 25)
  - Riesgo **medio-bajo**: P25–P50
  - Riesgo **medio-alto**: P50–P75
  - Riesgo **alto**: > P75
- **Regla dura del plan:** los cortes se **fijan una sola vez** con el escenario sin intervención y se reutilizan idénticos en el escenario con intervención. Si se decide usar otro esquema (deciles), mantener la misma regla.

Estos cortes son **provisionales** hasta tener las predicciones de la Fase 7; se pueden afinar sin alterar la comparabilidad entre escenarios.

## 5. Tratamiento de `NS` (no especificados)

- **Recomendación:** Mantener el enfoque del INE: excluir `NS` de la participación (`SV/(SV+NV)`). Es consistente con la metodología del CCPC y con la validación hecha (totales coinciden).
- **Sensibilidad:** Probar un caso alternativo `SV/(SV+NV+NS)` (trata NS como "no votó") solo para diagnóstico (Fase 7/8) — no cambia la definición oficial, pero muestra el rango de incertidumbre. Especialmente relevante en años con mayor NS (p.ej. 2021) y por estado.
- **2012:** NS/LN muy bajo (0.22%). No se corrige forzadamente; se documenta el efecto en la comparabilidad (Fase 2). Secciones con `SV+NV==0` quedan con `participacion` y `abstencion` **NULL** (sin dato), no en 0.
- **Secciones con NS > 50%:** Marcar `ns_alto` (umbral >10% provisional; revisar en Fases 7–8) para seguimiento — no se excluyen automáticamente.

## 6. Secciones muy pequeñas

- **Umbral provisional:** Excluir o tratar con cautela las secciones con **LN < 100** para la clasificación en colores extremos. Razón: variabilidad mucho mayor de la participación entre años (EDA Fase 4, pregunta 5).
- **Aplicación:** Usar `seccion_pequena` (LN<100) como marca. En el semáforo, mostrar el valor pero quizás no priorizar por color extremo sin respaldo (intervalos más amplios/rangos por decil pueden ayudar). El umbral definitivo se confirma tras validar el modelo en Fase 7.
- **Sin dato:** `sin_dato` (`SV+NV==0`) → no se asigna riesgo numérico; se marcan como "sin dato" en mapas/tabla.

## 7. Secciones sin historial o sin dato

- **Nuevas en 2024:** ≈2,775 (Fase 2). No tienen historial completo del mismo tipo. Solución propuesta: usar **la última elección del tipo más cercano disponible** (o características de la sección: tipo U/M/R, distribución por edad/sexo del padrón, municipio, distrito) para inferir una **línea base**; evitar extrapolaciones entre tipos si hay poca evidencia.
- **Con huecos:** mantener las observaciones existentes (no imputar a lo loco); el modelo puede usar el último valor observado del mismo tipo como feature.
- **Desaparecidas (no presentes en 2024):** no entran en la predicción para 2027; se documentan.
- **Secciones sin dato en alguna elección:** no usar su porcentaje para calcular medias ponderadas entre años; en la tabla de análisis `participacion/abstencion` quedan NULL.
- **Regla práctica (punto de partida Fase 7):** “Cada sección repetirá lo de su última elección parecida” (baseline). Cualquier modelo debe **ganar** a este baseline en ordenación (Spearman) y en precisión del color del semáforo (accuracy del bucket).

## 8. Intervención hipotética

Requisitos del plan: definir **a quién va dirigida, dónde se aplica, qué efecto se supone**.

Propuesta **mínima, verificable y transparente** (ajustable en Fase 8):

- **A quién va dirigida:** Secciones con alto riesgo de abstención **según el escenario sin intervención** (color rojo/alto), con foco en secciones **U/M/R** según tipo, priorizando aquellas con mayor población potencial (`LN`) para maximizar cobertura. Alternativa: centrarse en secciones donde la **persistencia** es alta (top decil que suele mantenerse) para obtener efecto más "duradero".
- **Dónde se aplica:** Geográficamente por distrito federal (para reporte) y por sección (para modelo). Se propone aplicar **selectivamente** a un subconjunto (no a todo el país): p.ej. **top 10–20%** de secciones con mayor riesgo **o** todas las que caigan en el nivel "alto", con límite razonable.
- **Qué efecto se supone:** Un **efecto marginal** en la participación, expresado como **puntos porcentuales** (pp) sobre `participacion` (o reducción equivalente de `abstencion`), aplicado **únicamente** a las secciones objetivo. Valores a probar en Fase 8: **+1 pp, +2 pp, +3 pp** (sensibilidad). La suposición debe ser explícita: "se asume un incremento de X pp en participación si se aplica la acción". No se inventan causas, solo se cuantifica un supuesto de intervención hipotética.
- **Criterio de comparación:** Usar **los mismos cortes** fijados con el escenario sin intervención. Calcular **mapa 3 (diferencia)** y priorización por "ganancia" (secciones donde pasar a nivel inferior rinde más en términos de reducción de abstención o cobertura).

## 9. Validación del modelo (Fase 7)

- **Baseline obligatorio:** última elección del mismo tipo. Métrica clave: **Spearman** entre predicción y real (ordenación de riesgo) + **accuracy por bucket** del semáforo (¿acertamos el color?) + **MAE/RMSE** de `abstencion` (menor peso por dispersión entre intermedias).
- **Validación temporal:** predecir 2021 usando datos hasta 2018 (intermedia→intermedia), y predecir 2024 usando hasta 2021 para presidenciales? También probar dejando estados fuera (validación por grupo).
- **Rango de incertidumbre:** dar **intervalo** para cada predicción (no solo punto).
- **Solo usar datos CCPC históricos** (sin Censo, sin marginación) — coherente con lo acordado.

## 10. Notas sobre umbrales provisionales

- `seccion_pequena` = LN < 100
- `ns_alto` = tasa_ns > 10%

Ambos son **provisionales**. Se revisarán al validar el modelo (Fase 7) y confirmar con cortes del semáforo (Fase 8). Si cambian, se actualiza `DECISIONES.md` con justificación.

## 11. Checklist para pasar a Fases 6–7

- [x] Secciones clasificadas por historial (Fase 2) — sabemos qué comparar.
- [x] Tabla de análisis + desglose disponibles (Fase 3).
- [x] EDA responde las 8 preguntas con cifras (Fase 4).
- [x] Decisiones documentadas (Fase 5) — este archivo.
- [ ] Conseguir contornos de secciones 2023 (Fase 6, paralelo).
- [ ] Construir y validar modelo contra baseline (Fase 7).
- [ ] Escenarios + semáforo con cortes fijos (Fase 8).
