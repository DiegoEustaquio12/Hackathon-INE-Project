# Reporte de tendencias, edades y lista nominal (Fase 2)

Generado por `ai/src/data_prep/analisis_tendencias.py`. Tablas en `data/processed/tendencias/`.

## 1. Tendencia de participación
| anio | tipo | ln | participacion_pct | abstencion_pct | ns_pct_de_ln | cambio_pp_vs_anterior | cambio_pp_vs_misma_clase | iml | imv |
|---|---|---|---|---|---|---|---|---|---|
| 2009 | intermedia | 77,481,831 | 44.06 | 55.94 | 2.41 | — | — | 93.09 | 79.67 |
| 2012 | presidencial | 76,490,962 | 62.08 | 37.92 | 0.22 | 18.02 | — | 92.82 | 81.15 |
| 2015 | intermedia | 83,563,462 | 47.07 | 52.93 | 6.13 | -15.01 | 3.01 | 92.79 | 78.28 |
| 2018 | presidencial | 89,123,997 | 62.37 | 37.63 | 6.83 | 15.29 | 0.28 | 92.87 | 81.42 |
| 2021 | intermedia | 93,532,133 | 51.84 | 48.16 | 4.32 | -10.53 | 4.76 | 92.99 | 79.76 |
| 2024 | presidencial | 98,330,348 | 59.67 | 40.33 | 6.43 | 7.83 | -2.70 | 92.41 | 78.74 |

Participación = SV / (SV + NV); `abstencion_pct` es su complemento y `ns_pct_de_ln` = NS / LN.
`cambio_pp_vs_anterior` compara con la elección anterior (sea del tipo que sea);
`cambio_pp_vs_misma_clase` compara con la elección anterior **del mismo tipo** (intermedia con intermedia,
presidencial con presidencial), que es la comparación justa.

- En elecciones **intermedias**, la participación subió de 44.1% (2009) a 51.8% (2021): +7.8 puntos.
- En elecciones **presidencials**, la participación bajó de 62.1% (2012) a 59.7% (2024): -2.4 puntos.

**Cambio por estado** entre la primera y la última elección de cada tipo:

**Intermedias: mayor aumento**

| estado | desde | hasta | cambio_pp |
|---|---|---|---|
| TLAXCALA | 2,009 | 2,021 | 29.76 |
| GUERRERO | 2,009 | 2,021 | 24.42 |
| CHIAPAS | 2,009 | 2,021 | 22.22 |
| PUEBLA | 2,009 | 2,021 | 17.85 |
| MICHOACAN | 2,009 | 2,021 | 15.58 |

**Intermedias: mayor caída**

| estado | desde | hasta | cambio_pp |
|---|---|---|---|
| SONORA | 2,009 | 2,021 | -7.73 |
| QUERETARO | 2,009 | 2,021 | -7.40 |
| COLIMA | 2,009 | 2,021 | -5.89 |
| JALISCO | 2,009 | 2,021 | -3.81 |
| GUANAJUATO | 2,009 | 2,021 | -3.43 |

**Presidencials: mayor aumento**

| estado | desde | hasta | cambio_pp |
|---|---|---|---|
| TLAXCALA | 2,012 | 2,024 | 7.02 |
| COAHUILA | 2,012 | 2,024 | 3.39 |
| MICHOACAN | 2,012 | 2,024 | 2.48 |
| PUEBLA | 2,012 | 2,024 | 2.36 |
| CHIHUAHUA | 2,012 | 2,024 | 0.19 |

**Presidencials: mayor caída**

| estado | desde | hasta | cambio_pp |
|---|---|---|---|
| TABASCO | 2,012 | 2,024 | -10.23 |
| SONORA | 2,012 | 2,024 | -7.83 |
| VERACRUZ | 2,012 | 2,024 | -7.15 |
| JALISCO | 2,012 | 2,024 | -6.83 |
| COLIMA | 2,012 | 2,024 | -5.62 |


## 2. Desfase de edades entre votantes y lista nominal
| anio | edad_media_ln | edad_media_votantes | edad_media_abstencion | edad_mediana_ln | edad_mediana_votantes | desfase_media_anios | desfase_mediana_anios |
|---|---|---|---|---|---|---|---|
| 2009 | 41.02 | 43.12 | 39.37 | 38 | 41 | 2.10 | 3 |
| 2012 | 40.82 | 42.22 | 38.53 | 38 | 40 | 1.40 | 2 |
| 2015 | 41.44 | 44.08 | 39.14 | 39 | 43 | 2.64 | 4 |
| 2018 | 42.07 | 43.40 | 39.89 | 40 | 42 | 1.33 | 2 |
| 2021 | 42.67 | 45.09 | 40.09 | 40 | 44 | 2.42 | 4 |
| 2024 | 43.23 | 45.46 | 39.98 | 41 | 44 | 2.23 | 3 |

`desfase_*` = edad de quienes votaron menos edad de la lista nominal. Si es **positivo**, votan personas más
grandes que el promedio de la lista (los jóvenes participan menos). Si crece con los años, la brecha generacional
de participación se está ampliando.

Participación y peso de cada etapa de vida:
| anio | etapa | ln | sv | nv | participacion_pct | pct_de_ln | pct_de_votantes |
|---|---|---|---|---|---|---|---|
| 2009 | 18-24 | 12,391,879 | 4,492,856 | 7,598,538 | 37.16 | 15.99 | 13.49 |
| 2009 | 25-34 | 19,998,338 | 7,039,230 | 12,475,587 | 36.07 | 25.81 | 21.13 |
| 2009 | 35-44 | 17,360,792 | 7,503,638 | 9,435,372 | 44.30 | 22.41 | 22.52 |
| 2009 | 45-59 | 16,352,038 | 8,479,792 | 7,479,139 | 53.14 | 21.10 | 25.45 |
| 2009 | 60-74 | 7,932,450 | 4,455,353 | 3,289,880 | 57.52 | 10.24 | 13.37 |
| 2009 | 75-79 | 1,524,132 | 752,021 | 736,600 | 50.52 | 1.97 | 2.26 |
| 2009 | 80-84 | 954,882 | 383,928 | 549,093 | 41.15 | 1.23 | 1.15 |
| 2009 | 85-89 | 582,601 | 163,451 | 405,723 | 28.72 | 0.75 | 0.49 |
| 2009 | 90-99 | 342,118 | 45,229 | 288,825 | 13.54 | 0.44 | 0.14 |
| 2009 | 100+ | 42,601 | 1,476 | 40,206 | 3.54 | 0.05 | 0 |
| 2012 | 18-24 | 13,030,028 | 7,242,137 | 5,758,836 | 55.70 | 17.03 | 15.28 |
| 2012 | 25-34 | 19,353,600 | 10,346,199 | 8,963,198 | 53.58 | 25.30 | 21.84 |
| 2012 | 35-44 | 16,506,639 | 10,498,810 | 5,972,209 | 63.74 | 21.58 | 22.16 |
| 2012 | 45-59 | 16,451,149 | 11,646,607 | 4,769,751 | 70.95 | 21.51 | 24.58 |
| 2012 | 60-74 | 7,969,503 | 5,827,487 | 2,124,294 | 73.29 | 10.42 | 12.30 |
| 2012 | 75-79 | 1,470,288 | 976,458 | 490,530 | 66.56 | 1.92 | 2.06 |
| 2012 | 80-84 | 939,482 | 540,294 | 397,048 | 57.64 | 1.23 | 1.14 |
| 2012 | 85-89 | 504,180 | 228,041 | 274,971 | 45.34 | 0.66 | 0.48 |
| 2012 | 90-99 | 251,707 | 74,838 | 176,252 | 29.81 | 0.33 | 0.16 |
| 2012 | 100+ | 14,386 | 2,283 | 12,070 | 15.91 | 0.02 | 0 |
| 2015 | 18-24 | 14,326,457 | 5,115,748 | 8,317,587 | 38.08 | 17.14 | 13.85 |
| 2015 | 25-34 | 19,985,340 | 7,020,798 | 11,720,034 | 37.46 | 23.92 | 19.01 |
| 2015 | 35-44 | 17,422,320 | 7,844,610 | 8,485,926 | 48.04 | 20.85 | 21.24 |
| 2015 | 45-59 | 18,670,503 | 9,733,803 | 7,810,347 | 55.48 | 22.34 | 26.36 |
| 2015 | 60-74 | 9,400,586 | 5,503,866 | 3,350,901 | 62.16 | 11.25 | 14.90 |
| 2015 | 75-79 | 1,687,691 | 911,818 | 677,960 | 57.36 | 2.02 | 2.47 |
| 2015 | 80-84 | 1,113,009 | 509,689 | 538,650 | 48.62 | 1.33 | 1.38 |
| 2015 | 85-89 | 602,430 | 211,350 | 356,503 | 37.22 | 0.72 | 0.57 |
| 2015 | 90-99 | 337,583 | 73,148 | 245,225 | 22.98 | 0.40 | 0.20 |
| 2015 | 100+ | 17,543 | 1,782 | 14,741 | 10.78 | 0.02 | 0 |
| 2018 | 18-24 | 14,576,336 | 7,427,491 | 6,136,054 | 54.76 | 16.36 | 14.34 |
| 2018 | 25-34 | 20,791,862 | 10,713,290 | 8,646,344 | 55.34 | 23.33 | 20.69 |
| 2018 | 35-44 | 18,029,122 | 10,663,371 | 6,135,017 | 63.48 | 20.23 | 20.59 |
| 2018 | 45-59 | 20,763,528 | 13,430,052 | 5,928,045 | 69.38 | 23.30 | 25.93 |
| 2018 | 60-74 | 10,736,132 | 7,291,365 | 2,723,893 | 72.80 | 12.05 | 14.08 |
| 2018 | 75-79 | 1,868,532 | 1,172,168 | 568,944 | 67.32 | 2.10 | 2.26 |
| 2018 | 80-84 | 1,249,627 | 679,335 | 485,026 | 58.34 | 1.40 | 1.31 |
| 2018 | 85-89 | 702,519 | 299,179 | 355,510 | 45.70 | 0.79 | 0.58 |
| 2018 | 90-99 | 391,056 | 105,814 | 259,166 | 28.99 | 0.44 | 0.20 |
| 2018 | 100+ | 15,283 | 2,334 | 11,857 | 16.45 | 0.02 | 0 |
| 2021 | 18-24 | 14,276,703 | 5,998,549 | 7,646,398 | 43.96 | 15.26 | 12.93 |
| 2021 | 25-34 | 21,697,597 | 8,586,427 | 12,159,935 | 41.39 | 23.20 | 18.51 |
| 2021 | 35-44 | 18,493,899 | 8,922,294 | 8,772,087 | 50.42 | 19.77 | 19.23 |
| 2021 | 45-59 | 22,414,486 | 12,807,254 | 8,649,969 | 59.69 | 23.96 | 27.61 |
| 2021 | 60-74 | 12,065,051 | 7,744,070 | 3,812,888 | 67.01 | 12.90 | 16.69 |
| 2021 | 75-79 | 2,029,465 | 1,223,485 | 719,151 | 62.98 | 2.17 | 2.64 |
| 2021 | 80-84 | 1,335,906 | 690,162 | 588,155 | 53.99 | 1.43 | 1.49 |
| 2021 | 85-89 | 758,155 | 304,115 | 422,217 | 41.87 | 0.81 | 0.66 |
| 2021 | 90-99 | 439,030 | 110,098 | 310,644 | 26.17 | 0.47 | 0.24 |
| 2021 | 100+ | 21,841 | 2,735 | 18,180 | 13.08 | 0.02 | 0.01 |
| 2024 | 18-24 | 14,877,066 | 7,004,922 | 6,894,094 | 50.40 | 15.13 | 12.76 |
| 2024 | 25-34 | 21,897,968 | 10,146,882 | 10,322,263 | 49.57 | 22.27 | 18.48 |
| 2024 | 35-44 | 19,019,143 | 10,332,646 | 7,458,712 | 58.08 | 19.34 | 18.82 |
| 2024 | 45-59 | 23,803,128 | 14,870,380 | 7,411,689 | 66.74 | 24.21 | 27.09 |
| 2024 | 60-74 | 13,698,100 | 9,603,122 | 3,237,663 | 74.79 | 13.93 | 17.49 |
| 2024 | 75-79 | 2,287,271 | 1,532,346 | 613,090 | 71.42 | 2.33 | 2.79 |
| 2024 | 80-84 | 1,453,966 | 866,345 | 496,374 | 63.57 | 1.48 | 1.58 |
| 2024 | 85-89 | 815,423 | 393,262 | 371,803 | 51.40 | 0.83 | 0.72 |
| 2024 | 90-99 | 458,518 | 145,902 | 284,676 | 33.89 | 0.47 | 0.27 |
| 2024 | 100+ | 19,765 | 3,421 | 15,102 | 18.47 | 0.02 | 0.01 |

## 3. Adultos mayores en la lista nominal (estimación)

**Método.** Se toma la participación de las personas de 60-74 años como la "abstención normal" de
adultos mayores vivos. En 80+ se calcula cuánta abstención **sobra** respecto a ese nivel
(`exceso_abstencion_est`). Ese exceso incluye personas fallecidas que siguen inscritas, pero también adultos
mayores vivos con dificultades para votar (salud, movilidad), así que es una **cota superior**. Se usa como
orden de magnitud, no como conteo de fallecidos.

| anio | ln | ln_mayores | pct_ln_mayores | ln_100_mas | edad_media_mayores_85 | part_base_pct | exceso_abstencion_est | pct_ln_exceso_est | participacion_pct | participacion_ajustada_pct | ajuste_pp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2009 | 77,481,831 | 1,922,202 | 2.48 | 42,601 | 89.86 | 57.52 | 486,173.43 | 0.63 | 44.06 | 44.35 | 0.29 |
| 2012 | 76,490,962 | 1,709,755 | 2.24 | 14,386 | 88.92 | 73.29 | 404,642.54 | 0.53 | 62.08 | 62.41 | 0.33 |
| 2015 | 83,563,462 | 2,070,565 | 2.48 | 17,543 | 89.05 | 62.16 | 416,770.64 | 0.50 | 47.07 | 47.32 | 0.25 |
| 2018 | 89,123,997 | 2,358,485 | 2.65 | 15,283 | 89.07 | 72.80 | 513,699.33 | 0.58 | 62.37 | 62.75 | 0.39 |
| 2021 | 93,532,133 | 2,554,932 | 2.73 | 21,841 | 89.13 | 67.01 | 532,107.25 | 0.57 | 51.84 | 52.15 | 0.31 |
| 2024 | 98,330,348 | 2,747,672 | 2.79 | 19,765 | 89.09 | 74.79 | 518,221.73 | 0.53 | 59.67 | 60.01 | 0.34 |

- `edad_media_mayores_85`: edad media de quienes tienen 85 años o más en la lista.
- `ln_100_mas`: personas de 100 años o más inscritas. Es poco probable que sigan vivas casi todas.
- `participacion_ajustada_pct` quita el exceso estimado del denominador; `ajuste_pp` es cuánto sube por ello.

**Promedio de todos los años:** 2.56% de la lista tiene 80+ años; el exceso
estimado equivale a 0.55% de la lista y subiría la participación en
0.32 puntos; edad media de los 85+: 89.2 años.

Detalle por grupo de edad:
| anio | grupo | ln | sv | nv | participacion_pct | exceso_abstencion_est | pct_del_grupo_en_ln |
|---|---|---|---|---|---|---|---|
| 2009 | 80-84 | 954,882 | 383,928 | 549,093 | 41.15 | 152,781.21 | 16 |
| 2009 | 85-89 | 582,601 | 163,451 | 405,723 | 28.72 | 163,959.56 | 28.14 |
| 2009 | 90-99 | 342,118 | 45,229 | 288,825 | 13.54 | 146,931.58 | 42.95 |
| 2009 | 100+ | 42,601 | 1,476 | 40,206 | 3.54 | 22,501.07 | 52.82 |
| 2012 | 80-84 | 939,482 | 540,294 | 397,048 | 57.64 | 146,639.95 | 15.61 |
| 2012 | 85-89 | 504,180 | 228,041 | 274,971 | 45.34 | 140,592.88 | 27.89 |
| 2012 | 90-99 | 251,707 | 74,838 | 176,252 | 29.81 | 109,174.07 | 43.37 |
| 2012 | 100+ | 14,386 | 2,283 | 12,070 | 15.91 | 8,235.64 | 57.25 |
| 2015 | 80-84 | 1,113,009 | 509,689 | 538,650 | 48.62 | 141,928.08 | 12.75 |
| 2015 | 85-89 | 602,430 | 211,350 | 356,503 | 37.22 | 141,610.93 | 23.51 |
| 2015 | 90-99 | 337,583 | 73,148 | 245,225 | 22.98 | 124,743.41 | 36.95 |
| 2015 | 100+ | 17,543 | 1,782 | 14,741 | 10.78 | 8,488.22 | 48.39 |
| 2018 | 80-84 | 1,249,627 | 679,335 | 485,026 | 58.34 | 168,349.71 | 13.47 |
| 2018 | 85-89 | 702,519 | 299,179 | 355,510 | 45.70 | 177,451.40 | 25.26 |
| 2018 | 90-99 | 391,056 | 105,814 | 259,166 | 28.99 | 159,900.81 | 40.89 |
| 2018 | 100+ | 15,283 | 2,334 | 11,857 | 16.45 | 7,997.41 | 52.33 |
| 2021 | 80-84 | 1,335,906 | 690,162 | 588,155 | 53.99 | 166,410.84 | 12.46 |
| 2021 | 85-89 | 758,155 | 304,115 | 422,217 | 41.87 | 182,584.51 | 24.08 |
| 2021 | 90-99 | 439,030 | 110,098 | 310,644 | 26.17 | 171,832.20 | 39.14 |
| 2021 | 100+ | 21,841 | 2,735 | 18,180 | 13.08 | 11,279.69 | 51.64 |
| 2024 | 80-84 | 1,453,966 | 866,345 | 496,374 | 63.57 | 152,779.36 | 10.51 |
| 2024 | 85-89 | 815,423 | 393,262 | 371,803 | 51.40 | 178,900.26 | 21.94 |
| 2024 | 90-99 | 458,518 | 145,902 | 284,676 | 33.89 | 176,110.48 | 38.41 |
| 2024 | 100+ | 19,765 | 3,421 | 15,102 | 18.47 | 10,431.63 | 52.78 |

Estados con mayor exceso estimado (3 por año):
| anio | estado | ln_mayores | exceso_abstencion_est | pct_ln_exceso_est |
|---|---|---|---|---|
| 2009 | DISTRITO FEDERAL | 255,963 | 70,523.56 | 0.96 |
| 2009 | DURANGO | 34,725 | 9,702.20 | 0.85 |
| 2009 | OAXACA | 81,338 | 19,869.69 | 0.79 |
| 2012 | GUERRERO | 66,767 | 16,697.26 | 0.76 |
| 2012 | OAXACA | 78,202 | 19,136.19 | 0.75 |
| 2012 | DISTRITO FEDERAL | 210,422 | 53,313.68 | 0.75 |
| 2015 | GUERRERO | 87,088 | 19,571.39 | 0.81 |
| 2015 | SAN LUIS POTOSI | 58,169 | 11,939.86 | 0.64 |
| 2015 | HIDALGO | 53,212 | 12,605.45 | 0.64 |
| 2018 | GUERRERO | 102,919 | 27,538.54 | 1.10 |
| 2018 | OAXACA | 104,044 | 24,782.99 | 0.87 |
| 2018 | PUEBLA | 138,645 | 36,411.49 | 0.81 |
| 2021 | OAXACA | 115,784 | 27,606.59 | 0.92 |
| 2021 | GUERRERO | 95,315 | 22,139.49 | 0.86 |
| 2021 | PUEBLA | 148,999 | 37,877.14 | 0.80 |
| 2024 | GUERRERO | 105,139 | 25,327.12 | 0.96 |
| 2024 | OAXACA | 118,100 | 25,845.51 | 0.83 |
| 2024 | DURANGO | 45,242 | 10,984.32 | 0.79 |

## 4. Contexto externo por elección
| anio | tipo | participacion_pct | fecha | contexto |
|---|---|---|---|---|
| 2009 | intermedia | 44.06 | 5 jul 2009 | Crisis económica global 2008-09; brote de influenza A(H1N1) (abr-may 2009) con medidas sanitarias; campaña ciudadana por anular el voto; violencia por la estrategia contra el crimen organizado. |
| 2012 | presidencial | 62.08 | 1 jul 2012 | Presidencial con regreso del PRI; movimiento estudiantil #YoSoy132; elecciones locales concurrentes. Ojo con los datos: la lista nominal de 2012 excluye cuadernillos no disponibles, y casi no tiene NS. |
| 2015 | intermedia | 47.07 | 7 jun 2015 | Intermedia posterior al caso Ayotzinapa (sep 2014) y protestas; campañas por voto nulo/abstención; bloqueos y boicot de la CNTE en varios estados; primeras candidaturas independientes; 9 gubernaturas. |
| 2018 | presidencial | 62.37 | 1 jul 2018 | Presidencial con elecciones locales concurrentes en casi todas las entidades y muchísimos cargos en disputa; alta violencia política; alternancia con Morena. |
| 2021 | intermedia | 51.84 | 6 jun 2021 | Intermedia en plena pandemia de COVID-19 (medidas sanitarias, vacunación en curso); 15 gubernaturas; violencia política; fuerte polarización. |
| 2024 | presidencial | 59.67 | 2 jun 2024 | Presidencial con las dos principales candidatas mujeres; elecciones locales concurrentes en las 32 entidades (9 gubernaturas); violencia política elevada; primer año con código de sexo no binario en el CCPC. |

**Cómo usar esto:** son hechos de contexto para **interpretar** los cambios, no variables medidas. Con solo seis
elecciones no se puede separar el efecto de un evento del efecto de ser presidencial o intermedia, ni del
reseccionamiento o de cambios en la lista nominal. Conviene **verificar cada dato con fuentes** antes de citarlo
en el reporte final, y presentarlo como hipótesis.

## 5. Límites
- Las cifras son agregados nacionales y por estado: no se sabe quién votó, solo cuántas personas por sección, sexo y edad.
- Las comparaciones entre años usan secciones que pueden haber cambiado por reseccionamiento.
- 2012 tiene una lista nominal menor y casi sin NS por exclusión de cuadernillos: compárala con cuidado.
- El CCPC no incluye casillas especiales ni votantes en el extranjero.
