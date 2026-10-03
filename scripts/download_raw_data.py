#!/usr/bin/env python3
"""Descarga los datos del CCPC (INE) y los deja en data/raw/ con la estructura esperada:

    data/raw/ConteosCensales2009/datosabiertos_deceyec_conteoscensales2009_ags.csv
    data/raw/ConteosCensales2009/01_descripcioncampos_conteoscensales2009.txt
    ...

Solo usa la biblioteca estándar, no hay nada que instalar.

Uso (desde cualquier carpeta):
    python scripts/download_raw_data.py                    # las seis elecciones
    python scripts/download_raw_data.py --years 2021 2024  # solo algunas
    python scripts/download_raw_data.py --force            # vuelve a descargar aunque ya estén

Los años que ya están completos (32 CSV + el diccionario) se omiten.
"""
import argparse
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

BASE = "https://ine.mx/wp-content/uploads"
# Año -> carpeta de subida en ine.mx (los enlaces vienen de docs/reto_y_datos.md)
UPLOAD_PATH = {
    2024: "2025/08",
    2021: "2022/04",
    2018: "2022/04",
    2015: "2022/04",
    2012: "2022/04",
    2009: "2022/04",
}
EXPECTED_CSV = 32  # un CSV por entidad federativa
EXPECTED_TXT = 1   # 01_descripcioncampos_conteoscensalesAAAA.txt
RETRIES = 3
DEFAULT_DEST = Path(__file__).resolve().parents[1] / "data" / "raw"


def zip_url(year: int) -> str:
    return f"{BASE}/{UPLOAD_PATH[year]}/DatosAbiertos_DECEyEC_ConteosCensales{year}.zip"


def count_files(folder: Path) -> tuple[int, int]:
    if not folder.is_dir():
        return 0, 0
    return len(list(folder.glob("*.csv"))), len(list(folder.glob("*.txt")))


def is_complete(folder: Path) -> bool:
    return count_files(folder) == (EXPECTED_CSV, EXPECTED_TXT)


def download(url: str, target: Path) -> None:
    """Baja `url` a `target` mostrando el avance; reintenta si la red falla."""
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, open(target, "wb") as out:
                total = int(resp.headers.get("Content-Length") or 0)
                done = 0
                while chunk := resp.read(1024 * 256):
                    out.write(chunk)
                    done += len(chunk)
                    if total:
                        print(f"\r  descargando... {done / total:6.1%} ({done / 1e6:.0f}/{total / 1e6:.0f} MB)",
                              end="", flush=True)
            print()
            return
        except OSError as exc:
            print(f"\n  intento {attempt}/{RETRIES} falló: {exc}")
            if attempt == RETRIES:
                raise
            time.sleep(2 * attempt)


def extract(zip_path: Path, dest_folder: Path) -> None:
    """Extrae solo los .csv/.txt, sin la carpeta intermedia que trae el .zip."""
    dest_folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad:
            raise zipfile.BadZipFile(f"archivo dañado dentro del zip: {bad}")
        for member in zf.infolist():
            if member.is_dir():
                continue
            # Se usa solo el nombre del archivo: evita rutas raras y quita la carpeta del zip
            name = PurePosixPath(member.filename).name
            if name.startswith(".") or not name.lower().endswith((".csv", ".txt")):
                continue
            part = dest_folder / (name + ".part")
            with zf.open(member) as src, open(part, "wb") as out:
                shutil.copyfileobj(src, out)
            part.replace(dest_folder / name)


def fetch_year(year: int, dest: Path, force: bool) -> bool:
    folder = dest / f"ConteosCensales{year}"
    if is_complete(folder) and not force:
        print(f"[{year}] ya está completo en {folder.relative_to(dest.parent.parent)}, se omite (usa --force para repetir)")
        return True

    print(f"[{year}] {zip_url(year)}")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / f"{year}.zip"
        download(zip_url(year), zip_path)
        print("  extrayendo...")
        extract(zip_path, folder)

    n_csv, n_txt = count_files(folder)
    ok = (n_csv, n_txt) == (EXPECTED_CSV, EXPECTED_TXT)
    status = "OK" if ok else f"AVISO: se esperaban {EXPECTED_CSV} CSV y {EXPECTED_TXT} txt"
    print(f"  {n_csv} CSV y {n_txt} txt en {folder.name} -> {status}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga los datos del CCPC a data/raw/")
    parser.add_argument("--years", nargs="+", type=int, choices=sorted(UPLOAD_PATH),
                        default=sorted(UPLOAD_PATH), help="elecciones a descargar (por defecto todas)")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST,
                        help=f"carpeta destino (por defecto {DEFAULT_DEST})")
    parser.add_argument("--force", action="store_true", help="descargar de nuevo aunque ya esté completo")
    args = parser.parse_args()

    args.dest.mkdir(parents=True, exist_ok=True)
    failed = []
    for year in sorted(args.years):
        try:
            if not fetch_year(year, args.dest, args.force):
                failed.append(year)
        except Exception as exc:  # una elección que falla no debe frenar las demás
            print(f"  ERROR en {year}: {exc}")
            failed.append(year)

    if failed:
        print(f"\nCon problemas: {failed}. Vuelve a correr el script, solo repetirá esos años.")
        return 1
    print("\nListo: todos los datos están en", args.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
