# Reto 2: riesgo de abstención por municipio (Hackathon INE)

> ## 🌐 Visor en vivo: **[celadon-babka-6b599e.netlify.app](https://celadon-babka-6b599e.netlify.app)**
>
> **Ahí están los resultados funcionando**, sin instalar nada: el mapa de los 2,477 municipios con el semáforo de abstención prevista para 2027, sin intervención y con intervención, un buscador de municipios, la ficha de cada uno con sus razones y la lista ordenable.

Este repositorio predice con un modelo de regresión la **tasa de abstención de cada municipio de México en la elección intermedia de 2027**. Usa los Conteos Censales de Participación Ciudadana (CCPC) del INE de 2009 a 2024. Con esa predicción se arma un **semáforo de riesgo** en dos escenarios, **sin intervención** y **con una intervención hipotética**, y se entregan los mapas y la base de datos.

## Contenido

1. [El reto en breve](#el-reto-en-breve)
2. [Resultados principales](#resultados-principales)
3. [Dónde está cada entregable](#dónde-está-cada-entregable)
4. [Cómo funciona](#cómo-funciona)
5. [Cómo reproducirlo](#cómo-reproducirlo)
6. [Visor web](#visor-web)
7. [Estructura del repositorio](#estructura-del-repositorio)
8. [Supuestos y limitaciones](#supuestos-y-limitaciones)
9. [Documentación](#documentación)

## El reto en breve

- **Problema.** El INE tiene recursos limitados para promover la participación. Necesita saber **dónde actuar primero**, antes de la elección.
- **Respuesta.** Un modelo que predice cuántas personas de la lista nominal no votarían en cada municipio en 2027. Los municipios se clasifican en rojo, amarillo y verde, y se simula cuánto cambiaría el mapa si el INE interviniera en los rojos.
- **Unidad.** El municipio: 2,477 en la elección más reciente.
- **Abstención.** `NV / (SV + NV)`: personas que no votaron entre las personas con dato conocido. El `NS` (no se sabe si votó) queda fuera. Primero se suman los conteos y después se divide; nunca se promedian porcentajes.
- **Sin información del futuro.** Para predecir una elección solo se usa lo que se sabía antes de ella.

## Resultados principales

**El modelo le gana al método simple** de repetir la última elección del mismo tipo. Fuente: [reporte del modelo](docs/reports/reporte_modelo.md).

| Prueba | Método | Error medio (pp) | Rojos detectados |
|---|---|---|---|
| Predecir 2021 con datos hasta 2018 (prueba principal) | **Modelo** | **8.61** | **76.1%** |
| | Repetir la última elección | 12.40 | 52.0% |
| Predecir 2021 dejando estados completos fuera | **Modelo** | **9.71** | **60.7%** |
| | Repetir la última elección | 12.40 | 52.0% |
| Predecir la presidencial 2024 (prueba secundaria) | Modelo | 6.68 | 74.5% |
| | Repetir la última elección | 5.70 | 78.2% |

- En la prueba principal, el modelo detecta **76 de cada 100 municipios que terminaron en rojo**, frente a 52 del método simple.
- Un remuestreo por estados confirma la ventaja: en 2021 el modelo yerra **3.79 pp menos** (intervalo del 95%: de 1.15 a 5.95).
- En 2024 el modelo no supera al método simple. Esa prueba es secundaria porque 2027 es intermedia, como 2021, y no decide la adopción. Se reporta tal cual.

**Semáforo 2027.** Fuente: [reporte de escenarios](docs/reports/reporte_fase8.md).

| Color | Abstención prevista | Municipios |
|---|---|---|
| 🔴 Rojo (alta) | 49.32% o más | 821 |
| 🟡 Amarillo (media) | de 36.93% a 49.32% | 821 |
| 🟢 Verde (baja) | menos de 36.93% | 823 |
| ⚪ Gris (sin datos suficientes) | — | 12 |

El mapa muestra 819 municipios rojos: Eldorado y Juan José Ríos (Sinaloa) son rojos, pero no tienen polígono en la cartografía de 2022 (ver [Supuestos y limitaciones](#supuestos-y-limitaciones)).

**Intervención hipotética en los municipios rojos**, con un efecto supuesto del 10%:

| Grupo al que se dirige | Municipios que salen del rojo | Reducción media de la abstención |
|---|---|---|
| Hombres | 173 de 821 (21.1%) | 2.76 pp |
| Jóvenes de 18 a 34 años | 129 de 821 (15.7%) | 2.29 pp |
| Zonas rurales | 105 de 821 (12.8%) | 1.40 pp |

El efecto de la intervención **es un supuesto declarado**, no una medición. Cada intervención se evalúa por separado y sus efectos no se suman. También se calcularon efectos de 5% y 15%.

## Dónde está cada entregable

| Entregable | Dónde |
|---|---|
| **Visor interactivo de los mapas** | **[celadon-babka-6b599e.netlify.app](https://celadon-babka-6b599e.netlify.app)** (código en [`web/`](web/)) |
| Mapa de escenarios con y sin intervención (GPKG y GeoJSON) y base de datos anonimizada (CSV y XLSX) | [`docs/deliverables/mapa_escenarios/`](docs/deliverables/mapa_escenarios/). Su [guía](docs/deliverables/mapa_escenarios/GUIA_DEL_ENTREGABLE.md) explica cada archivo y cómo abrirlo en QGIS |
| Comparaciones lado a lado, en PDF y PNG | [`docs/deliverables/mapa_escenarios/`](docs/deliverables/mapa_escenarios/) |
| Predicciones 2027 por municipio, con rango, razones y marcas de calidad | [`ai/artifacts/predicciones_2027.csv`](ai/artifacts/predicciones_2027.csv) |
| Código | Este repositorio |
| Reporte metodológico (PDF), presentación y cartas firmadas | Se entregan aparte; no están en este repositorio |

## Cómo funciona

```
CCPC del INE 2009–2024 (192 CSV: 32 estados × 6 elecciones)
  │  Fase 1  Carga y limpieza: una sola tabla, sin borrar filas; las filas raras se marcan
  │  Fase 2  Consistencia entre años: qué municipios conservan su territorio
  │  Fase 3  Tablas por municipio: una "foto" por elección con solo el pasado
  │  Fase 4  Análisis exploratorio: diez preguntas, un reporte
  │  Fase 5  Definiciones aprobadas por el equipo
  │  Fase 7  Modelo LightGBM, validación, calibración y explicación
  │  Fase 8  Semáforo y escenarios con intervención
  ▼
Mapas, base de datos y visor web
```

**El modelo, en cinco ideas:**

1. **Predice la distancia de cada municipio al nivel del país**, no el porcentaje directo. El nivel nacional cambia mucho entre elecciones (intermedias: 55.94% en 2009, 52.93% en 2015 y 48.16% en 2021) y no se puede anticipar con datos municipales. Para 2027 se supone el nivel de 2021 (48.16%) y se suma la distancia predicha.
2. **Aprende de cuatro fotos** (2015, 2018, 2021 y 2024). Cada una tiene solo lo que se sabía antes de esa elección.
3. **Usa 39 variables, todas del CCPC del INE**: historial de abstención, abstención por edad, sexo y tipo de sección, composición de la lista nominal, tamaño y calidad del dato. También se probaron variables del censo (ECEG 2010 y 2020 del INEGI), pero aumentaron el error de 7.72 a 8.03 pp, así que el modelo final no las usa.
4. **Se eligió antes de ver 2021.** Las columnas y los ajustes se escogieron solo con 2015 y 2018, validando por grupos de estados. Después se probó en 2021, en 2021 dejando estados fuera y en 2024.
5. **Es explicable.** Cada municipio trae las tres variables que más empujan su predicción, calculadas con TreeSHAP. Las de mayor peso son la abstención en la última presidencial y su diferencia con el país. Son aportes del modelo, no causas.

Cada predicción trae además un **rango del 80%**, que marca dónde el color es menos seguro. El semáforo usa **terciles** del escenario sin intervención, y esos mismos cortes se usan con intervención para que los colores se puedan comparar.

## Cómo reproducirlo

Necesitas **Python 3.12 o superior** y unos 4 GB libres. En macOS, LightGBM necesita OpenMP: `brew install libomp`.

```bash
# 1. Crear y activar el entorno (desde la raíz del repo)
python3.12 -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate

# 2. Instalar las librerías (versiones fijas)
pip install -r ai/requirements.txt

# 3. Descargar el CCPC a data/raw/ (~290 MB de descarga, ~3.5 GB descomprimidos)
python scripts/download_raw_data.py
```

Con el entorno activado, el comando es `python` en Mac, Linux y Windows. En Windows, si PowerShell no deja activar el entorno, corre una vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**El pipeline completo, en orden:**

```bash
python ai/src/data_prep/fase1.py          # Fase 1: tabla limpia en data/interim/ccpc/
python ai/src/data_prep/fase2.py          # Fase 2: consistencia entre años
python scripts/download_complementary_data.py   # ECEG 2010 y 2020 del INEGI, que la Fase 3 une como columnas candidatas
python ai/src/data_prep/fase3.py          # Fase 3: tablas por municipio en data/processed/
python scripts/comparar_totales_ine.py    # comprueba los totales contra el tablero oficial del INE
python scripts/ejecutar_eda.py            # Fase 4: análisis exploratorio (opcional para el modelo)
python ai/src/models/fase7.py             # Fase 7: modelo, validación y predicciones 2027
python ai/src/models/fase8.py             # Fase 8: semáforo y escenarios con intervención
python ai/src/geo/entregable_mapa.py      # mapa y base de datos del entregable
python -m unittest discover -s ai/tests -v   # pruebas
```

Detalles útiles:

- **Datos ya procesados.** Las tablas por municipio de `data/processed/` ya están en el repositorio. Para correr solo el modelo bastan los pasos 1 a 3 de instalación y después `fase7.py` y `fase8.py`, sin descargar el CCPC.
- **Descarga.** `download_raw_data.py` omite los años que ya están completos. `--years 2021 2024` baja solo esos años y `--force` vuelve a descargar.
- **Validación oficial.** `comparar_totales_ine.py` no necesita red y coincide en las 192 combinaciones estado–elección del tablero del INE ([evidencia](docs/reports/reporte_validacion_ine.md)).
- **Modelo.** `fase7.py` tarda unos minutos y escribe todo en `ai/artifacts/`: el modelo, las métricas, las predicciones y la configuración con versiones y huellas SHA256 de los datos. También regenera el [reporte del modelo](docs/reports/reporte_modelo.md). `fase8.py` no reentrena: lee esa predicción y escribe `ai/artifacts/fase8/` y el [reporte de escenarios](docs/reports/reporte_fase8.md).
- **Mapa del entregable.** `entregable_mapa.py` necesita los polígonos municipales 2022 (`mun22cw`, [CONABIO](http://geoportal.conabio.gob.mx/metadatos/doc/html/mun22cw.html)) en `data/external/mun22gw_c/`. Los polígonos no se versionan.
- **Notebook.** `jupyter lab ai/notebooks/00_exploracion_inicial.ipynb` abre la exploración inicial. Usa rutas relativas, así que se abre desde su propia carpeta.

## Visor web

**En línea: [celadon-babka-6b599e.netlify.app](https://celadon-babka-6b599e.netlify.app)**

Es una página estática (HTML, CSS y JavaScript con Leaflet) que solo muestra resultados ya calculados; no entrena ni recalcula nada. Permite:

- ver el **mapa sin intervención** y el **mapa con intervención**, elegir el grupo (jóvenes, hombres o rural) y el efecto (5, 10 o 15%);
- **comparar** los dos mapas lado a lado o con una cortina;
- **buscar** un municipio o estado y abrir su ficha: abstención prevista, rango, color, cambio con la intervención y sus tres razones;
- ver la **lista** de municipios ordenable y filtrable, y exportar el mapa o los datos.

Para abrirlo en tu computadora, usa un servidor local (con doble clic no carga los datos):

```bash
cd web && python3 -m http.server 8000
```

Luego abre `http://localhost:8000/`. Si cambian las predicciones, `web/make_escenarios.py` regenera `escenarios.json`; el comando exacto está al inicio del archivo.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `data/raw/` | CSV originales del CCPC, una carpeta por elección. **No se versiona** (se descarga con el script) |
| `data/interim/` | Tabla limpia en Parquet (Fases 1 y 2). **No se versiona** |
| `data/processed/` | Tablas por municipio y elección, tablas de entrenamiento y de 2027, y evidencia de la validación oficial. **Se versiona y se entrega** |
| `data/external/` | Polígonos municipales y fuentes externas. **No se versiona** |
| `ai/src/data_prep/` | Fases 1 a 3: carga, limpieza, consistencia y tablas por municipio |
| `ai/src/eda/` | Fase 4: un script por pregunta (`eda_p1.py` a `eda_p10.py`) |
| `ai/src/models/` | Fase 7 (`fase7.py`: modelo, validación, calibración y explicación) y Fase 8 (`fase8.py`: semáforo y escenarios) |
| `ai/src/geo/` | Genera el entregable del mapa |
| `ai/artifacts/` | Modelo guardado, métricas, predicciones 2027 y escenarios (`fase8/`) |
| `ai/tests/` | Pruebas automáticas |
| `ai/notebooks/` | Exploración inicial |
| `web/` | Visor web publicado en Netlify, con sus datos |
| `docs/` | Documentación del reto, plan, reportes, EDA y entregables |
| `scripts/` | Descarga de datos, validación oficial y ejecutor del EDA |

## Supuestos y limitaciones

- **Nivel nacional de 2027.** Se supone igual al de 2021 (48.16%). El orden de los municipios es robusto, pero la cifra puntual depende de ese supuesto. El reporte del modelo incluye escenarios de ±5 pp y otras tendencias.
- **El efecto de la intervención no se puede estimar con estos datos.** Es un supuesto declarado (5, 10 o 15%) y se reporta como tal.
- **"Sin intervención" no significa "sin INE".** Los datos ya incluyen todo lo que el INE hizo hasta 2024; el escenario supone que todo sigue igual.
- **Pocas elecciones para validar.** Hay cuatro fotos para entrenar y una sola intermedia (2021) para decidir.
- **Municipios con pocos datos.** Los municipios con menos de 500 personas con dato o mucho `NS` reciben predicción, pero llevan una marca de calidad. Ningún municipio se borra.
- **Cartografía.** Los polígonos son de 2022. Eldorado y Juan José Ríos (Sinaloa) se crearon en 2021 y no tienen polígono propio, pero sus datos están en la base.
- **Solo datos agregados.** Todo está agregado por municipio; nunca se usan datos de personas.

## Documentación

| Documento | Para qué |
|---|---|
| [docs/reto_y_datos.md](docs/reto_y_datos.md) | El reto, los entregables, qué traen los datos del CCPC y el glosario. **Empieza aquí** |
| [docs/PLAN.md](docs/PLAN.md) | Las fases del trabajo y qué produce cada una |
| [docs/reports/reporte_modelo.md](docs/reports/reporte_modelo.md) | Modelo: selección, pruebas, calibración, rangos y explicación |
| [docs/reports/reporte_fase8.md](docs/reports/reporte_fase8.md) | Semáforo y escenarios con intervención |
| [docs/EDA/reporte_eda.md](docs/EDA/reporte_eda.md) | Análisis exploratorio (diez preguntas) |
| [docs/reports/reporte_validacion_ine.md](docs/reports/reporte_validacion_ine.md) | Comparación con los totales oficiales del INE |
| [docs/reports/reporte_calidad.md](docs/reports/reporte_calidad.md), [reporte_consistencia.md](docs/reports/reporte_consistencia.md) | Calidad de los datos y consistencia entre años |
| [docs/reports/diccionario_datos.md](docs/reports/diccionario_datos.md) | Qué significa cada columna |
| [docs/reports/reporte_externos.md](docs/reports/reporte_externos.md) | Variables del censo (ECEG) que se evaluaron |

### Nota técnica: saltos de línea

[`.gitattributes`](.gitattributes) fija saltos de línea **LF** para el código y los documentos, y trata los Parquet como binarios. `data/processed/totales_oficiales_ine.csv` es la excepción (`-text`): Git conserva sus bytes originales porque la validación oficial comprueba su huella SHA256. No hace falta cambiar la configuración global de Git.
