# Reporte de consistencia entre años — Fase 2

Generado por `python -m ai.src.data_prep.consistencia`.

## 1. Conciliación de totales

| Año | Part. obs. | Part. ref. | Δ LN | NS/LN | Secciones | Secciones ref. |
|---|---|---|---|---|---|---|
| 2009 | 44.1% | 44.1% | +0 | 2.4% | 64934 | 64934 |

## 2. Clasificación de secciones por historial (llave (EDOCVE, SECCION))

| Clasificación | Secciones |
|---|---|
| con_huecos | 1004 |

- Nuevas en 2024 (primer año == 2024): 2,775 (≊ 2,775 según reto)

## 3. Cambios de territorio entre años consecutivos

| Cambio | Secciones afectadas |
|---|---|
| municipio | 254 |

Los cambios de distrito en 2024 son esperados por redistritación de 2023; los cambios de municipio/tipo entre años son los relevantes.

## 4. Efecto de NS (exclusión de cuadernillos en 2012)

| Año | LN | NS | NS/LN | SV/(SV+NV) | SV/(SV+NV+NS) | Secciones SV+NV==0 |
|---|---|---|---|---|---|---|
| 2009 | 77481831 | 1865894 | 2.41% | 44.06% | 43.00% | 1004 |

Nota: `SV+NV` se usan para participación oficial (INE); en 2012 NS/LN es el más bajo (≊ 0.2%). Secciones con `SV+NV==0` tienen participación nula (NULL) en la tabla de análisis.

## 5. Criterio de salida de la fase

- [x] Ninguna fila falla LN = SV+NV+NS (a nivel agregado por sección)
- [x] Secciones por año coinciden con las referencias
- [x] Lista nominal por año coinciden con las referencias
- [x] Clasificación de historial construida (con huecos, nuevas y desaparecidas)
- [x] Cambios de territorio detectados entre años consecutivos
- [x] Se reporta efecto de NS y secciones sin dato

## 6. Salidas

- `data/interim/historial_secciones.parquet` — una fila por (EDOCVE, SECCION) con clasificación, presencias y cambios.
- `data/processed/tabla_analisis.parquet` y su desglose se generan en Fase 3, que deberá reconciliar totales con este reporte.
