"""El reporte se publica completo y una ejecución individual conserva las otras preguntas."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai/src/eda"))
sys.path.insert(0, str(ROOT))
import eda_common as common
from scripts import ejecutar_eda as runner


class ReporteEdaTests(unittest.TestCase):
    def run_pipeline(self, failure=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, map_path, out = root / "reporte_eda.md", root / "mapa.shp", root / "resultados"
            report.write_text("reporte anterior", encoding="utf-8")
            map_path.touch()

            def fake_question(number, data, output, fragments, env):
                if number == failure:
                    return number, "Fallo simulado"
                (fragments / f"p{number}.json").write_text(json.dumps({
                    "pregunta": number, "seccion": f"## Pregunta {number}. Resultado\n\nDato {number}."}), encoding="utf-8")
                return number, None

            with patch.object(common, "REPORT", report), patch.object(runner, "MAP", map_path), \
                 patch.object(runner, "prerequisites"), patch.object(runner, "run_one", side_effect=fake_question) as run, \
                 patch.object(runner.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = runner.main(["--salida", str(out)])
            return status, report.read_text(encoding="utf-8"), run.call_count

    def test_un_proceso_fallido_conserva_el_reporte_anterior(self):
        status, report, count = self.run_pipeline(failure=6)
        self.assertEqual(status, 1)
        self.assertEqual(count, 10)
        self.assertEqual(report, "reporte anterior")

    def test_publica_las_diez_preguntas_una_vez_y_en_orden(self):
        status, report, count = self.run_pipeline()
        self.assertEqual(status, 0)
        self.assertEqual(count, 10)
        self.assertEqual(list(common.sections_from_report(report)), list(range(1, 11)))
        self.assertEqual(report.count("## Pregunta "), 10)
        summary = report.split("## Resumen\n", 1)[1].split("## Pregunta 1.", 1)[0]
        self.assertIn("| # | Respuesta en una línea | Decisión que apoya |", summary)
        for number in range(1, 11):
            self.assertEqual(summary.count(f"| {number} |"), 1)

    def test_ejecucion_individual_sustituye_solo_su_seccion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "reporte_eda.md"
            sections = {n: f"## Pregunta {n}. Resultado\n\nDato {n}." for n in range(1, 11)}
            base = pd.DataFrame({"EDOCVE": [1], "MPIOCVE": [1], "AELEC": [2024]})
            train = pd.DataFrame({"EDOCVE": [1], "MPIOCVE": [1], "eleccion_objetivo": [2024]})
            with patch.object(common, "REPORT", report), patch.object(common, "REPORT_DIR", root), \
                 patch.object(common.pd, "read_parquet", side_effect=[base, train]), \
                 patch.object(common, "record_sources"), patch.object(sys, "argv", ["eda_p5.py", "--salida", str(root)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                common.write_report(sections, root)
                common.run_question(5, lambda *args: ["## Pregunta 5. Nuevo resultado", "Nueva cifra."], __file__)
            updated = common.sections_from_report(report.read_text(encoding="utf-8"))
            self.assertEqual(len(updated), 10)
            self.assertEqual(report.read_text(encoding="utf-8").count("## Resumen\n"), 1)
            self.assertIn("Nueva cifra.", updated[5])
            for number in set(range(1, 11)) - {5}:
                self.assertEqual(updated[number], sections[number])


if __name__ == "__main__":
    unittest.main()
