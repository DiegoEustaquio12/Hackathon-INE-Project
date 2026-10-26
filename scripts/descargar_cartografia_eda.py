"""Descarga cartografía municipal 2022 para el EDA de vecinos (pregunta 10).

Fuente pública señalada en docs/PLAN.md. Solo usa la biblioteca estándar.
python scripts/descargar_cartografia_eda.py

scripts/ejecutar_eda.py lo llama antes de iniciar los diez análisis en paralelo.
Para ejecutar únicamente la pregunta de vecinos:
python scripts/descargar_cartografia_eda.py
python ai/src/eda/eda_p10.py
"""
import datetime
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

URL = "http://www.conabio.gob.mx/informacion/gis/maps/geo/mun22gw.zip"
METADATA = "http://geoportal.conabio.gob.mx/metadatos/doc/html/mun22gw.html"
DEST = Path(__file__).resolve().parents[1] / "data/external/cartografia/mun22gw"


def main():
    required = [f"mun22gw.{ext}" for ext in ["shp", "shx", "dbf", "prj"]]
    if all((DEST / n).is_file() for n in [*required, "fuente.json", "mun22gw.zip"]):
        meta = json.loads((DEST / "fuente.json").read_text())
        with (DEST / "mun22gw.zip").open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() == meta["sha256"]:
                print(f"Cartografía ya descargada: {DEST}")
                return
    DEST.mkdir(parents=True, exist_ok=True)
    # El servidor de esta publicación ofrece HTTP. Se registra SHA256 como
    # procedencia reproducible; no se presenta como autenticación del origen.
    with tempfile.TemporaryDirectory(dir=DEST) as temporary:
        archive = Path(temporary) / "mun22gw.zip"
        request = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise ValueError("ZIP cartográfico dañado")
            for name in required:
                with z.open(name) as src, (DEST / name).open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        archive.replace(DEST / "mun22gw.zip")
    with (DEST / "mun22gw.zip").open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    (DEST / "fuente.json").write_text(json.dumps(dict(
        url=URL, metadata_url=METADATA, sha256=digest,
        descarga_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        bytes=(DEST / "mun22gw.zip").stat().st_size), indent=2)+"\n")
    print(f"Cartografía descargada en {DEST}")


if __name__ == "__main__":
    main()
