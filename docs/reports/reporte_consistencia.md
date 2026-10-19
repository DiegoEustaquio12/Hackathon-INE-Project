# Reporte de consistencia: Fase 2 (consistencia entre años)

Lo genera `python ai/src/data_prep/fase2.py` a partir de la tabla limpia de la Fase 1. No se edita a mano: si algo cambia, se vuelve a correr el script.

Sirve para saber qué municipios se pueden comparar entre elecciones. La idea es seguir cada sección electoral: si una sección pasa de un municipio a otro, el territorio de los dos cambió, aunque conserven su clave y su nombre.

## Resultado

- ✅ Al sumar por sección, los totales de cada estado y elección quedan iguales a los de la tabla limpia: no se perdió nada.
- ✅ En cada elección, cada sección cae en un solo municipio y cada municipio trae un solo nombre.
- ✅ Las 19 correcciones de nombre son escrituras que ya traen los archivos, y ningún nombre elegido se repite dentro de un estado.
- El catálogo tiene **2,477 municipios**, uno por cada clave que aparece en alguna elección. Todos siguen en 2024.
- **254 secciones cambian de municipio** (64 en 2021 y 190 en 2024; antes de 2021, ninguna). Por eso **46 municipios** cambian de territorio.
- **5 claves pasan a otro territorio** (CHIAPAS (7), en 2021).
- **22 claves no aparecen en alguna elección**: los municipios creados después de 2009 y los 3 que faltan en 2012.
- **1,048 secciones faltan en 2012** aunque están en 2009 y en 2015.

## Salidas

| Archivo | Qué trae |
|---|---|
| `data/processed/catalogo_municipios.csv` | Una fila por municipio: nombre, situación en cada elección, peso del hueco de 2012 y una nota con sus cambios de territorio |
| `data/processed/cambios_secciones.csv` | Las 254 secciones que cambian de municipio, con su municipio antes y después |
| `data/interim/secciones.parquet` | Una fila por sección y elección, con la elección y el municipio de su aparición anterior. No se sube a GitHub |

Los CSV llevan BOM para que Excel muestre bien los acentos. En Python se leen con `pd.read_csv(ruta, encoding="utf-8-sig")`.

## 1. Las secciones entre elecciones

Cada sección se compara con la última elección en la que apareció. Así, una sección que falta en 2012 y regresa en 2015 se compara contra 2009 y no parece nueva.

| Elección | Secciones | Siguen en su municipio | Cambian de municipio | Nuevas | Regresan después de faltar | De la elección anterior, ya no están |
|---|---|---|---|---|---|---|
| 2009 | 64,934 | — | — | — | — | — |
| 2012 | 65,599 | 63,789 | 0 | 1,810 | 0 | 1,145 |
| 2015 | 68,362 | 66,426 | 0 | 1,936 | 1,048 | 221 |
| 2018 | 68,408 | 68,361 | 0 | 47 | 0 | 1 |
| 2021 | 68,812 | 67,569 | 64 | 1,179 | 0 | 775 |
| 2024 | 70,751 | 67,786 | 190 | 2,775 | 0 | 836 |

- **Nuevas:** no habían aparecido antes. Casi todas salen del reseccionamiento (cuando el INE divide o redibuja secciones).
- **Regresan después de faltar:** no estaban en la elección anterior, pero sí en una más vieja.
- **Ya no están:** estaban en la elección anterior y no en esta. Algunas regresan después, como las que faltan en 2012.

Historial de cada sección en las seis elecciones (idea tomada de `consistencia.py`, rama `proposals-Max`):

| Historial | Secciones |
|---|---|
| En las seis elecciones | 62,048 |
| Aparece después de 2009 | 7,747 |
| Está desde 2009 y ya no está en 2024 | 1,882 |
| Está en 2009 y en 2024, pero falta en alguna elección entre ellas | 1,004 |

Cambios de tipo de sección y de distrito. Solo se comparan cuando la sección tiene valor en las dos elecciones:

| Elección | Cambian de tipo (U, M, R) | Cambian de distrito federal | Cambian de distrito local |
|---|---|---|---|
| 2012 | 553 | 0 | 0 |
| 2015 | 308 | 0 | 0 |
| 2018 | 372 | 0 | 0 |
| 2021 | 142 | 0 | 0 |
| 2024 | 324 | 13,183 | 20,890 |

Según el diccionario del INE, `DEF` y `DEL` de 2009 a 2021 vienen en el mapa de distritos de 2021, y los de 2024 en el de 2023 (`reporte_calidad.md`, sección 3). Por eso todos los cambios de distrito aparecen en 2024. Un cambio de distrito, por sí solo, no cambia el territorio del municipio.

## 2. Situación de cada municipio en cada elección

Cada municipio recibe una situación por elección. Se revisan en este orden y gana la primera que se cumple:

| Situación | Qué quiere decir |
|---|---|
| `sin_registro` | La clave no aparece en esa elección |
| `nuevo` | Primera elección en la que aparece la clave (2009 es el punto de partida y ahí no cuenta) |
| `clave_reasignada` | La clave ya existía, pero ninguna de sus secciones anteriores sigue en ella y recibió secciones de otro municipio |
| `cambio_limites` | Recibió secciones de otro municipio o le cedió secciones |
| `sin_cambio` | Conserva sus secciones. Las secciones nuevas por reseccionamiento dentro del municipio no cuentan como cambio |

Municipios en cada situación:

| Situación | 2009 | 2012 | 2015 | 2018 | 2021 | 2024 |
|---|---|---|---|---|---|---|
| `sin_registro` | 19 | 22 | 19 | 14 | 9 | 0 |
| `nuevo` | 0 | 0 | 0 | 5 | 5 | 9 |
| `clave_reasignada` | 0 | 0 | 0 | 0 | 5 | 0 |
| `cambio_limites` | 0 | 0 | 0 | 0 | 13 | 14 |
| `sin_cambio` | 2,458 | 2,455 | 2,458 | 2,458 | 2,445 | 2,454 |

Si un municipio queda `sin_cambio` en dos elecciones seguidas, su territorio es el mismo en ambas y su historial se puede comparar.

## 3. Municipios con cambios de territorio

Son 46 municipios con al menos una elección en `nuevo`, `clave_reasignada` o `cambio_limites`. Su historial no se puede comparar tal como viene de un lado al otro del cambio. La columna `nota` del catálogo trae el mismo texto.

| Estado | Clave | Municipio | Qué pasó |
|---|---|---|---|
| BAJA CALIFORNIA (2) | 1 | Ensenada | 2024: cedió 34 secciones (18.4% de su lista de 2021): 33 a San Quintin (clave 6) y 1 a San Felipe (clave 7) |
| BAJA CALIFORNIA (2) | 2 | Mexicali | 2024: cedió 8 secciones (1.6% de su lista de 2021): 8 a San Felipe (clave 7) |
| BAJA CALIFORNIA (2) | 6 | San Quintin | 2024: municipio nuevo; recibió 33 secciones (100.0% de su lista): 33 de Ensenada (clave 1) |
| BAJA CALIFORNIA (2) | 7 | San Felipe | 2024: municipio nuevo; recibió 9 secciones (100.0% de su lista): 1 de Ensenada (clave 1) y 8 de Mexicali (clave 2) |
| CAMPECHE (4) | 2 | Calkiní | 2021: cedió 6 secciones (26.8% de su lista de 2018): 6 a Dzitbalché (clave 12) |
| CAMPECHE (4) | 4 | Champotón | 2021: cedió 9 secciones (17.2% de su lista de 2018): 9 a Seybaplaya (clave 13) |
| CAMPECHE (4) | 12 | Dzitbalché | 2021: municipio nuevo; recibió 6 secciones (100.0% de su lista): 6 de Calkiní (clave 2) |
| CAMPECHE (4) | 13 | Seybaplaya | 2021: municipio nuevo; recibió 9 secciones (100.0% de su lista): 9 de Champotón (clave 4) |
| CHIAPAS (7) | 2 | Acala | 2021: cedió 4 secciones (30.0% de su lista de 2018): 4 a Emiliano Zapata (clave 122) |
| CHIAPAS (7) | 71 | Pueblo Nuevo Solistahuacán | 2021: cedió 2 secciones (18.1% de su lista de 2018): 2 a Rincón Chamula San Pedro (clave 120) |
| CHIAPAS (7) | 81 | Siltepec | 2021: cedió 7 secciones (35.7% de su lista de 2018): 2 a Capitán Luis Ángel Vidal (clave 119) y 5 a Honduras de la Sierra (clave 124) |
| CHIAPAS (7) | 93 | Tecpatán | 2021: cedió 14 secciones (48.8% de su lista de 2018): 14 a Mezcalapa (clave 123) |
| CHIAPAS (7) | 108 | Villa Corzo | 2021: cedió 5 secciones (18.8% de su lista de 2018): 5 a El Parral (clave 121) |
| CHIAPAS (7) | 119 | Capitán Luis Ángel Vidal | 2021: municipio nuevo; recibió 2 secciones (100.0% de su lista): 2 de Siltepec (clave 81) |
| CHIAPAS (7) | 120 | Rincón Chamula San Pedro | 2018: municipio nuevo; sus 4 secciones son nuevas, así que no se sabe de qué municipio salieron · 2021: la clave ya no es el territorio de 2018 (entonces Emiliano Zapata, con 4 secciones); recibió 2 secciones (100.0% de su lista): 2 de Pueblo Nuevo Solistahuacán (clave 71) |
| CHIAPAS (7) | 121 | El Parral | 2018: municipio nuevo; sus 3 secciones son nuevas, así que no se sabe de qué municipio salieron · 2021: la clave ya no es el territorio de 2018 (entonces Mezcalapa, con 3 secciones); recibió 5 secciones (100.0% de su lista): 5 de Villa Corzo (clave 108) |
| CHIAPAS (7) | 122 | Emiliano Zapata | 2018: municipio nuevo; sus 2 secciones son nuevas, así que no se sabe de qué municipio salieron · 2021: la clave ya no es el territorio de 2018 (entonces El Parral, con 2 secciones); recibió 4 secciones (100.0% de su lista): 4 de Acala (clave 2) |
| CHIAPAS (7) | 123 | Mezcalapa | 2018: municipio nuevo; su única sección es nueva, así que no se sabe de qué municipio salió · 2021: la clave ya no es el territorio de 2018 (entonces Capitán Luis Ángel Vidal, con 1 sección); recibió 14 secciones (100.0% de su lista): 14 de Tecpatán (clave 93) |
| CHIAPAS (7) | 124 | Honduras de la Sierra | 2018: municipio nuevo; sus 2 secciones son nuevas, así que no se sabe de qué municipio salieron · 2021: la clave ya no es el territorio de 2018 (entonces Rincón Chamula San Pedro, con 2 secciones); recibió 5 secciones (99.6% de su lista): 5 de Siltepec (clave 81) |
| CIUDAD DE MEXICO (9) | 4 | Cuajimalpa de Morelos | 2021: recibió 4 secciones (5.4% de su lista): 4 de Álvaro Obregón (clave 10) |
| CIUDAD DE MEXICO (9) | 10 | Álvaro Obregón | 2021: cedió 4 secciones (1.6% de su lista de 2018): 4 a Cuajimalpa de Morelos (clave 4) |
| GUERRERO (12) | 12 | Ayutla de los Libres | 2024: cedió 12 secciones (15.2% de su lista de 2021): 12 a Ñuu Savi (clave 82) |
| GUERRERO (12) | 23 | Cuajinicuilapa | 2024: cedió 8 secciones (25.1% de su lista de 2021): 8 a San Nicolás (clave 84) |
| GUERRERO (12) | 42 | Malinaltepec | 2024: cedió 3 secciones (23.4% de su lista de 2021): 3 a Santa Cruz del Rincón (clave 85) |
| GUERRERO (12) | 54 | San Marcos | 2024: cedió 9 secciones (20.1% de su lista de 2021): 9 a Las Vigas (clave 83) |
| GUERRERO (12) | 82 | Ñuu Savi | 2024: municipio nuevo; recibió 12 secciones (100.0% de su lista): 12 de Ayutla de los Libres (clave 12) |
| GUERRERO (12) | 83 | Las Vigas | 2024: municipio nuevo; recibió 9 secciones (100.0% de su lista): 9 de San Marcos (clave 54) |
| GUERRERO (12) | 84 | San Nicolás | 2024: municipio nuevo; recibió 8 secciones (100.0% de su lista): 8 de Cuajinicuilapa (clave 23) |
| GUERRERO (12) | 85 | Santa Cruz del Rincón | 2024: municipio nuevo; recibió 3 secciones (100.0% de su lista): 3 de Malinaltepec (clave 42) |
| MORELOS (17) | 15 | Miacatlán | 2021: cedió 5 secciones (38.3% de su lista de 2018): 5 a Coatetelco (clave 34) |
| MORELOS (17) | 17 | Puente de Ixtla | 2021: cedió 7 secciones (37.1% de su lista de 2018): 7 a Xoxocotla (clave 35) |
| MORELOS (17) | 22 | Tetela del Volcán | 2024: cedió 4 secciones (22.0% de su lista de 2021): 4 a Hueyapan (clave 36) |
| MORELOS (17) | 34 | Coatetelco | 2021: municipio nuevo; recibió 5 secciones (100.0% de su lista): 5 de Miacatlán (clave 15) |
| MORELOS (17) | 35 | Xoxocotla | 2021: municipio nuevo; recibió 7 secciones (99.7% de su lista): 7 de Puente de Ixtla (clave 17) |
| MORELOS (17) | 36 | Hueyapan | 2024: municipio nuevo; recibió 4 secciones (100.0% de su lista): 4 de Tetela del Volcán (clave 22) |
| NUEVO LEON (19) | 6 | Apodaca | 2024: recibió 2 secciones (0.3% de su lista): 2 de Guadalupe (clave 26); cedió 1 sección (0.2% de su lista de 2021): 1 a Guadalupe (clave 26) |
| NUEVO LEON (19) | 26 | Guadalupe | 2024: recibió 1 sección (0.1% de su lista): 1 de Apodaca (clave 6); cedió 2 secciones (0.2% de su lista de 2021): 2 a Apodaca (clave 6) |
| SINALOA (25) | 1 | Ahome | 2024: cedió 7 secciones (1.4% de su lista de 2021): 7 a Juan José Ríos (clave 20) |
| SINALOA (25) | 6 | Culiacán | 2024: cedió 52 secciones (4.0% de su lista de 2021): 52 a Eldorado (clave 19) |
| SINALOA (25) | 10 | El Fuerte | 2024: cedió 3 secciones (2.2% de su lista de 2021): 3 a Juan José Ríos (clave 20) |
| SINALOA (25) | 11 | Guasave | 2024: cedió 46 secciones (10.9% de su lista de 2021): 46 a Juan José Ríos (clave 20) |
| SINALOA (25) | 17 | Sinaloa | 2024: cedió 1 sección (0.3% de su lista de 2021): 1 a Juan José Ríos (clave 20) |
| SINALOA (25) | 19 | Eldorado | 2024: municipio nuevo; recibió 52 secciones (100.0% de su lista): 52 de Culiacán (clave 6) |
| SINALOA (25) | 20 | Juan José Ríos | 2024: municipio nuevo; recibió 57 secciones (100.0% de su lista): 7 de Ahome (clave 1), 3 de El Fuerte (clave 10), 46 de Guasave (clave 11) y 1 de Sinaloa (clave 17) |
| TLAXCALA (29) | 10 | Chiautempan | 2021: recibió 1 sección (2.3% de su lista): 1 de La Magdalena Tlaltelulco (clave 52) |
| TLAXCALA (29) | 52 | La Magdalena Tlaltelulco | 2021: cedió 1 sección (9.3% de su lista de 2018): 1 a Chiautempan (clave 10) |

## 4. Municipios nuevos y claves reasignadas

La última columna dice qué parte de su lista está en secciones que ya existían en elecciones anteriores. Si es casi 100%, su historial se puede rearmar con esas secciones.

| Elección | Estado | Clave | Nombre en esa elección | Situación | Secciones | Lista nominal | En secciones que ya existían |
|---|---|---|---|---|---|---|---|
| 2024 | BAJA CALIFORNIA (2) | 6 | San Quintin | `nuevo` | 33 | 87,992 | 100.0% |
| 2024 | BAJA CALIFORNIA (2) | 7 | San Felipe | `nuevo` | 9 | 15,169 | 100.0% |
| 2021 | CAMPECHE (4) | 12 | Dzitblache | `nuevo` | 6 | 11,472 | 100.0% |
| 2021 | CAMPECHE (4) | 13 | Seybaplaya | `nuevo` | 9 | 11,547 | 100.0% |
| 2021 | CHIAPAS (7) | 119 | Capitán Luis Ángel Vidal | `nuevo` | 2 | 2,811 | 100.0% |
| 2018 | CHIAPAS (7) | 120 | Emiliano Zapata | `nuevo` | 4 | 2,301 | 0.0% |
| 2021 | CHIAPAS (7) | 120 | Rincón Chamula San Pedro | `clave_reasignada` | 2 | 5,125 | 100.0% |
| 2018 | CHIAPAS (7) | 121 | Mezcalapa | `nuevo` | 3 | 1,202 | 0.0% |
| 2021 | CHIAPAS (7) | 121 | El Parral | `clave_reasignada` | 5 | 11,969 | 100.0% |
| 2018 | CHIAPAS (7) | 122 | El Parral | `nuevo` | 2 | 909 | 0.0% |
| 2021 | CHIAPAS (7) | 122 | Emiliano Zapata | `clave_reasignada` | 4 | 8,457 | 100.0% |
| 2018 | CHIAPAS (7) | 123 | Capitán Luis Ángel Vidal | `nuevo` | 1 | 481 | 0.0% |
| 2021 | CHIAPAS (7) | 123 | Mezcalapa | `clave_reasignada` | 14 | 16,726 | 100.0% |
| 2018 | CHIAPAS (7) | 124 | Rincón Chamula San Pedro | `nuevo` | 2 | 936 | 0.0% |
| 2021 | CHIAPAS (7) | 124 | Honduras de la Sierra | `clave_reasignada` | 6 | 8,171 | 99.6% |
| 2024 | GUERRERO (12) | 82 | Ñuu Savi | `nuevo` | 12 | 7,596 | 100.0% |
| 2024 | GUERRERO (12) | 83 | Las Vigas | `nuevo` | 9 | 7,166 | 100.0% |
| 2024 | GUERRERO (12) | 84 | San Nicolás | `nuevo` | 8 | 5,088 | 100.0% |
| 2024 | GUERRERO (12) | 85 | Santa Cruz del Rincón | `nuevo` | 3 | 4,960 | 100.0% |
| 2021 | MORELOS (17) | 34 | Coatetelco | `nuevo` | 5 | 7,982 | 100.0% |
| 2021 | MORELOS (17) | 35 | Xoxocotla | `nuevo` | 8 | 19,345 | 99.7% |
| 2024 | MORELOS (17) | 36 | Hueyapan | `nuevo` | 4 | 5,814 | 100.0% |
| 2024 | SINALOA (25) | 19 | Eldorado | `nuevo` | 52 | 29,770 | 100.0% |
| 2024 | SINALOA (25) | 20 | Juan José Ríos | `nuevo` | 57 | 30,496 | 100.0% |

Una clave reasignada tenía antes secciones que ya no aparecen después, y en la elección siguiente la misma clave es otro municipio. Unir por clave mezclaría municipios distintos, y unir por nombre compararía un pedazo de territorio con el municipio completo.

## 5. Claves que no aparecen en alguna elección

| Estado | Clave | Municipio | Sin registro en |
|---|---|---|---|
| BAJA CALIFORNIA (2) | 6 | San Quintin | 2009, 2012, 2015, 2018, 2021 |
| BAJA CALIFORNIA (2) | 7 | San Felipe | 2009, 2012, 2015, 2018, 2021 |
| CAMPECHE (4) | 12 | Dzitbalché | 2009, 2012, 2015, 2018 |
| CAMPECHE (4) | 13 | Seybaplaya | 2009, 2012, 2015, 2018 |
| CHIAPAS (7) | 117 | San Andrés Duraznal | 2012 |
| CHIAPAS (7) | 119 | Capitán Luis Ángel Vidal | 2009, 2012, 2015, 2018 |
| CHIAPAS (7) | 120 | Rincón Chamula San Pedro | 2009, 2012, 2015 |
| CHIAPAS (7) | 121 | El Parral | 2009, 2012, 2015 |
| CHIAPAS (7) | 122 | Emiliano Zapata | 2009, 2012, 2015 |
| CHIAPAS (7) | 123 | Mezcalapa | 2009, 2012, 2015 |
| CHIAPAS (7) | 124 | Honduras de la Sierra | 2009, 2012, 2015 |
| GUERRERO (12) | 82 | Ñuu Savi | 2009, 2012, 2015, 2018, 2021 |
| GUERRERO (12) | 83 | Las Vigas | 2009, 2012, 2015, 2018, 2021 |
| GUERRERO (12) | 84 | San Nicolás | 2009, 2012, 2015, 2018, 2021 |
| GUERRERO (12) | 85 | Santa Cruz del Rincón | 2009, 2012, 2015, 2018, 2021 |
| MORELOS (17) | 34 | Coatetelco | 2009, 2012, 2015, 2018 |
| MORELOS (17) | 35 | Xoxocotla | 2009, 2012, 2015, 2018 |
| MORELOS (17) | 36 | Hueyapan | 2009, 2012, 2015, 2018, 2021 |
| OAXACA (20) | 144 | San Francisco Nuxaño | 2012 |
| OAXACA (20) | 218 | San Juan Teita | 2012 |
| SINALOA (25) | 19 | Eldorado | 2009, 2012, 2015, 2018, 2021 |
| SINALOA (25) | 20 | Juan José Ríos | 2009, 2012, 2015, 2018, 2021 |

## 6. El hueco de 2012

- 1,048 secciones están en 2009 y en 2015 pero no en 2012. En 2009 tenían 626,254 personas en la lista nominal.
- Ninguna cambia de municipio entre 2009 y 2015: el hueco no es un cambio de territorio, es información que falta.
- Afectan a 332 municipios. En 66 son más del 10% de su lista de 2009, y en 8, más de la mitad.
- 3 municipios faltan completos en 2012: San Andrés Duraznal (CHIAPAS (7)), San Francisco Nuxaño (OAXACA (20)) y San Juan Teita (OAXACA (20)).
- Esto coincide con lo que documenta el manual del INE: en 2012 se excluyeron los cuadernillos no disponibles (ver «¿Qué es NS?» en `reto_y_datos.md`).

Municipios con más de la mitad de su lista en el hueco:

| Estado | Clave | Municipio | Secciones que faltan | % de su lista de 2009 |
|---|---|---|---|---|
| CHIAPAS (7) | 117 | San Andrés Duraznal | 1 | 100.0% |
| OAXACA (20) | 144 | San Francisco Nuxaño | 1 | 100.0% |
| OAXACA (20) | 218 | San Juan Teita | 1 | 100.0% |
| MICHOACAN (16) | 24 | Cherán | 6 | 84.3% |
| OAXACA (20) | 302 | San Pedro Coxcaltepec Cántaros | 1 | 79.5% |
| CHIHUAHUA (8) | 56 | Rosario | 3 | 75.1% |
| CHIHUAHUA (8) | 7 | Balleza | 8 | 59.3% |
| OAXACA (20) | 329 | San Pedro Tidaá | 1 | 51.1% |

La columna `pct_hueco_2012` del catálogo trae este porcentaje para cada municipio.

## 7. Nombres

Entre elecciones, los municipios se unen con este catálogo, nunca por nombre. El nombre solo sirve para mostrar.

- **Municipio:** el nombre más reciente (2024). Si ese nombre solo cambia acentos, mayúsculas o espacios respecto a otros años, se usa la escritura más frecuente: en 2024 vienen errores como «ARío» o «Dr. BelisaRío Domínguez».
- **Estado:** el nombre más reciente.
- **Correcciones a mano:** los casos que esa regla deja mal. Cada una es una escritura que ya traen los archivos.

| Estado | Clave | Nombre elegido | Por qué |
|---|---|---|---|
| CAMPECHE (4) | 6 | Hopelchén | «Hopelche}én» (2024) es errata |
| CHIAPAS (7) | 38 | Huitiupán | «Huitiupaán» (2024) es errata |
| CHIAPAS (7) | 107 | Villa Comaltitlán | «Villacomaltitlán» (2024) viene junto |
| HIDALGO (13) | 50 | San Agustín Metzquititlán | «San Agustón» (2024) es errata |
| NUEVO LEON (19) | 10 | El Carmen | 2024 le quita el «El» |
| NUEVO LEON (19) | 14 | Doctor Arroyo | 2024 lo abrevia («Dr.») |
| NUEVO LEON (19) | 15 | Doctor Coss | 2024 lo abrevia («Dr.») |
| NUEVO LEON (19) | 16 | Doctor González | 2024 lo abrevia («Dr.») |
| NUEVO LEON (19) | 20 | General Bravo | 2024 lo abrevia («Gral.») |
| NUEVO LEON (19) | 21 | General Escobedo | 2024 lo abrevia («Gral.») |
| NUEVO LEON (19) | 22 | General Terán | 2024 lo abrevia («Gral.») |
| NUEVO LEON (19) | 23 | General Treviño | 2024 lo abrevia («Gral.») |
| NUEVO LEON (19) | 24 | General Zaragoza | 2024 lo abrevia («Gral.») |
| NUEVO LEON (19) | 25 | General Zuazua | 2024 lo abrevia («Gral.») |
| OAXACA (20) | 208 | San Juan Mixtepec Dto 08 | sin el distrito se llama igual que la clave 209 |
| OAXACA (20) | 209 | San Juan Mixtepec Dto 26 | sin el distrito se llama igual que la clave 208 |
| OAXACA (20) | 316 | San Pedro Mixtepec Dto 22 | sin el distrito se llama igual que la clave 317 |
| OAXACA (20) | 317 | San Pedro Mixtepec Dto 26 | sin el distrito se llama igual que la clave 316 |
| VERACRUZ (30) | 10 | Alto Lucero de Gutiérrez Barrios | «Barios» (2024) es errata |

**Estados con más de un nombre:**

- Estado 9: DISTRITO FEDERAL (2009, 2012, 2015, 2018) · CIUDAD DE MEXICO (2021, 2024) → queda **CIUDAD DE MEXICO**

**Municipios:** 78 claves aparecen con más de una escritura. En 38 solo cambian acentos, mayúsculas o espacios. En las otras 40, este es el nombre elegido:

| Estado | Clave | Escrituras (años) | Nombre elegido |
|---|---|---|---|
| CAMPECHE (4) | 6 | Hopelchén (2009, 2012, 2015, 2018, 2021) · Hopelche}én (2024) | Hopelchén |
| CAMPECHE (4) | 12 | Dzitblache (2021) · Dzitbalché (2024) | Dzitbalché |
| COAHUILA (5) | 7 | Cuatro Ciénegas (2009, 2012, 2015, 2018, 2021) · Cuatrociénegas (2024) | Cuatrociénegas |
| CHIAPAS (7) | 38 | Huitiupán (2009, 2012, 2015, 2018, 2021) · Huitiupaán (2024) | Huitiupán |
| CHIAPAS (7) | 107 | Villa Comaltitlán (2009, 2012, 2015, 2018, 2021) · Villacomaltitlán (2024) | Villa Comaltitlán |
| CHIAPAS (7) | 114 | Maravilla Tejenapa (2009, 2012, 2015, 2018) · Maravilla Tenejapa (2021, 2024) | Maravilla Tenejapa |
| CHIAPAS (7) | 120 | Emiliano Zapata (2018) · Rincón Chamula San Pedro (2021, 2024) | Rincón Chamula San Pedro |
| CHIAPAS (7) | 121 | Mezcalapa (2018) · El Parral (2021, 2024) | El Parral |
| CHIAPAS (7) | 122 | El Parral (2018) · Emiliano Zapata (2021, 2024) | Emiliano Zapata |
| CHIAPAS (7) | 123 | Capitán Luis Ángel Vidal (2018) · Mezcalapa (2021, 2024) | Mezcalapa |
| CHIAPAS (7) | 124 | Rincón Chamula San Pedro (2018) · Honduras de la Sierra (2021, 2024) | Honduras de la Sierra |
| CHIHUAHUA (8) | 8 | Batopilas (2009, 2012, 2015, 2018) · Batopilas de Manuel Gómez Morín (2021, 2024) | Batopilas de Manuel Gómez Morín |
| DURANGO (10) | 6 | General Simón Bolívar (2009, 2012, 2015, 2018, 2021) · Simón Bolívar (2024) | Simón Bolívar |
| HIDALGO (13) | 50 | San Agustín Metzquititlán (2009, 2012, 2015, 2018, 2021) · San Agustón Metzquititlán (2024) | San Agustín Metzquititlán |
| MICHOACAN (16) | 65 | Parácuaro (2009, 2012, 2015, 2018, 2024) · Paracho (2021) | Parácuaro |
| MICHOACAN (16) | 66 | Paracho (2009, 2012, 2015, 2018, 2024) · Parácuaro (2021) | Paracho |
| MORELOS (17) | 13 | Jonacatepec (2009, 2012, 2015, 2018, 2024) · Jonacatepec de Leandro Valle (2021) | Jonacatepec |
| NUEVO LEON (19) | 10 | El Carmen (2009, 2012, 2015, 2018, 2021) · Carmen (2024) | El Carmen |
| NUEVO LEON (19) | 14 | Doctor Arroyo (2009, 2012, 2015, 2018, 2021) · Dr. Arroyo (2024) | Doctor Arroyo |
| NUEVO LEON (19) | 15 | Doctor Coss (2009, 2012, 2015, 2018, 2021) · Dr. Coss (2024) | Doctor Coss |
| NUEVO LEON (19) | 16 | Doctor González (2009, 2012, 2015, 2018, 2021) · Dr. González (2024) | Doctor González |
| NUEVO LEON (19) | 20 | General Bravo (2009, 2012, 2015, 2018, 2021) · Gral. Bravo (2024) | General Bravo |
| NUEVO LEON (19) | 21 | General Escobedo (2009, 2012, 2015, 2018, 2021) · Gral. Escobedo (2024) | General Escobedo |
| NUEVO LEON (19) | 22 | General Terán (2009, 2012, 2015, 2018, 2021) · Gral. Terán (2024) | General Terán |
| NUEVO LEON (19) | 23 | General Treviño (2009, 2012, 2015, 2018, 2021) · Gral. Treviño (2024) | General Treviño |
| NUEVO LEON (19) | 24 | General Zaragoza (2009, 2012, 2015, 2018, 2021) · Gral. Zaragoza (2024) | General Zaragoza |
| NUEVO LEON (19) | 25 | General Zuazua (2009, 2012, 2015, 2018, 2021) · Gral. Zuazua (2024) | General Zuazua |
| OAXACA (20) | 43 | Heroica Ciudad de Juchitán de Zaragoza (2009, 2012, 2015, 2018, 2024) · Juchitán de Zaragoza (2021) | Heroica Ciudad de Juchitán de Zaragoza |
| OAXACA (20) | 121 | San Blas Atempa (2009, 2012, 2015, 2018, 2021) · Heroica Villa de San Blas Atempa (2024) | Heroica Villa de San Blas Atempa |
| OAXACA (20) | 208 | San Juan Mixtepec (2009, 2012, 2015, 2018, 2024) · San Juan Mixtepec Dto 08 (2021) | San Juan Mixtepec Dto 08 |
| OAXACA (20) | 209 | San Juan Mixtepec (2009, 2012, 2015, 2018, 2024) · San Juan Mixtepec Dto 26 (2021) | San Juan Mixtepec Dto 26 |
| OAXACA (20) | 316 | San Pedro Mixtepec (2009, 2012, 2015, 2018, 2024) · San Pedro Mixtepec Dto 22 (2021) | San Pedro Mixtepec Dto 22 |
| OAXACA (20) | 317 | San Pedro Mixtepec (2009, 2012, 2015, 2018, 2024) · San Pedro Mixtepec Dto 26 (2021) | San Pedro Mixtepec Dto 26 |
| OAXACA (20) | 332 | Villa de Tututepec de Melchor Ocampo (2009, 2012, 2015, 2018) · Villa de Tututepec (2021, 2024) | Villa de Tututepec |
| OAXACA (20) | 459 | Santiago Chazumba (2009, 2012, 2015, 2018, 2024) · Villa de Santiago Chazumba (2021) | Santiago Chazumba |
| OAXACA (20) | 549 | Heroica Villa Tezoatlán de Segura y Luna, Cuna de (2009, 2012, 2015, 2018) · Heroica Villa Tezoatlán de Segura y Luna, Cuna de la Independencia de Oaxaca (2021, 2024) | Heroica Villa Tezoatlán de Segura y Luna, Cuna de la Independencia de Oaxaca |
| OAXACA (20) | 562 | Villa Hidalgo (2009, 2012, 2015, 2018, 2021) · Villa Hidalgo Yalalag (2024) | Villa Hidalgo Yalalag |
| TLAXCALA (29) | 37 | Ziltlaltépec de Trinidad Sánchez Santos (2009, 2012, 2015, 2018, 2021) · Zitlaltépec de Trinidad Sánchez Santos (2024) | Zitlaltépec de Trinidad Sánchez Santos |
| VERACRUZ (30) | 10 | Alto Lucero de Gutiérrez Barrios (2009, 2012, 2015, 2018, 2021) · Alto Lucero de Gutiérrez Barios (2024) | Alto Lucero de Gutiérrez Barrios |
| VERACRUZ (30) | 47 | Cosamaloapan de Carpio (2009, 2012, 2015, 2018, 2021) · Cosamaloapan (2024) | Cosamaloapan |

## 8. Pendiente

- **Comparar con el tablero del INE** (punto 5 de la Fase 2): falta que alguien del equipo exporte las cifras por estado y elección.
- **Qué hacer con los 46 municipios con cambios** (decisión 8 de la Fase 5): marcarlos y no usar su historial anterior al cambio, o rearmar su historial sumando las secciones que hoy les pertenecen. De los 24 casos de `nuevo` o `clave_reasignada`, 19 tienen más del 99% de su lista en secciones que ya existían; los otros 5 están hechos solo de secciones nuevas, así que no se sabe de dónde salieron.

## 9. Cambios propuestos para los docs

Los docs no se tocan en esta fase. Esto es lo que se propone cambiar:

- `reto_y_datos.md`, «Lo que cambia con el tiempo»: 254 secciones cambian de municipio (64 en 2021 y 190 en 2024; antes de 2021, ninguna), así que 46 municipios cambian de territorio aunque conserven su clave y su nombre. Además, 5 claves pasan a otro territorio (secciones 3 y 4).
- `reto_y_datos.md`, «Cosas a cuidar cuando limpiemos»: entre elecciones, los municipios se unen con `catalogo_municipios.csv`, no por nombre ni solo por clave: hay claves reasignadas y nombres repetidos dentro de un estado (secciones 4 y 7).
- `reto_y_datos.md`, «¿Qué es NS?»: en 2012 faltan 1,048 secciones que sí están en 2009 y 2015; en 66 municipios son más del 10% de su lista (sección 6).
- `reto_y_datos.md`, «Lo que falta verificar»: ya se sabe qué municipios se pueden comparar y por qué; falta contrastar los totales con el tablero.
- `PLAN.md`, Fase 2: anotar que se corre con `python ai/src/data_prep/fase2.py` y que sus salidas son `catalogo_municipios.csv`, `cambios_secciones.csv` y este reporte.

## Qué sigue

Fase 3: armar la tabla de municipios con este catálogo. El nombre sale de `nombre_municipio`, y las columnas `situacion_AAAA` dicen qué parte del historial de cada municipio se puede comparar.
