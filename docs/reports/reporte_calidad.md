# Reporte de calidad (Fase 1)

Generado por `ai/src/data_prep/carga_limpieza.py`. Las cifras son las de esta corrida.

- Archivos CSV leídos: **192** (se esperan 192: 32 estados por 6 elecciones)
- Archivos con encabezados distintos a los 16 esperados: **ninguno**

## Totales por elección
| año | tipo | archivos | filas | secciones | ln | sv | nv | ns | participacion_pct | ns_pct_de_ln |
|---|---|---|---|---|---|---|---|---|---|---|
| 2009 | intermedia | 32 | 8,706,843 | 64,934 | 77,481,831 | 33,316,974 | 42,298,963 | 1,865,894 | 44.06 | 2.41 |
| 2012 | presidencial | 32 | 8,604,456 | 65,599 | 76,490,962 | 47,383,154 | 28,939,159 | 168,649 | 62.08 | 0.22 |
| 2015 | intermedia | 32 | 9,106,059 | 68,362 | 83,563,462 | 36,926,612 | 41,517,874 | 5,118,976 | 47.07 | 6.13 |
| 2018 | presidencial | 32 | 9,251,122 | 68,408 | 89,123,997 | 51,784,399 | 31,249,856 | 6,089,742 | 62.37 | 6.83 |
| 2021 | intermedia | 32 | 9,430,502 | 68,812 | 93,532,133 | 46,389,189 | 43,099,624 | 4,043,320 | 51.84 | 4.32 |
| 2024 | presidencial | 32 | 9,773,730 | 70,751 | 98,330,348 | 54,899,228 | 37,105,466 | 6,325,654 | 59.67 | 6.43 |


Participación = SV / (SV + NV). `ns_pct_de_ln` = NS / LN. Para cada estado y año se espera 1 archivo por estado (32 por año).
## Marcas de calidad
| anio | falla_regla_ln | negativos | filas_edad_mayor_90 | edad_maxima | dto_federal_vacio | dto_local_vacio | sexo_no_0_ni_1 |
|---|---|---|---|---|---|---|---|
| 2009 | 0 | 0 | 271,633 | 130 | 28,477 | 28,477 | 0 |
| 2012 | 0 | 0 | 175,445 | 132 | 15,677 | 15,677 | 0 |
| 2015 | 0 | 0 | 227,486 | 117 | 0 | 0 | 0 |
| 2018 | 0 | 0 | 258,762 | 137 | 0 | 0 | 0 |
| 2021 | 0 | 0 | 282,879 | 139 | 0 | 0 | 0 |
| 2024 | 0 | 0 | 294,440 | 140 | 0 | 20,912 | 105 |

## Grupos duplicados (año + estado + sección + sexo + edad)
Ninguno.

## Secciones sin dato (SV + NV = 0): su participación es vacía, no cero
| anio | secciones_sin_dato |
|---|---|
| 2009 | 1,004 |
| 2012 | 82 |
| 2015 | 2,042 |
| 2018 | 2,517 |
| 2021 | 1,693 |
| 2024 | 2,100 |

## Estado con más no especificados por año
| anio | estado | ns_pct_de_ln |
|---|---|---|
| 2009 | AGUASCALIENTES | 10 |
| 2012 | YUCATAN | 2 |
| 2015 | QUINTANA ROO | 18.55 |
| 2018 | SINALOA | 16.89 |
| 2021 | CHIHUAHUA | 12.75 |
| 2024 | CHIHUAHUA | 14.92 |

## Filas por tipo de sección
| anio | tipo_sec | filas |
|---|---|---|
| 2009 | M | 802,990 |
| 2009 | R | 2,487,887 |
| 2009 | U | 5,415,966 |
| 2012 | M | 822,843 |
| 2012 | R | 2,332,505 |
| 2012 | U | 5,449,108 |
| 2015 | M | 865,402 |
| 2015 | R | 2,413,166 |
| 2015 | U | 5,827,491 |
| 2018 | M | 899,994 |
| 2018 | R | 2,430,287 |
| 2018 | U | 5,920,841 |
| 2021 | M | 919,109 |
| 2021 | R | 2,437,152 |
| 2021 | U | 6,074,241 |
| 2024 | M | 921,814 |
| 2024 | R | 2,483,182 |
| 2024 | U | 6,368,734 |
