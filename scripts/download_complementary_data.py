#!/usr/bin/env python3
"""Descarga los datos complementarios del INEGI y los separa por grupo y fuente:

    data/external/sociodemografico/eceg_2010/ECEG_01_2010/conjunto_de_datos/secciones_01.csv
    data/external/sociodemografico/eceg_2020/conjunto_de_datos/INE_SECCION_2020.csv
    data/external/economico/ce_2024/conjunto_de_datos/tr_ce_nac_2024.csv
    ...

Solo usa la biblioteca estándar, no hay nada que instalar.

Los dos conjuntos sociodemográficos son los ECEG (entorno geoelectoral) del Censo de
Población y Vivienda 2010 y 2020. Los económicos son los Censos Económicos 2024, 2014 y
2000. El ZIP de 2010 trae un ZIP por entidad, que se extrae en su propia carpeta.

Uso (desde cualquier carpeta):
    python scripts/download_complementary_data.py                     # todos
    python scripts/download_complementary_data.py --grupo economico    # solo económicos
    python scripts/download_complementary_data.py --datasets ce_2024   # solo una fuente
    python scripts/download_complementary_data.py --force              # vuelve a extraer

Las fuentes que ya están completas se omiten.
"""
import argparse
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

DEFAULT_DEST = Path(__file__).resolve().parents[1] / "data" / "external"

BASE = "https://www.inegi.org.mx/contenidos"
# grupo -> fuente -> URL y número de CSV que debe quedar tras extraer (incluye ZIP anidados)
DATOS = {
    "sociodemografico": {
        "eceg_2010": {
            "url": f"{BASE}/programas/ccpv/2010/datosabiertos/geoelectorales/eceg_2010_csv.zip",
            "csv_esperados": 192,  # 32 ZIP estatales x 6 CSV
        },
        "eceg_2020": {
            "url": f"{BASE}/programas/ccpv/2020/datosabiertos/geoelectorales/eceg_2020_csv.zip",
            "csv_esperados": 8,
        },
    },
    "economico": {
        "ce_2024": {
            "url": f"{BASE}/programas/ce/2024/datosabiertos/conjunto_de_datos_ce_nac_2024_csv.zip",
            "csv_esperados": 5,
        },
        "ce_2014": {
            "url": f"{BASE}/programas/ce/2019/Datosabiertos/ce2014_nac_csv.zip",
            "csv_esperados": 6,
        },
        "ce_00": {
            "url": f"{BASE}/masiva/ce/ce_00_csv.zip",
            "csv_esperados": 2,
        },
    },
}
RETRIES = 3


def count_csv(folder: Path) -> int:
    """Cuenta .csv sin importar mayúsculas: el INEGI mezcla .csv y .CSV."""
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ".csv")


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


def _carpeta_raiz_comun(nombres: list[str]) -> str | None:
    """Nombre de la única carpeta que envuelve a todos los archivos, si existe."""
    partes = [PurePosixPath(n).parts for n in nombres]
    if all(len(p) > 1 for p in partes):
        primeras = {p[0] for p in partes}
        if len(primeras) == 1:
            return primeras.pop()
    return None


def extract_zip(zip_path: Path, dest: Path, quitar_raiz: bool = True) -> None:
    """Extrae los archivos del ZIP conservando sus subcarpetas, sin rutas inseguras."""
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad:
            raise zipfile.BadZipFile(f"archivo dañado dentro del zip: {bad}")
        miembros = [m for m in zf.infolist() if not m.is_dir()]
        raiz = _carpeta_raiz_comun([m.filename for m in miembros]) if quitar_raiz else None
        for member in miembros:
            partes = PurePosixPath(member.filename).parts
            if raiz and partes[0] == raiz:
                partes = partes[1:]
            if not partes or any(p in ("", ".", "..") for p in partes):
                continue
            destino = dest.joinpath(*partes)
            destino.parent.mkdir(parents=True, exist_ok=True)
            part = destino.with_name(destino.name + ".part")
            with zf.open(member) as src, open(part, "wb") as out:
                shutil.copyfileobj(src, out)
            part.replace(destino)


def extract_nested(folder: Path) -> None:
    """Extrae los ZIP que quedaron dentro (ECEG 2010 trae un ZIP por entidad)."""
    for z in sorted(folder.rglob("*.zip")):
        sub = z.with_suffix("")  # ECEG_01_2010/
        extract_zip(z, sub)
        z.unlink()


def fetch(nombre: str, info: dict, grupo_dir: Path, force: bool) -> bool:
    final = grupo_dir / nombre
    esperados = info["csv_esperados"]
    if final.is_dir() and not force:
        n = count_csv(final)
        if n == esperados:
            print(f"[{nombre}] ya está completo en {final} (usa --force para repetir)")
            return True
        print(f"[{nombre}] existe con {n} CSV (se esperan {esperados}); se vuelve a extraer")

    print(f"[{nombre}] {info['url']}")
    grupo_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=grupo_dir, prefix=f".{nombre}-") as tmp:
        tmp = Path(tmp)
        zip_path = tmp / f"{nombre}.zip"
        download(info["url"], zip_path)
        print("  extrayendo...")
        extraer = tmp / "extraido"
        extract_zip(zip_path, extraer)
        extract_nested(extraer)

        n = count_csv(extraer)
        if final.exists():
            shutil.rmtree(final)
        extraer.rename(final)

    ok = n == esperados
    status = "OK" if ok else f"AVISO: {n} CSV, se esperaban {esperados}"
    print(f"  {n} CSV en {final} -> {status}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga datos complementarios del INEGI a data/external/")
    parser.add_argument("--grupo", choices=["all", *DATOS], default="all",
                        help="grupo a descargar (por defecto todos)")
    parser.add_argument("--datasets", nargs="+",
                        choices=[n for grupo in DATOS.values() for n in grupo],
                        help="fuentes concretas a descargar")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST,
                        help=f"carpeta destino (por defecto {DEFAULT_DEST})")
    parser.add_argument("--force", action="store_true", help="extraer de nuevo aunque ya esté completo")
    args = parser.parse_args()

    grupos = list(DATOS) if args.grupo == "all" else [args.grupo]
    args.dest.mkdir(parents=True, exist_ok=True)
    failed = []
    for grupo in grupos:
        for nombre, info in DATOS[grupo].items():
            if args.datasets and nombre not in args.datasets:
                continue
            try:
                if not fetch(nombre, info, args.dest / grupo, args.force):
                    failed.append(nombre)
            except Exception as exc:  # una fuente que falla no debe frenar las demás
                print(f"  ERROR en {nombre}: {exc}")
                failed.append(nombre)

    if failed:
        print(f"\nCon problemas: {failed}. Vuelve a correr el script, solo repetirá esos.")
        return 1
    print("\nListo: los datos complementarios están en", args.dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
