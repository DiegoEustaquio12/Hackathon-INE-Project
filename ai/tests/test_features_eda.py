"""Disponibilidad temporal, antecedentes ausentes y orden del historial."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/data_prep"))
from features_eda import calcular_features_temporales


class FeaturesTemporalesTests(unittest.TestCase):
    def setUp(self):
        self.nacional = pd.Series({2009: .55, 2012: .35, 2015: .50, 2018: .38, 2021: .48, 2024: .40})
        self.hist = pd.DataFrame([
            (1, 1, 2018, "presidencial", .4),
            (1, 1, 2009, "intermedia", .6),
            (1, 1, 2012, "presidencial", .3),
            (1, 1, 2015, "intermedia", None),
            (1, 2, 2018, "presidencial", .5),
            (1, 3, 2018, "presidencial", None),
        ], columns=["EDOCVE", "MPIOCVE", "AELEC", "tipo", "abstencion"])

    def test_usa_ultima_con_dato_y_no_depende_del_orden(self):
        resultado = calcular_features_temporales(self.hist, 2021, self.nacional)
        self.assertAlmostEqual(resultado.loc[(1, 1), "cambio_presidenciales"], .1)
        self.assertEqual(resultado.loc[(1, 1), "anios_desde_ultima_intermedia"], 12)
        self.assertEqual(resultado.loc[(1, 1), "anios_desde_ultima_presidencial"], 3)
        pd.testing.assert_frame_equal(resultado, calcular_features_temporales(self.hist.iloc[::-1], 2021, self.nacional))

    def test_no_inventa_antecedentes(self):
        resultado = calcular_features_temporales(self.hist, 2021, self.nacional)
        self.assertTrue(pd.isna(resultado.loc[(1, 2), "cambio_presidenciales"]))
        self.assertTrue(pd.isna(resultado.loc[(1, 2), "anios_desde_ultima_intermedia"]))
        self.assertTrue(resultado.loc[(1, 3)].drop("n_presidenciales_previas_sin_2012").isna().all())

    def test_rechaza_eleccion_objetivo_y_futuras(self):
        for objetivo in (2018, 2015):
            with self.assertRaisesRegex(ValueError, "anteriores"):
                calcular_features_temporales(self.hist, objetivo, self.nacional)

    def test_rechaza_historial_duplicado(self):
        with self.assertRaisesRegex(ValueError, "duplicado"):
            calcular_features_temporales(pd.concat([self.hist, self.hist.iloc[:1]]), 2021, self.nacional)

    def test_excluir_2012_no_rellena_antecedentes(self):
        antes = calcular_features_temporales(self.hist[self.hist["AELEC"] < 2015], 2015, self.nacional)
        self.assertTrue(pd.isna(antes.loc[(1, 1), "abst_ultima_presidencial_sin_2012"]))
        self.assertTrue(pd.isna(antes.loc[(1, 1), "brecha_intermedia_presidencial_sin_2012"]))
        self.assertEqual(antes.loc[(1, 1), "n_presidenciales_previas_sin_2012"], 0)
        despues = calcular_features_temporales(self.hist, 2021, self.nacional)
        self.assertAlmostEqual(despues.loc[(1, 1), "abst_prom_presidenciales_sin_2012"], .4)
        self.assertAlmostEqual(despues.loc[(1, 1), "brecha_intermedia_presidencial_sin_2012"], .2)

    def test_cambio_relativo_usa_pais_de_cada_antecedente(self):
        resultado = calcular_features_temporales(self.hist, 2021, self.nacional)
        self.assertAlmostEqual(resultado.loc[(1, 1), "cambio_presidenciales_vs_pais"], .07)
        self.assertTrue(pd.isna(resultado.loc[(1, 1), "cambio_intermedias_vs_pais"]))
        # La tasa nacional del objetivo, incluso si cambia mucho, no interviene.
        alterada = self.nacional.copy()
        alterada.loc[2021] = .99
        pd.testing.assert_frame_equal(resultado, calcular_features_temporales(self.hist, 2021, alterada))

    def test_promedios_y_cambio_intermedio_con_tres_antecedentes(self):
        extras = pd.DataFrame([
            (1, 1, 2021, "intermedia", .5),
            (1, 1, 2024, "presidencial", .45),
        ], columns=self.hist.columns)
        resultado = calcular_features_temporales(pd.concat([self.hist, extras]), 2027, self.nacional)
        self.assertAlmostEqual(resultado.loc[(1, 1), "abst_prom_presidenciales_sin_2012"], .425)
        self.assertEqual(resultado.loc[(1, 1), "n_presidenciales_previas_sin_2012"], 2)
        self.assertAlmostEqual(resultado.loc[(1, 1), "cambio_intermedias_vs_pais"], -.03)
        self.assertAlmostEqual(resultado.loc[(1, 1), "cambio_presidenciales_vs_pais"], .03)

    def test_rechaza_pais_ausente(self):
        with self.assertRaisesRegex(ValueError, "nacional"):
            calcular_features_temporales(self.hist, 2021, self.nacional.drop(2012))


if __name__ == "__main__":
    unittest.main()
