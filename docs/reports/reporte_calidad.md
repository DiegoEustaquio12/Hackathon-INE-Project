# Reporte de calidad: Fase 1 (carga y limpieza)

Lo genera `python ai/src/data_prep/fase1.py` a partir de los CSV de `data/raw/`. No se edita a mano: si algo cambia, se vuelve a correr el script.

La tabla limpia tiene **54,872,712 filas** de 192 archivos. Queda en `data/interim/ccpc/`, un Parquet por elección, y no se sube a GitHub. Ninguna fila se borró: las raras solo se marcan.

## Resultado

- ✅ Los 192 archivos traen las mismas 16 columnas, en el mismo orden.
- ✅ Se leyeron todas las filas: en cada archivo, filas leídas = líneas del archivo menos el encabezado.
- ✅ Cada archivo trae un solo estado y el año de su carpeta; los 32 estados aparecen una vez por elección.
- ✅ La fecha leída es la de cada elección.
- ✅ Filas que no cumplen LN = SV + NV + NS: 0.
- ✅ Filas con algún conteo negativo: 0.
- ✅ Filas repetidas (estado + sección + sexo + edad): 0.
- ✅ Filas con un código de SEXO o TIPOSEC inválido: 0.
- ✅ Secciones con más de un municipio, tipo o distrito dentro de su elección: 0.
- ✅ Secciones de cada elección iguales a los docs.
- ✅ Lista nominal nacional de cada elección igual a los docs.
- ✅ Participación nacional de cada elección igual a los docs (a un decimal).
- ✅ Aguascalientes 2021: LN 1,017,420, SV 489,469, NV 499,413, NS 28,538 y 49.5% (docs: LN 1,017,420, SV 489,469, NV 499,413, NS 28,538 y 49.5%).
- ✅ Aguascalientes 2024: LN 1,097,171, SV 626,084, NV 441,222, NS 29,865 y 58.7% (docs: LN 1,097,171, SV 626,084, NV 441,222, NS 29,865 y 58.7%).
- ✅ Personas con SEXO = 2 (no binario) en 2024: 105 (docs: 105).
- ✅ Secciones sin dato (SV + NV = 0) en 2024: 2,100 (docs: unas 2,100).
- ✅ No especificados en 2012: 0.2% de la lista nominal (docs: 0.2%).
- ✅ No especificados en 2021: el menor es COLIMA (1.4%) y el mayor CHIHUAHUA (12.7%) (docs: Colima 1.4%, Chihuahua 12.7%).
- ✅ Todas las elecciones quedaron con las mismas columnas y tipos de dato.

Las tres primeras se revisan al leer cada archivo: si alguna fallara, el script se detendría con un error.

## Cómo usar la tabla

Desde un script de `ai/src/data_prep/` (en un notebook de `ai/notebooks/`, antes agrega `sys.path.append("../src/data_prep")`):

```python
from ccpc import leer_tabla
df = leer_tabla(anios=[2018, 2021], columnas=["EDOCVE", "MPIOCVE", "SV", "NV"])
```

Pide solo las columnas que uses: las seis elecciones completas ocupan varios GB en memoria. Las tasas se calculan después de sumar (por ejemplo, por municipio), nunca promediando porcentajes.

## 1. Estructura

Cada elección son 32 archivos, uno por estado, con las mismas 16 columnas.

| Elección | Tipo | Filas | Secciones | Municipios | `FELECCION` en el archivo | Fecha leída |
|---|---|---|---|---|---|---|
| 2009 | intermedia | 8,706,843 | 64,934 | 2,458 | 5/7/2009 | 2009-07-05 |
| 2012 | presidencial | 8,604,456 | 65,599 | 2,455 | 1/7/2012 | 2012-07-01 |
| 2015 | intermedia | 9,106,059 | 68,362 | 2,458 | 7/6/2015 | 2015-06-07 |
| 2018 | presidencial | 9,251,122 | 68,408 | 2,463 | 1/7/2018 | 2018-07-01 |
| 2021 | intermedia | 9,430,502 | 68,812 | 2,468 | 6/6/2021 | 2021-06-06 |
| 2024 | presidencial | 9,773,730 | 70,751 | 2,477 | 06/02/2024 | 2024-06-02 |

La fecha se lee como día/mes/año hasta 2021 y como mes/día/año en 2024. Para saber de qué elección es cada fila se usa `AELEC`.

## 2. Códigos de sexo y tipo de sección

| Elección | Personas: hombres (0) | Mujeres (1) | No binario (2) | Filas: urbanas (U) | Mixtas (M) | Rurales (R) |
|---|---|---|---|---|---|---|
| 2009 | 37,353,906 | 40,127,925 | 0 | 5,415,966 | 802,990 | 2,487,887 |
| 2012 | 36,821,304 | 39,669,658 | 0 | 5,449,108 | 822,843 | 2,332,505 |
| 2015 | 40,219,786 | 43,343,676 | 0 | 5,827,491 | 865,402 | 2,413,166 |
| 2018 | 42,913,845 | 46,210,152 | 0 | 5,920,841 | 899,994 | 2,430,287 |
| 2021 | 45,067,547 | 48,464,586 | 0 | 6,074,241 | 919,109 | 2,437,152 |
| 2024 | 47,226,431 | 51,103,812 | 105 | 6,368,734 | 921,814 | 2,483,182 |

El código 2 (no binario) solo debe aparecer en 2024. Un código fuera de lo esperado quedaría marcado en `flag_codigo`.

## 3. Distritos vacíos

| Elección | `DEF` vacío: filas | `DEF`: secciones | `DEF`: personas | `DEL` vacío: filas | `DEL`: secciones | `DEL`: personas |
|---|---|---|---|---|---|---|
| 2009 | 28,477 | 318 | 1,522,844 | 28,477 | 318 | 1,522,844 |
| 2012 | 15,677 | 221 | 909,923 | 15,677 | 221 | 909,923 |
| 2015 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2018 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2021 | 0 | 0 | 0 | 0 | 0 | 0 |
| 2024 | 0 | 0 | 0 | 20,912 | 136 | 1,862,959 |

Un distrito vacío queda nulo; la fila y sus conteos se quedan. Así venían escritos: un espacio en `DEF` 2009, `DEL` 2009, `DEF` 2012, `DEL` 2012; celda vacía en `DEL` 2024.

Según el diccionario del INE, `DEF` y `DEL` de 2009 a 2021 vienen en el mapa de distritos DERFE 2021, y los de 2024 en el de 2023. O sea, el distrito de una fila de 2009 no es necesariamente el que se usó en esa elección.

## 4. Edades

| Elección | Mínima | Máxima | Menos de 18: filas | Menos de 18: personas | 101 a 120: filas | 101 a 120: personas | Más de 120: filas | Más de 120: personas |
|---|---|---|---|---|---|---|---|---|
| 2009 | 18 | 130 | 0 | 0 | 32,549 | 33,815 | 212 | 213 |
| 2012 | 18 | 132 | 0 | 0 | 10,266 | 10,469 | 52 | 53 |
| 2015 | 18 | 117 | 0 | 0 | 12,123 | 12,345 | 0 | 0 |
| 2018 | 18 | 137 | 0 | 0 | 10,269 | 10,417 | 51 | 51 |
| 2021 | 18 | 139 | 0 | 0 | 13,178 | 13,492 | 38 | 38 |
| 2024 | 18 | 140 | 0 | 0 | 12,873 | 13,179 | 18 | 18 |

Se marcan en `flag_edad` las filas con edad menor de 18 o mayor de 100. Sus conteos se quedan, cuentan en el grupo "60 o más" y `EDAD` no se modifica. Filas sin grupo de edad: 0.

## 5. Marcas

Filas marcadas por elección. Las marcas no borran nada: sirven para revisar y decidir después.

| Marca | Sí cuando | 2009 | 2012 | 2015 | 2018 | 2021 | 2024 | Total filas | Total personas |
|---|---|---|---|---|---|---|---|---|---|
| `flag_regla_ln` | LN no es igual a SV + NV + NS | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `flag_negativo` | algún conteo es negativo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `flag_duplicado` | estado + sección + sexo + edad se repite en la misma elección | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `flag_codigo` | SEXO o TIPOSEC traen un código que no corresponde | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `flag_edad` | la edad es menor de 18 o mayor de 100 | 32,761 | 10,318 | 12,123 | 10,320 | 13,216 | 12,891 | 91,629 | 94,090 |
| `flag_revision` | la fila tiene cualquiera de las marcas anteriores | 32,761 | 10,318 | 12,123 | 10,320 | 13,216 | 12,891 | 91,629 | 94,090 |

Primeros ejemplos de `flag_edad`:

| Elección | Estado | Municipio | Sección | Sexo | Edad | LN | SV | NV | NS |
|---|---|---|---|---|---|---|---|---|---|
| 2009 | AGUASCALIENTES | Aguascalientes | 8 | 1 | 101 | 1 | 0 | 1 | 0 |
| 2009 | AGUASCALIENTES | Aguascalientes | 12 | 0 | 106 | 1 | 0 | 1 | 0 |
| 2009 | AGUASCALIENTES | Aguascalientes | 15 | 0 | 107 | 1 | 0 | 1 | 0 |
| 2009 | AGUASCALIENTES | Aguascalientes | 18 | 1 | 101 | 1 | 0 | 1 | 0 |
| 2009 | AGUASCALIENTES | Aguascalientes | 21 | 1 | 101 | 1 | 1 | 0 | 0 |

## 6. Consistencia dentro de cada elección

Secciones que, dentro de una misma elección, aparecen con más de un valor (los vacíos cuentan como valor):

| Elección | Municipio | Tipo de sección | Distrito federal | Distrito local |
|---|---|---|---|---|
| 2009 | 0 | 0 | 0 | 0 |
| 2012 | 0 | 0 | 0 | 0 |
| 2015 | 0 | 0 | 0 | 0 |
| 2018 | 0 | 0 | 0 | 0 |
| 2021 | 0 | 0 | 0 | 0 |
| 2024 | 0 | 0 | 0 | 0 |

Si todo es 0, cada sección cae en un solo municipio dentro de su elección, así que sumar secciones por municipio no parte ninguna sección. Esto no dice nada de los cambios entre elecciones: eso lo revisa la Fase 2.

## 7. Cifras de "revisión rápida" de los docs

Participación = SV / (SV + NV) y abstención = NV / (SV + NV), sumando primero todo el país. `NS` queda fuera, como hace el INE.

| Elección | Secciones | Docs | Diferencia | Lista nominal | Docs | Diferencia | Participación | Docs | Abstención |
|---|---|---|---|---|---|---|---|---|---|
| 2009 | 64,934 | 64,934 | 0 | 77,481,831 | 77,481,831 | 0 | 44.1% | 44.1% | 55.9% |
| 2012 | 65,599 | 65,599 | 0 | 76,490,962 | 76,490,962 | 0 | 62.1% | 62.1% | 37.9% |
| 2015 | 68,362 | 68,362 | 0 | 83,563,462 | 83,563,462 | 0 | 47.1% | 47.1% | 52.9% |
| 2018 | 68,408 | 68,408 | 0 | 89,123,997 | 89,123,997 | 0 | 62.4% | 62.4% | 37.6% |
| 2021 | 68,812 | 68,812 | 0 | 93,532,133 | 93,532,133 | 0 | 51.8% | 51.8% | 48.2% |
| 2024 | 70,751 | 70,751 | 0 | 98,330,348 | 98,330,348 | 0 | 59.7% | 59.7% | 40.3% |

**No especificados (`NS`).** Los docs dicen que 2012 casi no tiene (0.2%) y que en 2021 va de 1.4% en Colima a 12.7% en Chihuahua.

| Elección | Sí votaron | No votaron | No especificado | % de la lista nominal | Estado con menos NS | Estado con más NS |
|---|---|---|---|---|---|---|
| 2009 | 33,316,974 | 42,298,963 | 1,865,894 | 2.4% | QUERETARO (0.6%) | AGUASCALIENTES (10.0%) |
| 2012 | 47,383,154 | 28,939,159 | 168,649 | 0.2% | CAMPECHE (0.0%) | YUCATAN (2.0%) |
| 2015 | 36,926,612 | 41,517,874 | 5,118,976 | 6.1% | TLAXCALA (1.1%) | QUINTANA ROO (18.6%) |
| 2018 | 51,784,399 | 31,249,856 | 6,089,742 | 6.8% | AGUASCALIENTES (1.4%) | SINALOA (16.9%) |
| 2021 | 46,389,189 | 43,099,624 | 4,043,320 | 4.3% | COLIMA (1.4%) | CHIHUAHUA (12.7%) |
| 2024 | 54,899,228 | 37,105,466 | 6,325,654 | 6.4% | CIUDAD DE MEXICO (1.9%) | CHIHUAHUA (14.9%) |

**Secciones sin dato:** secciones donde no se sabe de nadie si votó (`SV + NV = 0`). Su participación es desconocida, no cero. Los docs dicen que en 2024 son unas 2,100.

| Elección | Secciones sin dato | Personas en la lista |
|---|---|---|
| 2009 | 1,004 | 749,977 |
| 2012 | 82 | 43,596 |
| 2015 | 2,042 | 1,638,223 |
| 2018 | 2,517 | 1,727,261 |
| 2021 | 1,693 | 1,130,307 |
| 2024 | 2,100 | 1,588,642 |

La comparación de cada cifra con los docs está en el Resultado, al inicio.

## 8. Aguascalientes contra el tablero

Aguascalientes 2021 y 2024 ya se habían comparado con el tablero del INE (ambos sexos juntos).

| Elección | Fuente | LN | SV | NV | NS | Participación |
|---|---|---|---|---|---|---|
| 2021 | Este reporte | 1,017,420 | 489,469 | 499,413 | 28,538 | 49.5% |
| 2021 | Docs (tablero del INE) | 1,017,420 | 489,469 | 499,413 | 28,538 | 49.5% |
| 2024 | Este reporte | 1,097,171 | 626,084 | 441,222 | 29,865 | 58.7% |
| 2024 | Docs (tablero del INE) | 1,097,171 | 626,084 | 441,222 | 29,865 | 58.7% |

## 9. Nombres que cambian entre elecciones

Aquí no se corrige ningún nombre: se conservan como vienen y la Fase 2 decide qué hacer. Los municipios se identifican por clave (`EDOCVE` + `MPIOCVE`), no por nombre.

**Estados con más de un nombre:**

- Estado 9: DISTRITO FEDERAL (2009, 2012, 2015, 2018) · CIUDAD DE MEXICO (2021, 2024)

**Municipios:** 78 de 2,477 claves municipales aparecen con más de una escritura. En 38 solo cambian acentos, mayúsculas o espacios. Las otras 40 cambian en algo más (otro nombre, una abreviatura, una errata o nombres cruzados entre claves):

| Estado | Clave del municipio | Escrituras (años) |
|---|---|---|
| CAMPECHE (4) | 6 | Hopelchén (2009, 2012, 2015, 2018, 2021) · Hopelche}én (2024) |
| CAMPECHE (4) | 12 | Dzitblache (2021) · Dzitbalché (2024) |
| COAHUILA (5) | 7 | Cuatro Ciénegas (2009, 2012, 2015, 2018, 2021) · Cuatrociénegas (2024) |
| CHIAPAS (7) | 38 | Huitiupán (2009, 2012, 2015, 2018, 2021) · Huitiupaán (2024) |
| CHIAPAS (7) | 107 | Villa Comaltitlán (2009, 2012, 2015, 2018, 2021) · Villacomaltitlán (2024) |
| CHIAPAS (7) | 114 | Maravilla Tejenapa (2009, 2012, 2015, 2018) · Maravilla Tenejapa (2021, 2024) |
| CHIAPAS (7) | 120 | Emiliano Zapata (2018) · Rincón Chamula San Pedro (2021, 2024) |
| CHIAPAS (7) | 121 | Mezcalapa (2018) · El Parral (2021, 2024) |
| CHIAPAS (7) | 122 | El Parral (2018) · Emiliano Zapata (2021, 2024) |
| CHIAPAS (7) | 123 | Capitán Luis Ángel Vidal (2018) · Mezcalapa (2021, 2024) |
| CHIAPAS (7) | 124 | Rincón Chamula San Pedro (2018) · Honduras de la Sierra (2021, 2024) |
| CHIHUAHUA (8) | 8 | Batopilas (2009, 2012, 2015, 2018) · Batopilas de Manuel Gómez Morín (2021, 2024) |
| DURANGO (10) | 6 | General Simón Bolívar (2009, 2012, 2015, 2018, 2021) · Simón Bolívar (2024) |
| HIDALGO (13) | 50 | San Agustín Metzquititlán (2009, 2012, 2015, 2018, 2021) · San Agustón Metzquititlán (2024) |
| MICHOACAN (16) | 65 | Parácuaro (2009, 2012, 2015, 2018, 2024) · Paracho (2021) |
| MICHOACAN (16) | 66 | Paracho (2009, 2012, 2015, 2018, 2024) · Parácuaro (2021) |
| MORELOS (17) | 13 | Jonacatepec (2009, 2012, 2015, 2018, 2024) · Jonacatepec de Leandro Valle (2021) |
| NUEVO LEON (19) | 10 | El Carmen (2009, 2012, 2015, 2018, 2021) · Carmen (2024) |
| NUEVO LEON (19) | 14 | Doctor Arroyo (2009, 2012, 2015, 2018, 2021) · Dr. Arroyo (2024) |
| NUEVO LEON (19) | 15 | Doctor Coss (2009, 2012, 2015, 2018, 2021) · Dr. Coss (2024) |
| NUEVO LEON (19) | 16 | Doctor González (2009, 2012, 2015, 2018, 2021) · Dr. González (2024) |
| NUEVO LEON (19) | 20 | General Bravo (2009, 2012, 2015, 2018, 2021) · Gral. Bravo (2024) |
| NUEVO LEON (19) | 21 | General Escobedo (2009, 2012, 2015, 2018, 2021) · Gral. Escobedo (2024) |
| NUEVO LEON (19) | 22 | General Terán (2009, 2012, 2015, 2018, 2021) · Gral. Terán (2024) |
| NUEVO LEON (19) | 23 | General Treviño (2009, 2012, 2015, 2018, 2021) · Gral. Treviño (2024) |
| NUEVO LEON (19) | 24 | General Zaragoza (2009, 2012, 2015, 2018, 2021) · Gral. Zaragoza (2024) |
| NUEVO LEON (19) | 25 | General Zuazua (2009, 2012, 2015, 2018, 2021) · Gral. Zuazua (2024) |
| OAXACA (20) | 43 | Heroica Ciudad de Juchitán de Zaragoza (2009, 2012, 2015, 2018, 2024) · Juchitán de Zaragoza (2021) |
| OAXACA (20) | 121 | San Blas Atempa (2009, 2012, 2015, 2018, 2021) · Heroica Villa de San Blas Atempa (2024) |
| OAXACA (20) | 208 | San Juan Mixtepec (2009, 2012, 2015, 2018, 2024) · San Juan Mixtepec Dto 08 (2021) |
| OAXACA (20) | 209 | San Juan Mixtepec (2009, 2012, 2015, 2018, 2024) · San Juan Mixtepec Dto 26 (2021) |
| OAXACA (20) | 316 | San Pedro Mixtepec (2009, 2012, 2015, 2018, 2024) · San Pedro Mixtepec Dto 22 (2021) |
| OAXACA (20) | 317 | San Pedro Mixtepec (2009, 2012, 2015, 2018, 2024) · San Pedro Mixtepec Dto 26 (2021) |
| OAXACA (20) | 332 | Villa de Tututepec de Melchor Ocampo (2009, 2012, 2015, 2018) · Villa de Tututepec (2021, 2024) |
| OAXACA (20) | 459 | Santiago Chazumba (2009, 2012, 2015, 2018, 2024) · Villa de Santiago Chazumba (2021) |
| OAXACA (20) | 549 | Heroica Villa Tezoatlán de Segura y Luna, Cuna de (2009, 2012, 2015, 2018) · Heroica Villa Tezoatlán de Segura y Luna, Cuna de la Independencia de Oaxaca (2021, 2024) |
| OAXACA (20) | 562 | Villa Hidalgo (2009, 2012, 2015, 2018, 2021) · Villa Hidalgo Yalalag (2024) |
| TLAXCALA (29) | 37 | Ziltlaltépec de Trinidad Sánchez Santos (2009, 2012, 2015, 2018, 2021) · Zitlaltépec de Trinidad Sánchez Santos (2024) |
| VERACRUZ (30) | 10 | Alto Lucero de Gutiérrez Barrios (2009, 2012, 2015, 2018, 2021) · Alto Lucero de Gutiérrez Barios (2024) |
| VERACRUZ (30) | 47 | Cosamaloapan de Carpio (2009, 2012, 2015, 2018, 2021) · Cosamaloapan (2024) |

## 10. Columnas de la tabla

Las 16 primeras son las originales del INE, con su mismo nombre. Las nuevas van en minúsculas.

| Columna | Qué es | Tipo de dato |
|---|---|---|
| `AELEC` | Año de la elección | número entero |
| `FELECCION` | Fecha tal como viene en el archivo (en 2024 el mes va primero) | texto |
| `EDOCVE` | Clave del estado | número entero |
| `EDONOM` | Nombre del estado, como viene en el archivo | texto |
| `MPIOCVE` | Clave INE del municipio; junto con EDOCVE identifica al municipio | número entero |
| `MPIONOM` | Nombre del municipio, como viene en el archivo | texto |
| `SECCION` | Sección electoral; junto con EDOCVE identifica a la sección | número entero |
| `TIPOSEC` | Tipo de sección: U urbana, M mixta, R rural | texto |
| `DEF` | Distrito electoral federal (vacío = nulo) | número entero (puede estar vacío) |
| `DEL` | Distrito electoral local (vacío = nulo) | número entero (puede estar vacío) |
| `SEXO` | 0 hombre, 1 mujer, 2 no binario (solo en 2024) | número entero |
| `EDAD` | Edad en años, sin cambios | número entero |
| `LN` | Lista nominal: personas del grupo registradas para votar | número entero |
| `SV` | Sí votaron | número entero |
| `NV` | No votaron | número entero |
| `NS` | No especificado: no se sabe si votaron | número entero |
| `fecha_eleccion` | Nueva: la fecha leída con el formato de cada año | fecha |
| `tipo_eleccion` | Nueva: intermedia o presidencial | texto |
| `grupo_edad` | Nueva: etapa de vida del INE (18 a 24, 25 a 34, 35 a 44, 45 a 59, 60 o más) | texto |
| `flag_regla_ln` | Nueva: sí cuando LN no es igual a SV + NV + NS | sí/no |
| `flag_negativo` | Nueva: sí cuando algún conteo es negativo | sí/no |
| `flag_duplicado` | Nueva: sí cuando estado + sección + sexo + edad se repite en la misma elección | sí/no |
| `flag_codigo` | Nueva: sí cuando SEXO o TIPOSEC traen un código que no corresponde | sí/no |
| `flag_edad` | Nueva: sí cuando la edad es menor de 18 o mayor de 100 | sí/no |
| `flag_revision` | Nueva: sí cuando la fila tiene cualquiera de las marcas anteriores | sí/no |

## 11. Cambios propuestos para los docs

Los docs no se tocan en esta fase. Esto es lo que se propone cambiar cuando el equipo elija su versión de la Fase 1:

- `reto_y_datos.md`, «Panorama nacional»: las secciones, la lista nominal y la participación ya están confirmadas; se puede quitar «revisión rápida» y citar este reporte.
- `reto_y_datos.md`, «La regla que siempre se cumple»: confirmado, ninguna fila la falla.
- `reto_y_datos.md`, «Cosas a cuidar»: los distritos vacíos vienen como un espacio en `DEF` 2009, `DEL` 2009, `DEF` 2012, `DEL` 2012; celda vacía en `DEL` 2024 (sección 3).
- `reto_y_datos.md`, «¿Qué significa cada columna?»: según el diccionario del INE, `DEF` y `DEL` de 2009 a 2021 están en el mapa de distritos DERFE 2021 y los de 2024 en el de 2023.
- `reto_y_datos.md`, «Lo que cambia con el tiempo»: los nombres cambian entre elecciones (estado 9: DISTRITO FEDERAL (2009, 2012, 2015, 2018) · CIUDAD DE MEXICO (2021, 2024); 78 municipios con otra escritura), así que los municipios se identifican por clave (sección 9).
- `reto_y_datos.md`, «Cosas a cuidar»: las edades llegan hasta 140 años; se marcan las mayores de 100 (91,629 filas y 94,090 personas en las seis elecciones, sección 4).
- `reto_y_datos.md`, «¿Qué es NS?»: confirmado, en 2024 son exactamente 2,100 secciones sin dato.
- `PLAN.md`, Fase 1: anotar que la tabla queda en `data/interim/ccpc/` y que se lee con `leer_tabla()` de `ai/src/data_prep/ccpc.py`.

## Qué sigue

Fase 2: con esta tabla se revisa qué municipios se pueden comparar entre elecciones (municipios nuevos, cambios de clave o de límites y cambios en sus secciones).
