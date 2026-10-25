"""Casos que podrían dar un cierre incorrecto de la validación oficial."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ai.src.data_prep import validacion_ine as validacion
from scripts.comparar_totales_ine import validar_filtros


class ValidacionTotalesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oficiales, _ = validacion.cargar_oficiales()
        cls.proyecto = cls.oficiales[[*validacion.LLAVE, *validacion.CONTEOS]].copy()

    def test_la_evidencia_completa_coincide(self):
        resultado = validacion.comparar(self.oficiales, self.proyecto)
        self.assertEqual(len(resultado), 192)
        self.assertTrue(resultado.coincide.all())

    def test_diferencias_estatales_que_se_cancelan_en_el_pais_no_pasan(self):
        proyecto = self.proyecto.copy()
        proyecto.loc[0, ['SV', 'NV']] += [1, -1]
        proyecto.loc[1, ['SV', 'NV']] += [-1, 1]
        pd.testing.assert_series_equal(proyecto[validacion.CONTEOS].sum(), self.proyecto[validacion.CONTEOS].sum())
        resultado = validacion.comparar(self.oficiales, proyecto)
        self.assertEqual(int((~resultado.coincide).sum()), 2)
        self.assertIn('Pendiente de cierre', validacion.bloque_validacion_ine(resultado))

    def test_no_se_acepta_un_estado_faltante(self):
        with self.assertRaisesRegex(ValueError, '192'):
            validacion.comparar(self.oficiales.iloc[:-1], self.proyecto)

    def test_no_se_acepta_una_clave_oficial_duplicada(self):
        fuente = self.oficiales.copy()
        fuente.loc[1, validacion.LLAVE] = fuente.loc[0, validacion.LLAVE].to_numpy()
        with self.assertRaisesRegex(ValueError, '192'):
            validacion.comparar(fuente, self.proyecto)

    def test_redondeo_oficial_y_error_de_porcentaje(self):
        self.assertEqual(str(validacion.redondeo_publicado(4195, 10000)), '42.0')
        fuente = self.oficiales.copy()
        fuente.loc[0, 'participacion_publicada'] += 0.001
        resultado = validacion.comparar(fuente, self.proyecto)
        self.assertFalse(resultado.loc[0, 'coincide_participacion_redondeo'])
        self.assertFalse(resultado.loc[0, 'coincide'])

    def test_sin_fuente_oficial_no_se_declara_cierre(self):
        with patch.object(validacion, 'cargar_oficiales', side_effect=FileNotFoundError('falta evidencia')):
            self.assertIn('Pendiente de cierre', validacion.bloque_validacion_ine())

    def test_filtro_categorico_activo_se_rechaza(self):
        zonas = {'1': {'presModelHolder': {'quickFilterDisplay': {'quickFilter': {
            'quickFilterType': 'categorical', 'columnFullNames': ['[Sexo]'],
            'categoricalFilter': {'allSelected': False}}}}}}
        with self.assertRaisesRegex(ValueError, 'filtro categ'):
            validar_filtros(zonas)

    def test_rango_de_edad_restringido_se_rechaza(self):
        zonas = {'1': {'presModelHolder': {'quickFilterDisplay': {'quickFilter': {
            'quickFilterType': 'quantitative', 'columnFullNames': ['[Edad]'], 'included': 'include-all',
            'valueMin': '18', 'valueMax': '99', 'rangeMin': '18', 'rangeMax': '140'}}}}}
        with self.assertRaisesRegex(ValueError, 'filtro cuantitativo'):
            validar_filtros(zonas)


if __name__ == '__main__':
    unittest.main()
