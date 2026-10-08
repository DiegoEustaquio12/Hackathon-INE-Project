# Reto 2: riesgo de abstención (Hackathon INE)

Modelo de regresión que predice la tasa de abstención por municipio con los datos 2009–2024 del CCPC del INE, en dos escenarios (sin y con intervención), y presenta los resultados en mapas con semáforo. **Ya definimos que una zona del proyecto es un municipio.**

Todos los campos de los archivos del INE están disponibles para el análisis y la preparación de variables, incluidos edad, sexo, tipo de sección, distritos, conteos y los demás campos. No se incorporan fuentes externas. La agregación y selección de predictores se evalúa en las fases correspondientes, usando solo información disponible antes de la elección que se busca predecir.

El contexto del reto, los entregables y la explicación de los datos están en [docs/reto_y_datos.md](docs/reto_y_datos.md). El plan de trabajo por fases está en [docs/PLAN.md](docs/PLAN.md). Si acabas de llegar al equipo, léelos en ese orden.

**Trabajo inmediato:** la Fase 1 de carga y limpieza que ya está planteada en el [plan](docs/PLAN.md). Las demás definiciones de la Fase 5 siguen pendientes antes de modelar.

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

### Backend (fase final, opcional)

Tiene sus propias librerías, porque solo sirve resultados ya calculados y no entrena modelos:

```bash
pip install -r backend/requirements.txt
```

## Estructura

| Carpeta | Contenido | Fase del plan |
|---|---|---|
| `data/raw/` | CSV originales del CCPC, un directorio por elección (`ConteosCensales2009/` … `2024/`). **No se versiona** | 1 |
| `data/interim/` | Tabla unificada y limpia (Parquet). **No se versiona** | 1–2 |
| `data/processed/` | Tabla de análisis por municipio y elección, y tabla de escenarios municipales, agregadas y anonimizadas. **Se versiona y se entrega** | 3, 8 |
| `data/external/` | Cartografía del INE para los polígonos municipales, si el INE autoriza su uso. **No se versiona** | 6 |
| `ai/notebooks/` | Exploración y EDA | 4 |
| `ai/src/data_prep/` | Carga, limpieza, consistencia entre años, tabla de análisis | 1–3 |
| `ai/src/geo/` | Unión de polígonos con la tabla por estado y municipio | 6 |
| `ai/src/models/` | Entrenamiento, validación y explicación | 7 |
| `ai/src/scenarios/` | Escenarios, semáforo y brecha intermedia vs presidencial | 8 |
| `ai/artifacts/` | Modelo guardado, métricas y predicciones | 7 |
| `backend/app/` | API FastAPI (opcional) que **solo lee** `data/processed/` | fase final |
| `frontend/` | Interfaz con los cuatro mapas (opcional) | fase final |
| `docs/reports/` | `reporte_calidad.md`, `reporte_eda.md`, diccionario de datos | 1–4 |
| `docs/deliverables/` | Reporte metodológico (PDF), presentación y cartas firmadas | — |
| `scripts/` | Utilidades del repo, como la descarga de datos | — |
