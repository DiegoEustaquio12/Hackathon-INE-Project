# Reporte de fuentes externas sociodemográficas

Fuente: **ECEG (Entorno para la Construcción de Escenarios Geoelectorales)** del INEGI,
Censos de Población y Vivienda 2010 y 2020. Los datos originales están por sección;
aquí se agregan a municipio y se incorporan a las tablas canónicas de la Fase 3.

## Regla de vintage

Cada fila usa el censo más reciente **anterior** a su elección objetivo:

- 2015 y 2018: ECEG 2010.
- 2021, 2024 y 2027: ECEG 2020.

Así no se usa información posterior a la elección que se quiere predecir. La columna
`censo_fuente` indica qué censo se usó en cada fila.

## Agregación

- Los conteos se suman por municipio.
- Las tasas se calculan como `suma(numerador) / suma(denominador)`.
- Los promedios se ponderan: `GRAPROES` por `P_15YMAS` y `PROM_OCUP` por `VIVPAR_HAB`.
- Las tasas de vivienda usan `VIVPAR_HAB` en 2010 y `VIVPARH_CV` en 2020, el universo
  de las variables `VPH_*` (viviendas con características captadas).
- Los valores negativos (el centinela `-6` de 6 secciones de 2020) se tratan como faltantes.
- En el ECEG 2010 de Chiapas (07), `GRAPROES` viene escalado por 100; se divide entre 100.
- Los valores de `GRAPROES` mayores a 30 años se tratan como faltantes.
- Un denominador en cero produce `NaN`, no cero.

## Features

| Variable | Definición | Fórmula |
|---|---|---|
| `ext_pct_analfabeta` | Población de 15 años y más analfabeta | `P15YM_AN / P_15YMAS` |
| `ext_pct_sin_escolaridad` | Población de 15 años y más sin escolaridad | `P15YM_SE / P_15YMAS` |
| `ext_escolaridad_promedio` | Grado promedio de escolaridad (ponderado por población de 15+) | `suma(GRAPROES × P_15YMAS) / suma(P_15YMAS)` |
| `ext_pct_primaria_incompleta` | Población de 15 años y más con primaria incompleta | `P15PRI_IN / P_15YMAS` |
| `ext_pct_secundaria_incompleta` | Población de 15 años y más con secundaria incompleta | `P15SEC_IN / P_15YMAS` |
| `ext_pct_posbasica` | Población de 18 años y más con educación posbásica | `P18YM_PB / P_18YMAS` |
| `ext_tasa_participacion` | Población de 12 años y más económicamente activa | `PEA / P_12YMAS` |
| `ext_tasa_desocupacion` | Población de 12 años y más desocupada | `PDESOCUP / PEA` |
| `ext_tasa_participacion_femenina` | Mujeres de 12 años y más económicamente activas | `PEA_F / P_12YMAS_F` |
| `ext_tasa_ocupacion` | Población de 12 años y más ocupada | `POCUPADA / PEA` |
| `ext_pct_sin_electricidad` | Viviendas habitadas sin energía eléctrica | `VPH_S_ELEC / VIVPAR_HAB*` |
| `ext_pct_sin_agua_entubada` | Viviendas habitadas sin agua entubada en la vivienda | `VPH_AGUAFV / VIVPAR_HAB*` |
| `ext_pct_sin_drenaje` | Viviendas habitadas sin drenaje | `VPH_NODREN / VIVPAR_HAB*` |
| `ext_pct_piso_tierra` | Viviendas habitadas con piso de tierra | `VPH_PISOTI / VIVPAR_HAB*` |
| `ext_pct_con_internet` | Viviendas habitadas con internet | `VPH_INTER / VIVPAR_HAB*` |
| `ext_pct_con_computadora` | Viviendas habitadas con computadora, laptop o tablet | `VPH_PC / VIVPAR_HAB*` |
| `ext_pct_con_celular` | Viviendas habitadas con teléfono celular | `VPH_CEL / VIVPAR_HAB*` |
| `ext_pct_con_refrigerador` | Viviendas habitadas con refrigerador | `VPH_REFRI / VIVPAR_HAB*` |
| `ext_pct_con_automovil` | Viviendas habitadas con automóvil o camioneta | `VPH_AUTOM / VIVPAR_HAB*` |
| `ext_promedio_ocupantes` | Promedio de ocupantes por vivienda (ponderado) | `suma(PROM_OCUP × VIVPAR_HAB) / suma(VIVPAR_HAB)` |
| `ext_pct_limitacion_visual` | Población con limitación para ver, aun usando lentes | `PCLIM_VIS / POBTOT` |
| `ext_pct_limitacion_motriz` | Población con limitación para vestirse, bañarse o comer | `PCLIM_MOT2 / POBTOT` |
| `ext_pct_lengua_indigena` | Población de 3 años y más que habla alguna lengua indígena | `P3YM_HLI / P_3YMAS` |
| `ext_pct_nacido_otra_entidad` | Población nacida en otra entidad | `PNACOE / POBTOT` |
| `ext_pct_jefatura_femenina` | Población en hogares con persona de referencia mujer | `PHOGJEF_F / POBHOG` |
| `ext_promedio_hogar` | Promedio de personas por hogar censal | `POBHOG / TOTHOG` |
| `ext_razon_dependencia` | Razón de dependencia demográfica | `(POB0_14 + POB65_MAS) / POB15_64` |
| `ext_relacion_hombres_mujeres` | Hombres por cada mujer | `POBMAS / POBFEM` |

\* En 2020 el denominador es `VIVPARH_CV` (viviendas con características captadas).

## Cobertura

| Tabla | Elección | Filas | Municipios | Censo | Con dato del censo | Sin dato |
|---|---:|---:|---:|---:|---:|---:|
| entrenamiento | 2015 | 2,458 | 2,458 | 2010 | 2,447 | 11 |
| entrenamiento | 2018 | 2,463 | 2,463 | 2010 | 2,447 | 16 |
| entrenamiento | 2021 | 2,468 | 2,468 | 2020 | 2,468 | 0 |
| entrenamiento | 2024 | 2,477 | 2,477 | 2020 | 2,468 | 9 |
| 2027 | 2027 | 2,477 | 2,477 | 2020 | 2,468 | 9 |

### Municipios sin dato del censo elegido

- **2015:** 11 municipios: `04011`, `07112`, `07113`, `07114`, `07115`, `07116`, `07117`, `07118`, `23009`, `23010`, `23011`
- **2018:** 16 municipios: `04011`, `07112`, `07113`, `07114`, `07115`, `07116`, `07117`, `07118`, `07120`, `07121`, `07122`, `07123`, `07124`, `23009`, `23010` … (+1)
- **2021:** sin faltantes.
- **2024:** 9 municipios: `02006`, `02007`, `12082`, `12083`, `12084`, `12085`, `17036`, `25019`, `25020`
- **2027:** 9 municipios: `02006`, `02007`, `12082`, `12083`, `12084`, `12085`, `17036`, `25019`, `25020`

Los municipios sin dato son, en su mayoría, municipios creados después del censo.
Se conservan con `NaN` y `tiene_eceg_2010 = 0` o `tiene_eceg_2020 = 0`; no se imputan
en este paso. La decisión de imputar o mapear a un municipio padre corresponde al modelo.

## Validaciones

- Se conservaron todas las filas y el orden de las tablas canónicas.
- Las columnas originales y las dos columnas de respuesta (`conocidos_objetivo` y
  `abstencion_objetivo`) no cambiaron. En 2027 la respuesta sigue vacía.
- La llave `EDOCVE + MPIOCVE` de las fuentes externas es única.
- Ningún `censo_fuente` es posterior a `eleccion_objetivo`.
- Los valores negativos de la fuente se trataron como faltantes y no se sumaron.
- Se corrigió la escala de `GRAPROES` en Chiapas y se descartaron valores mayores a 30 años.
- Todas las tasas y porcentajes quedaron en [0, 1].

## Censos Económicos

No se usan. Los conjuntos de datos abiertos descargados (2024, 2014 y 2000) son solo
nacionales: no traen desagregación municipal y no permiten el cruce por `EDOCVE + MPIOCVE`.

## Archivos generados

- `data/interim/externos/eceg_2010_municipio.parquet`
- `data/interim/externos/eceg_2020_municipio.parquet`
- `data/processed/tabla_municipios_entrenamiento.parquet` y `.csv`
- `data/processed/tabla_municipios_2027.parquet` y `.csv`

## Reproducir

```bash
python scripts/features_externas_municipio.py
```

`fase3.py` integra estas mismas features cuando se corre el pipeline completo. Este
script es idempotente: si las tablas ya tienen las columnas `ext_*`, las reemplaza.
