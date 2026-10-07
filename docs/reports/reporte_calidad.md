# Reporte de calidad — Fase 1 (carga y limpieza)

Generado por `python -m ai.src.data_prep.build_interim` sobre los CSV de `data/raw/`.
Elecciones procesadas: 2009, 2012, 2015, 2018, 2021, 2024.

Regla del plan: **las filas raras se marcan, no se borran.** Todo lo de este
reporte son conteos de filas que quedaron en la tabla con sus banderas `flag_*`.

## 1. Estructura

| Elección | Archivos | Filas | Secciones | Columnas | FELECCION (no se usa) |
|---|---|---|---|---|---|
| 2009 | 32 | 8,706,843 | 64,934 | 16 | 5/7/2009 |
| 2012 | 32 | 8,604,456 | 65,599 | 16 | 1/7/2012 |
| 2015 | 32 | 9,106,059 | 68,362 | 16 | 7/6/2015 |
| 2018 | 32 | 9,251,122 | 68,408 | 16 | 1/7/2018 |
| 2021 | 32 | 9,430,502 | 68,812 | 16 | 6/6/2021 |
| 2024 | 32 | 9,773,730 | 70,751 | 16 | 06/02/2024 |

Todas las elecciones traen las mismas 16 columnas en el mismo orden. El campo
`FELECCION` cambia de formato entre años (en 2024 el mes va primero), por eso
la identificación de la elección usa `AELEC` y `FELECCION` solo queda como
referencia.

## 2. Códigos de sexo y tipo de sección

| Elección | SEXO (personas por código) | TIPOSEC (filas por código) | LN con SEXO=2 |
|---|---|---|---|
| 2009 | 0=4,319,232, 1=4,387,611 | U=5,415,966, M=802,990, R=2,487,887 | — |
| 2012 | 0=4,261,802, 1=4,342,654 | U=5,449,108, M=822,843, R=2,332,505 | — |
| 2015 | 0=4,505,049, 1=4,601,010 | U=5,827,491, M=865,402, R=2,413,166 | — |
| 2018 | 0=4,572,091, 1=4,679,031 | U=5,920,841, M=899,994, R=2,430,287 | — |
| 2021 | 0=4,652,658, 1=4,777,844 | U=6,074,241, M=919,109, R=2,437,152 | — |
| 2024 | 0=4,817,367, 1=4,956,258, 2=105 | U=6,368,734, M=921,814, R=2,483,182 | 105 |

`SEXO=2` (no binario) solo aparece en 2024, como dice el diccionario de ese año.
La suma de su lista nominal es 105 personas,
que es la cifra que el tablero del INE reporta para ese código.
`TIPOSEC` usa siempre `U`, `M` y `R`.

## 3. Distritos vacíos (se dejan vacíos, no se rellenan)

| Elección | DEF vacío (filas) | DEL vacío (filas) | % filas |
|---|---|---|---|
| 2009 | 28,477 | 28,477 | 0.3% |
| 2012 | 15,677 | 15,677 | 0.2% |
| 2015 | 0 | 0 | 0.0% |
| 2018 | 0 | 0 | 0.0% |
| 2021 | 0 | 0 | 0.0% |
| 2024 | 0 | 20,912 | 0.0% |

## 4. Edades

| Elección | Edad mín. | Edad máx. | Filas de más de 100 años | Filas marcadas (fuera de 18–120) |
|---|---|---|---|---|
| 2009 | 18 | 130 | 32,761 | 212 |
| 2012 | 18 | 132 | 10,318 | 52 |
| 2015 | 18 | 117 | 12,123 | 0 |
| 2018 | 18 | 137 | 10,320 | 51 |
| 2021 | 18 | 139 | 13,216 | 38 |
| 2024 | 18 | 140 | 12,891 | 18 |

Las edades muy altas (personas fallecidas que siguen en la lista) se quedan en
el grupo `60 o más`. La cola de 101 a 110 años es continua y plausible, así que
la bandera `flag_edad` solo marca lo que no puede ser: edades fuera de 18–120
(incluidas las vacías). La Fase 3 decide si excluye esas filas. No hay edades
menores de 18.

### Rangos observados (sirven para detectar desbordes de tipo de dato)

| Columna | 2009 | 2012 | 2015 | 2018 | 2021 | 2024 |
|---|---|---|---|---|---|---|
| EDOCVE | 1 … 32 | 1 … 32 | 1 … 32 | 1 … 32 | 1 … 32 | 1 … 32 |
| MPIOCVE | 1 … 570 | 1 … 570 | 1 … 570 | 1 … 570 | 1 … 570 | 1 … 570 |
| SECCION | 1 … 6,183 | 1 … 6,393 | 1 … 6,498 | 1 … 6,517 | 1 … 9,004 | 1 … 6,922 |
| EDAD | 18 … 130 | 18 … 132 | 18 … 117 | 18 … 137 | 18 … 139 | 18 … 140 |
| LN | 1 … 969 | 1 … 550 | 1 … 506 | 1 … 982 | 1 … 452 | 1 … 550 |
| SV | 0 … 424 | 0 … 310 | 0 … 282 | 0 … 415 | 0 … 200 | 0 … 237 |
| NV | 0 … 459 | 0 … 332 | 0 … 419 | 0 … 603 | 0 … 400 | 0 … 354 |
| NS | 0 … 149 | 0 … 102 | 0 … 259 | 0 … 166 | 0 … 112 | 0 … 179 |

## 5. Reglas de calidad

| Elección | Regla LN | Negativos | Duplicados | Códigos | Llave vacía | Filas marcadas |
|---|---|---|---|---|---|---|
| 2009 | 0 | 0 | 0 | 0 | 0 | 212 |
| 2012 | 0 | 0 | 0 | 0 | 0 | 52 |
| 2015 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2018 | 0 | 0 | 0 | 0 | 0 | 51 |
| 2021 | 0 | 0 | 0 | 0 | 0 | 38 |
| 2024 | 0 | 0 | 0 | 0 | 0 | 18 |

Filas marcadas en total: 371 de 54,872,712
(0.0007%).

### Muestras de los casos raros

Ninguna fila cayó en estas tres reglas.

## 6. Totales nacionales contra la revisión de `docs/reto_y_datos.md`

| Elección | Secciones | Ref. | Δ | Lista nominal | Ref. | Δ | Participación | Ref. |
|---|---|---|---|---|---|---|---|---|
| 2009 | 64,934 | 64,934 | 0 | 77,481,831 | 77,481,831 | 0 | 44.1% | 44.1% |
| 2012 | 65,599 | 65,599 | 0 | 76,490,962 | 76,490,962 | 0 | 62.1% | 62.1% |
| 2015 | 68,362 | 68,362 | 0 | 83,563,462 | 83,563,462 | 0 | 47.1% | 47.1% |
| 2018 | 68,408 | 68,408 | 0 | 89,123,997 | 89,123,997 | 0 | 62.4% | 62.4% |
| 2021 | 68,812 | 68,812 | 0 | 93,532,133 | 93,532,133 | 0 | 51.8% | 51.8% |
| 2024 | 70,751 | 70,751 | 0 | 98,330,348 | 98,330,348 | 0 | 59.7% | 59.7% |

La revisión previa es preliminar; las columnas Δ deben ser 0 o explicarse.

## 7. Cruce puntual: Aguascalientes (el mismo que ya se contrastó con el tablero)

| Elección | LN | Ref. | SV | Ref. | Participación | Ref. |
|---|---|---|---|---|---|---|
| 2021 | 1,017,420 | 1,017,420 | 489,469 | 489,469 | 49.5% | 49.5% |
| 2024 | 1,097,171 | 1,097,171 | 626,084 | 626,084 | 58.7% | 58.7% |

## 8. Criterio de salida de la fase

- [x] Los seis años se leyeron con las mismas 16 columnas y 32 archivos
- [x] Ninguna fila falla la regla LN = SV + NV + NS
- [x] Secciones por año coinciden con la revisión de docs/reto_y_datos.md
- [x] Lista nominal por año coincide con la revisión de docs/reto_y_datos.md

## Qué sigue

Con esta tabla se entra a la **Fase 2 (consistencia entre años)**: ver qué
secciones aparecen, desaparecen o cambian de territorio entre elecciones.
