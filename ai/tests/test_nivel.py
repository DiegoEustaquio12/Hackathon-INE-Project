"""Pruebas del nivel nacional y sus escenarios: python -m unittest ai/tests/test_nivel.py."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "ai/src/models"))
from nivel import INTERMEDIAS, PUBLICADO, analizar, tabla_escenarios, tabla_nacional


def serie_ejemplo():
    return pd.Series({2009: .45, 2015: .50, 2021: .48},
                     index=pd.Index([2009, 2015, 2021], name="AELEC"))


class NivelTest(unittest.TestCase):
    def test_tendencia_usa_solo_intermedias_anteriores(self):
        nacional = serie_ejemplo()
        info = analizar(nacional, objetivo=2027)
        esperada = np.polyval(np.polyfit([2009, 2015, 2021], [.45, .50, .48], 1), 2027)
        self.assertAlmostEqual(info["tendencia"], esperada)
        self.assertAlmostEqual(info["publicado"], .48)
        self.assertAlmostEqual(info["cambio"], .48 + (.48 - .50))
        self.assertEqual(info["intermedios"], [2009, 2015, 2021])

        # Un valor de 2027 no puede entrar en el ajuste ni cambiar el pronóstico.
        con_futuro = nacional.copy()
        con_futuro.loc[2027] = .99
        self.assertAlmostEqual(analizar(con_futuro)["tendencia"], esperada)

    def test_backtest_no_usa_el_anio_objetivo(self):
        info = analizar(serie_ejemplo())
        backtest = info["backtest"].set_index(["eleccion", "metodo"])
        self.assertAlmostEqual(backtest.loc[(2015, "ultimo"), "pronostico_pct"], 45.0)
        self.assertAlmostEqual(backtest.loc[(2015, "ultimo"), "error_pts"], -5.0)
        self.assertAlmostEqual(backtest.loc[(2021, "ultimo"), "pronostico_pct"], 50.0)
        self.assertAlmostEqual(backtest.loc[(2021, "ultimo"), "error_pts"], 2.0)
        self.assertIn((2021, "tendencia"), backtest.index)
        self.assertNotIn(2027, backtest.index.get_level_values("eleccion"))

    def test_tablas_separan_observado_backtest_y_pronostico(self):
        nacional = serie_ejemplo()
        info = analizar(nacional)
        tabla = tabla_nacional(nacional, info)
        self.assertEqual(set(tabla.origen), {"observado", "backtest", "pronostico"})
        pronostico = tabla.loc[tabla.origen.eq("pronostico")].iloc[0]
        self.assertEqual(int(pronostico.eleccion), 2027)
        self.assertAlmostEqual(pronostico.pronostico_pct, info["tendencia"] * 100)
        self.assertTrue(np.isnan(pronostico.abstencion_pct))

        escenarios = tabla_escenarios(info).set_index("escenario")
        self.assertEqual(set(escenarios.index),
                         {"publicado_compatibilidad", "tendencia_intermedias", "ultimo_cambio"})
        self.assertAlmostEqual(escenarios.loc["publicado_compatibilidad", "nivel_pct"], .48 * 100)
        self.assertAlmostEqual(
            escenarios.loc["publicado_compatibilidad", "diferencia_vs_publicado_pts"], 0.0)

    def test_errores_de_entrada(self):
        with self.assertRaises(ValueError):
            analizar(pd.Series(dtype=float))
        with self.assertRaises(ValueError):
            analizar(pd.Series({2009: .4, 2015: .5}), publicado=2021)
        with self.assertRaises(ValueError):
            analizar(pd.Series({2021: .5}))
        self.assertEqual(PUBLICADO, 2021)
        self.assertIn(2021, INTERMEDIAS)


if __name__ == "__main__":
    unittest.main()
