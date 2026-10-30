# Reto 2: riesgo de abstención (Hackathon INE)

Modelo de regresión que predice la tasa de abstención por municipio con los datos 2009–2024 del CCPC del INE, en dos escenarios (sin y con intervención), y presenta los resultados en mapas con semáforo. **Ya definimos que una zona del proyecto es un municipio.**

Todos los campos de los archivos del INE están disponibles para el análisis y la preparación de variables, incluidos edad, sexo, tipo de sección, distritos, conteos y los demás campos. Como fuentes externas sociodemográficas se incorporan los ECEG 2010 y 2020 del INEGI, eligiendo para cada fila el censo más reciente anterior a la elección objetivo; no se usan los Censos Económicos porque sus datos abiertos son solo nacionales. La agregación y selección de predictores se evalúa en las fases correspondientes, usando solo información disponible antes de la elección que se busca predecir.

El contexto del reto, los entregables y la explicación de los datos están en [docs/reto_y_datos.md](docs/reto_y_datos.md). El plan de trabajo por fases está en [docs/PLAN.md](docs/PLAN.md). Si acabas de llegar al equipo, léelos en ese orden.

Las fases 1 a 3 ya tienen sus entregables; la validación externa de la Fase 2 coincide en las 192 combinaciones estado–elección del tablero del INE ([evidencia](docs/reports/reporte_validacion_ine.md)). La Fase 4 tiene análisis reproducibles para las diez preguntas y un [reporte único](docs/EDA/reporte_eda.md). Azael aprobó el 29/10/2026 los valores de la Fase 5 para modelar, y las intervenciones van como las propuso Diego. La Fase 7 ya genera las predicciones; siguen pendientes los mapas y el semáforo.

## Cómo empezar

Necesitas **Python 3.12 o superior** y unos 4 GB libres en disco.

```bash
# 1. Crear el entorno (una sola vez, desde la raíz del repo)
python3 -m venv .venv              # en Windows: py -3.12 -m venv .venv

# 2. Activar el entorno (cada vez que abras una terminal nueva)
source .venv/bin/activate          # en Windows: .venv\Scripts\activate

# 3. Instalar las librerías (una sola vez)
pip install -r ai/requirements.txt

# 4. Descargar los datos a data/raw/ (~290 MB de descarga, ~3.5 GB ya descomprimidos)
python scripts/download_raw_data.py

# 5. Abrir el notebook
jupyter lab ai/notebooks/00_exploracion_inicial.ipynb
```

Con el entorno activado, el comando es `python` en Mac, Linux y Windows.

### Entrenar el modelo (Fase 7)

Requiere las tres tablas canónicas `.parquet` de `data/processed/`, producidas por Fase 3. En macOS instala OpenMP una sola vez con `brew install libomp` ([instrucciones de LightGBM](https://pypi.org/project/lightgbm/4.7.0/)).

```bash
python ai/src/models/fase7.py
python -m unittest discover -s ai/tests -v
```

`--sin-censo` elimina el bloque candidato ECEG de la selección y de todos los ajustes; `--minimo 500` configura el mínimo de personas con respuesta para entrenar. Las 2,477 predicciones se conservan aun para municipios con pocos casos. La corrida completa tarda unos minutos; los resultados anteriores se conservan mientras se calcula y valida la nueva corrida.

El modelo aprende la distancia de cada municipio al país. La selección de columnas, ajustes y árboles usa solo 2015/2018; las pruebas decisivas predicen 2021 por tiempo y dejando estados completos fuera. La calibración se ajusta con predicciones fuera de fold: A y B usan 2015/2018, C usa 2015/2018/2021 y la corrida final usa las cuatro fotos. Si la variante calibrada no supera A y B, se prueba la sin calibrar; si ninguna supera, se publica repetir la última intermedia. La prueba de 2024 es secundaria y tiene una tolerancia pre-registrada de 0.3 puntos: si el modelo empeora más, el reporte recomienda una mezcla o un modelo más simple, sin cambiar automáticamente la adopción. El supuesto nacional de 2027 es el de 2021 (48.16% redondeado); el reporte incluye escenarios ±5 puntos, tendencia de las intermedias, último cambio y rangos municipales del 80% que no cuentan el error del nivel del país.

**Resultado:** el modelo usa 39 columnas de historial y de la lista nominal; ni las del EDA ni las del censo mejoraron la selección. Con la variante calibrada, en 2021 el error simple/pesado baja de 12.40/8.46 a **8.61/6.02 puntos**; dejando estados fuera, a **9.71/6.17**. LightGBM gana las dos pruebas y se publica. La calibración reduce el MAE simple de A y B; el ponderado queda prácticamente igual. La calibración final con las cuatro fotos expande la distancia (pendiente 1.083). En la comprobación secundaria de 2024 el modelo pierde frente a repetir la presidencial anterior (6.68 contra 5.70 puntos), por encima de la tolerancia de 0.3 puntos; el reporte recomienda evaluar una mezcla o un modelo más simple, sin cambiar automáticamente la adopción.

Las salidas están en `ai/artifacts/`: `predicciones_2027.parquet` y `.csv` copian las columnas originales, llenan `abstencion_objetivo` y agregan abstención, participación, rangos, razones y marcas de calidad. `modelo_2027.txt` guarda el candidato; `modelo_config.json` registra versiones, columnas, parámetros, rango, calibración, nivel nacional y huellas SHA256. También se guardan selección, pruebas, sensibilidades, explicaciones, escenarios nacionales, predicciones fuera de fold, calibración e intervalos bootstrap. El [reporte del modelo](docs/reports/reporte_modelo.md) se genera leyendo esos archivos. Las tablas de `data/processed/` no se modifican y no se ejecuta Fase 8.

**Si `python3 --version` muestra 3.9 o 3.10** (es lo normal en un Mac sin configurar), instala una versión nueva (`brew install python@3.12`) y crea el entorno con ella: `python3.12 -m venv .venv`.

**Si PowerShell no te deja activar el entorno** (Windows), corre una sola vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` y vuelve a intentarlo.

**Si usas VS Code,** abre el notebook y elige como kernel el de `.venv`. No hace falta Jupyter Lab.

El notebook usa rutas relativas (`../../data/raw`), así que debe abrirse desde su propia carpeta. Jupyter Lab y VS Code lo hacen así por defecto.

### Descarga de datos

`scripts/download_raw_data.py` baja los `.zip` del [CCPC](https://ine.mx/transparencia/datos-abiertos/visualizacion-datos/conteos-censales-participacion/) y deja todo en `data/raw/ConteosCensalesAAAA/`, con los mismos nombres de archivo que usa el equipo. No necesita instalar nada.

- Omite los años que ya tengas completos (32 CSV y el diccionario).
- Si algo falla, vuelve a correrlo: solo repite los años que faltan.
- `--years 2021 2024` baja solo esas elecciones.
- `--force` vuelve a descargar un año aunque ya exista.

### Validar los totales de la Fase 2

Con la salida local `data/interim/secciones.parquet` ya generada:

```bash
python scripts/comparar_totales_ine.py
```

No necesita red: usa las cifras oficiales normalizadas y su manifiesto, guardados en `data/processed/`. Compara los 32 estados de las seis elecciones, genera `comparacion_totales_ine.csv` y actualiza el [reporte de validación](docs/reports/reporte_validacion_ine.md). Devuelve un código de error si hay diferencias o falta evidencia.

Para obtener una captura nueva del tablero público y reconstruir los agregados oficiales:

```bash
python scripts/descargar_evidencia_ine.py --tablero
python scripts/comparar_totales_ine.py --normalizar
```

Las respuestas originales quedan en `data/external/validacion_ine/` (excluido de Git); el CSV oficial y `fuentes_totales_ine.json` conservan las cifras, fecha, filtros y huellas de la consulta. No se modifican las tablas de análisis ni de entrenamiento.

### Ejecutar el análisis exploratorio (preguntas 1 a 10)

Con las fases 1 a 3 ya ejecutadas y el entorno activado:

```bash
python scripts/ejecutar_eda.py
```

El ejecutor usa el Python del entorno activo, comprueba o descarga la cartografía con `scripts/descargar_cartografia_eda.py` y corre `ai/src/eda/eda_p1.py` a `eda_p10.py` en paralelo. Cada pregunta guarda sus tablas y su salida de terminal en `docs/EDA/resultados/`. Cuando las diez terminan correctamente, reúne sus secciones en `docs/EDA/reporte_eda.md`. Si falla una pregunta, conserva el reporte anterior y muestra dónde revisar el error.

Para reducir los procesos simultáneos o repetir una pregunta:

```bash
python scripts/ejecutar_eda.py --procesos 4
python ai/src/eda/eda_p5.py
```

La ejecución individual actualiza únicamente su sección del mismo reporte. Para ejecutar la pregunta 10 por separado, prepara primero el mapa con `python scripts/descargar_cartografia_eda.py`. Las figuras se guardan en `docs/EDA/`. Los comandos anteriores de las preguntas 1 a 3 siguen disponibles como entradas compatibles.

### Backend (fase final, opcional)

Tiene sus propias librerías, porque solo sirve resultados ya calculados y no entrena modelos:

```bash
pip install -r backend/requirements.txt
```

## Saltos de línea y Git

El archivo [`.gitattributes`](.gitattributes) fija saltos de línea **LF** para Python, Markdown, JSON y notebooks, tanto en Windows como en Linux y macOS. Esto evita conversiones a CRLF y diferencias de formato entre integrantes del equipo. Las reglas del repositorio prevalecen sobre `core.autocrlf`; no hace falta cambiar la configuración global de Git.

Los archivos Parquet se tratan como binarios. `data/processed/totales_oficiales_ine.csv` tiene una excepción `-text`: Git conserva sus bytes originales porque la validación oficial comprueba su SHA256. Cambiar sus saltos de línea también cambiaría esa huella, aunque las cifras fueran iguales. Para ese archivo, la comprobación de espacios de Git reconoce CRLF como terminación válida y conserva las comprobaciones habituales de espacios sobrantes.

Al editar los archivos de código y documentación, configura el editor para guardar con LF. Puedes consultar las reglas y el formato actual con:

```bash
git check-attr text eol -- ai/tests/test_validacion_ine.py scripts/descargar_evidencia_ine.py
git ls-files --eol
```

Si Git ya había preparado el CSV oficial antes de añadir estas reglas, actualiza únicamente ese archivo en el área de preparación:

```bash
git add --renormalize -- data/processed/totales_oficiales_ine.csv
```

Evita una normalización masiva de los datos: esta excepción permite conservar la evidencia sin cambiar las tablas de análisis.

## Estructura

| Carpeta | Contenido | Fase del plan |
|---|---|---|
| `data/raw/` | CSV originales del CCPC, un directorio por elección (`ConteosCensales2009/` … `2024/`). **No se versiona** | 1 |
| `data/interim/` | Tabla unificada y limpia (Parquet). **No se versiona** | 1–2 |
| `data/processed/` | Tabla de análisis por municipio y elección, y tablas municipales de entrenamiento y 2027 (con features ECEG), agregadas y anonimizadas. **Se versiona y se entrega** | 3, 8 |
| `data/external/` | Cartografía del INE para los polígonos municipales, si el INE autoriza su uso. **No se versiona** | 6 |
| `ai/notebooks/` | Exploración interactiva de los datos | 4 |
| `ai/src/eda/` | Un script por pregunta (`eda_p1.py` … `eda_p10.py`) | 4 |
| `ai/src/data_prep/` | Carga, limpieza, consistencia entre años, tabla de análisis | 1–3 |
| `ai/src/geo/` | Unión de polígonos con la tabla por estado y municipio | 6 |
| `ai/src/models/` | Entrenamiento, validación y explicación | 7 |
| `ai/src/scenarios/` | Escenarios, semáforo y brecha intermedia vs presidencial | 8 |
| `ai/artifacts/` | Modelo guardado, métricas y predicciones | 7 |
| `backend/app/` | API FastAPI (opcional) que **solo lee** `data/processed/` | fase final |
| `frontend/` | Interfaz con los dos mapas, sin y con intervención (opcional) | fase final |
| `docs/reports/` | Reportes de calidad, consistencia, validación y diccionario de datos | 1–3 |
| `docs/EDA/` | `reporte_eda.md`, gráficas y resultados por pregunta | 4 |
| `docs/deliverables/` | Reporte metodológico (PDF), presentación y cartas firmadas | — |
| `scripts/` | Utilidades del repo, como la descarga de datos | — |
