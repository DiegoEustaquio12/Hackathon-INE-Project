"""Pruebas de calibración OOF: python -m unittest ai/tests/test_calibracion.py."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "ai/src/models"))
from calibracion import ajustar, aplicar, predicciones_oof, predecir_calibrado, resumen
from validacion import INICIALES


class CalibracionTest(unittest.TestCase):
    def test_ajuste_lineal_y_huber_recuperan_la_recta(self):
        rng = np.random.default_rng(2027)
        x = rng.uniform(-.3, .3, 400)
        y = .05 + 1.4 * x + rng.normal(0, .01, len(x))
        oof = pd.DataFrame(dict(distancia_pred=x, distancia_objetivo=y,
                                conocidos_objetivo=rng.integers(500, 5000, len(x))))
        for metodo in ("huber", "lineal"):
            cal = ajustar(oof, metodo)
            self.assertEqual(cal["metodo"], metodo)
            self.assertEqual(cal["n"], len(oof))
            self.assertAlmostEqual(cal["a"], .05, delta=.02)
            self.assertAlmostEqual(cal["b"], 1.4, delta=.05)

    def test_aplicar_recorta_y_conserva_el_orden(self):
        cal = dict(a=.1, b=1.5)
        valores = aplicar([-10, 0, .2, 10], cal)
        self.assertTrue(((valores >= -1) & (valores <= 1)).all())
        self.assertAlmostEqual(valores[1], .1)
        self.assertAlmostEqual(valores[2], .4)
        self.assertTrue(np.all(np.diff(valores) >= 0))
        with self.assertRaises(ValueError):
            aplicar([.1], dict(a=.1))

    def test_resumen_reporta_mae_sesgo_y_pendiente(self):
        y = np.array([.2, .4, .6])
        p = np.array([.3, .4, .6])
        r = resumen(y, p, [1, 2, 1])
        self.assertEqual(r["n"], 3)
        self.assertAlmostEqual(r["mae_pts"], 100 / 30)
        self.assertAlmostEqual(r["mae_ponderado_pts"], 2.5)
        self.assertAlmostEqual(r["sesgo_pts"], 100 / 30)
        self.assertTrue(np.isfinite(r["pendiente"]))
        with self.assertRaises(ValueError):
            resumen([.2], [.2], [0])
        with self.assertRaises(ValueError):
            resumen([np.nan], [.2], [1])
        with self.assertRaises(ValueError):
            resumen([], [], [])

    def test_predecir_calibrado_centra_al_nivel(self):
        class Modelo:
            def predict(self, x):
                return np.array([.2, -.2, .0])

        foto = pd.DataFrame(dict(pct_18_24=[.1, .2, .3], conocidos_ultima=[1, 2, 3]))
        pred, distancias = predecir_calibrado(Modelo(), foto, ["pct_18_24"], .48,
                                              dict(a=.1, b=2.0))
        np.testing.assert_allclose(distancias, [.2, -.2, 0])
        self.assertAlmostEqual(np.average(pred, weights=foto.conocidos_ultima), .48, places=13)
        self.assertTrue(((pred >= 0) & (pred <= 1)).all())

    def test_oof_cubre_cada_fila_una_vez(self):
        rng = np.random.default_rng(2027)
        estados = np.repeat(np.arange(1, 11), 6)
        foto = pd.DataFrame(dict(
            EDOCVE=estados,
            MPIOCVE=np.tile(np.arange(1, 7), 10),
            x=rng.normal(size=60),
            z=rng.uniform(size=60),
            distancia_objetivo=rng.normal(0, .1, 60),
            conocidos_objetivo=rng.integers(500, 5000, 60),
            eleccion_objetivo=2021,
        ))
        oof = predicciones_oof(foto, ["x", "z"], INICIALES, 10)
        self.assertEqual(len(oof), len(foto))
        self.assertEqual(oof.index.sort_values().tolist(), foto.index.tolist())
        self.assertTrue(np.isfinite(oof.distancia_pred).all())
        self.assertTrue(oof.fold.between(1, 5).all())
        self.assertEqual(oof.groupby("EDOCVE").fold.nunique().max(), 1)

    def test_errores_de_entrada(self):
        with self.assertRaises(ValueError):
            ajustar(pd.DataFrame(dict(distancia_pred=[], distancia_objetivo=[])))
        with self.assertRaises(ValueError):
            ajustar(pd.DataFrame(dict(distancia_pred=[.1, .1], distancia_objetivo=[.1, .2])))
        with self.assertRaises(ValueError):
            ajustar(pd.DataFrame(dict(distancia_pred=[.1, np.nan], distancia_objetivo=[.1, .2])))
        with self.assertRaises(ValueError):
            ajustar(pd.DataFrame(dict(distancia_pred=[.1, .2], distancia_objetivo=[.1, .2])),
                    "desconocido")
        with self.assertRaises(ValueError):
            predicciones_oof(pd.DataFrame(), ["x"], INICIALES, 10)


if __name__ == "__main__":
    unittest.main()
