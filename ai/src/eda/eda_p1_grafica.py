"""Entrada compatible para regenerar la gráfica de la pregunta 1."""
import argparse
from pathlib import Path

import pandas as pd
from eda_common import ROOT, REPORT_DIR
from eda_p1 import figure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datos", nargs="?", type=Path, default=ROOT / "data/processed")
    args = parser.parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    figure(pd.read_parquet(args.datos / "tabla_municipios_entrenamiento.parquet"))
    print(f"Gráfica: {REPORT_DIR / 'eda_p1_dispersion.png'}")


if __name__ == "__main__":
    main()
