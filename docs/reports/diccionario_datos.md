# Diccionario de datos — Fase 3

Generado por `python -m ai.src.data_prep.build_analisis`.

## 1. `data/processed/tabla_analisis.parquet`
Una fila por `(anio_eleccion, EDOCVE, SECCION)`. Agregación a nivel de sección electoral (años 2009–2024).

| Columna | Definición | Fuente | Año | Transformación |
|---|---|---|---|---|
| `anio_eleccion` | Año de la elección | `AELEC` | 2009–2024 | Copiado |
| `tipo_eleccion` | `intermedia` o `presidencial` | `AELEC` | 2009–2024 | Mapeo (2009/15/21 intermedia, 12/18/24 presidencial) |
| `EDOCVE`, `entidad`/`EDONOM` | Estado (clave y nombre) | `EDOCVE`, `EDONOM` | 2009–2024 | Primera ocurrencia por sección/año |
| `MPIOCVE`, `MPIONOM`, `municipio` | Municipio | `MPIOCVE`, `MPIONOM` | 2009–2024 | Primera ocurrencia por sección/año |
| `SECCION` | Sección electoral | `SECCION` | 2009–2024 | Llave |
| `TIPOSEC` | Tipo U/M/R | `TIPOSEC` | 2009–2024 | Primera ocurrencia por sección/año (mayúsculas) |
| `DEF`, `DEL` | Distritos federal/local | `DEF`, `DEL` | 2009–2024 | Primera ocurrencia; pueden ser nulos (especialmente 2009/2012/2024) — **no se rellenan** |
| `LN` | Lista nominal | `LN` | 2009–2024 | Suma por (estado,sección) |
| `SV`, `NV`, `NS` | Sí votaron, No votaron, No especificado | `SV`,`NV`,`NS` | 2009–2024 | Suma por (estado,sección) |
| `participacion` | `SV/(SV+NV)` | Calculada | 2009–2024 | Se deja **NULL** si `SV+NV==0` (sección sin dato). Nunca promedio de porcentajes |
| `abstencion` | `NV/(SV+NV)` | Calculada | 2009–2024 | Igual regla (NULL si sin dato) |
| `tasa_ns` | `NS/LN` | Calculada | 2009–2024 | NULL si `LN==0` |
| `sin_dato` | `SV+NV==0` | Calculada | 2009–2024 | Marca |
| `filas_marcadas` | Nº de filas con alguna bandera | `flag_revision` | 2009–2024 | Suma por (estado,sección) |
| `seccion_pequena` | `LN < 100` | Calculada | 2009–2024 | **Umbral provisional** (pendiente Fase 5) |
| `ns_alto` | `tasa_ns > 0.10` | Calculada | 2009–2024 | **Umbral provisional** (pendiente Fase 5) |
| `clasificacion` | Historial | Fase 2 | 2009–2024 | `historial_completo`, `nueva`, `con_huecos`, `desaparecida` |
| `primera_eleccion`, `ultima_eleccion`, `n_anios_presente`, `presente_YYYY`, `es_nueva_2024` | Presencias | Fase 2 | 2009–2024 | Derivados |
| `cambio_municipio/tipo/distrito_federal/local`, `anio_cambio_*` | Cambios de territorio | Fase 2 | 2009–2024 | Entre años consecutivos donde existen ambas; distrito puede no ser comparable si es nulo |

## 2. `data/processed/tabla_analisis_desglose.parquet`
Una fila por `(anio_eleccion, EDOCVE, SECCION, grupo_edad, SEXO)`. Desglose de LN/SV/NV/NS por grupo de edad y sexo.

| Columna | Definición | Fuente | Año | Transformación |
|---|---|---|---|---|
| `anio_eleccion` | Año | `AELEC` | 2009–2024 | Copiado |
| `EDOCVE`, `SECCION` | Claves | Original | 2009–2024 | — |
| `grupo_edad` | Grupo INE: `18 a 24, 25 a 34, 35 a 44, 45 a 59, 60 o más` | `EDAD` | 2009–2024 | `pd.cut` con etiquetas (Fase 1) |
| `SEXO` | 0=Hombre, 1=Mujer, 2=No binario (solo 2024) | `SEXO` | 2009–2024 | Entero |
| `LN`, `SV`, `NV`, `NS` | Conteos | Original | 2009–2024 | Suma por clave |

**Notas de anonimización:** Los datos ya son agregados a nivel de sección/grupo; no contienen información individual. `data/processed/` se considera lista para entrega (como indica README).

**Notas metodológicas:** Participación/abstención se calculan **sumando primero** (total de SV/NV por sección/año), nunca promediando porcentajes de subgrupos. Los umbrales `seccion_pequena` y `ns_alto` son provisionales y se revisan en Fase 5.
