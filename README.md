# Reto 2: riesgo de abstención (Hackathon INE)

Modelo que estima el riesgo de abstención por sección electoral con el historial 2009–2024 del CCPC, en dos escenarios (sin y con intervención), y lo presenta en mapas con semáforo.

El contexto del reto, los entregables y la explicación de los datos están en [docs/reto_y_datos.md](docs/reto_y_datos.md). El plan técnico por fases está en [docs/PLAN.md](docs/PLAN.md).

## Cómo empezar

Necesitas **Python 3.12 o superior** y unos 4 GB libres en disco.

```bash
# 1. Crear y activar el entorno (desde la raíz del repo)
python3 -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate

# 2. Instalar las librerías
pip install -r ai/requirements.txt

# 3. Descargar los datos a data/raw/ (~290 MB de descarga, ~3.5 GB ya descomprimidos)
python3 scripts/download_raw_data.py

# 4. Abrir el notebook
jupyter lab ai/notebooks/00_exploracion_inicial.ipynb
```

Pasos 1 y 2 se hacen una sola vez; en las siguientes sesiones solo activa el entorno (`source .venv/bin/activate`).

**Si `python3 --version` muestra 3.9 o 3.10** (es lo normal en un Mac sin configurar), instala una versión nueva (`brew install python@3.12`) y crea el entorno con ella: `python3.12 -m venv .venv`. En Windows: `py -3.12 -m venv .venv`.

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
| `data/processed/` | Tabla de análisis y tabla de escenarios, agregadas y anonimizadas. **Se versiona y se entrega** | 3, 8 |
| `data/external/` | Cartografía electoral y datos del Censo, si el INE los autoriza. **No se versiona** | 6 |
| `ai/notebooks/` | Exploración y EDA | 4 |
| `ai/src/data_prep/` | Carga, limpieza, consistencia entre años, tabla de análisis | 1–3 |
| `ai/src/geo/` | Unión de polígonos con la tabla por estado y sección | 6 |
| `ai/src/models/` | Entrenamiento, validación y explicación | 7 |
| `ai/src/scenarios/` | Escenarios, semáforo y brecha intermedia vs presidencial | 8 |
| `ai/artifacts/` | Modelo guardado, métricas y predicciones | 7 |
| `backend/app/` | API FastAPI (opcional) que **solo lee** `data/processed/` | fase final |
| `frontend/` | Interfaz con los cuatro mapas (opcional) | fase final |
| `docs/reports/` | `reporte_calidad.md`, `reporte_eda.md`, `DECISIONES.md`, diccionario de datos | 1–5 |
| `docs/deliverables/` | Reporte metodológico (PDF), presentación y cartas firmadas | — |
| `scripts/` | Utilidades del repo, como la descarga de datos | — |
