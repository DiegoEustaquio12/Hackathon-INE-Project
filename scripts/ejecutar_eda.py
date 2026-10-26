"""Ejecuta las diez preguntas en paralelo y genera docs/EDA/reporte_eda.md.

Uso: python scripts/ejecutar_eda.py
     python scripts/ejecutar_eda.py --procesos 4

Utiliza el mismo Python del entorno activo. Los procesos guardan sus secciones
por separado; el reporte se sustituye únicamente cuando terminan todos con éxito.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

ROOT = Path(__file__).resolve().parents[1]
EDA = ROOT / "ai/src/eda"
sys.path.insert(0, str(EDA))
from eda_common import MAP, RESULTS, YEARS, write_report

CONSOLE_LOCK = Lock()


def prerequisites(data):
    files = [data / name for name in ("municipio_eleccion.parquet", "tabla_municipios_entrenamiento.parquet",
                                      "tabla_municipios_2027.parquet", "catalogo_municipios.csv")]
    files += [ROOT / f"data/interim/ccpc/ccpc_{year}.parquet" for year in YEARS]
    files += [ROOT / "data/interim/secciones.parquet"]
    missing = [str(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p) for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError("Faltan insumos de las fases 1–3:\n" + "\n".join(missing))


def run_one(number, data, out, fragments, env):
    command = [sys.executable, "-u", str(EDA / f"eda_p{number}.py"), str(data),
               "--salida", str(out), "--fragmento", str(fragments / f"p{number}.json")]
    log = out / f"p{number}_salida.log"
    with CONSOLE_LOCK:
        print(f"[p{number}] Iniciando…", flush=True)
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, env=env)
    if result.returncode:
        return number, f"Pregunta {number}: código {result.returncode}. Revisa {log}.\n" + log.read_text(encoding="utf-8")[-2500:]
    fragment = fragments / f"p{number}.json"
    if not fragment.is_file():
        return number, f"Pregunta {number}: no produjo su sección del reporte. Revisa {log}."
    with CONSOLE_LOCK:
        print(f"[p{number}] Completada.", flush=True)
    return number, None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--procesos", type=int, choices=range(1, 11), default=10, metavar="1–10")
    parser.add_argument("--datos", type=Path, default=ROOT / "data/processed")
    parser.add_argument("--salida", type=Path, default=RESULTS)
    args = parser.parse_args(argv)
    data, out = args.datos.resolve(), args.salida.resolve()
    try:
        prerequisites(data)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    # La descarga debe terminar antes de que la pregunta 10 abra los polígonos.
    print("Comprobando cartografía de la pregunta 10…", flush=True)
    download = subprocess.run([sys.executable, str(ROOT / "scripts/descargar_cartografia_eda.py")], cwd=ROOT)
    if download.returncode:
        print("No se pudo preparar la cartografía; se conserva el reporte anterior.", file=sys.stderr)
        return 1
    if not MAP.is_file():
        print(f"No se encontró el mapa esperado: {MAP}", file=sys.stderr)
        return 1
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    # Diez procesos ya trabajan a la vez: evitar que cada librería cree más hilos.
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[variable] = "1"
    with tempfile.TemporaryDirectory(prefix="ine-eda-") as temporary:
        fragments = Path(temporary)
        failures = []
        with ThreadPoolExecutor(max_workers=args.procesos) as executor:
            futures = [executor.submit(run_one, number, data, out, fragments, env) for number in range(1, 11)]
            for future in as_completed(futures):
                try:
                    number, error = future.result()
                except Exception as exc:
                    failures.append(str(exc))
                    continue
                if error:
                    failures.append(error)
        if failures:
            print("\n".join(failures), file=sys.stderr)
            print("El reporte anterior se conserva. Corrige el error y vuelve a ejecutar.", file=sys.stderr)
            return 1
        sections = {}
        for number in range(1, 11):
            payload = json.loads((fragments / f"p{number}.json").read_text(encoding="utf-8"))
            if payload["pregunta"] != number or not payload["seccion"].startswith(f"## Pregunta {number}."):
                raise ValueError(f"Sección inválida para la pregunta {number}")
            sections[number] = payload["seccion"]
        write_report(sections, out)
    print("\nListo: docs/EDA/reporte_eda.md contiene las diez preguntas.")
    print(f"Tablas, fuentes y salidas por pregunta: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
