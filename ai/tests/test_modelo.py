"""Validación de Fase 7: python -m unittest ai/tests/test_modelo.py."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "ai/src/models"))
from datos_modelo import (
    BLOQUE_A, BLOQUE_B, BLOQUE_C, CONTEOS_CALENDARIO, PROHIBIDAS, bloques, cargar,
    filas_entrenables, huella, matriz, niveles_pais, punto_partida,
    preparar, sin_2012, solo_seleccion, variante_ns,
)
from explicacion import explicar, explicar_referencia
from fase7 import ARTIFACTOS, construir_salida, reporte_desde_archivos, validar_salida
from validacion import (
    INICIALES, aplicar_rango, calibrar_rango, centrar, entrenar, evaluar,
    gana, lightgbm, metricas, particiones_estados, predecir, seleccionar,
)


def base_ejemplo():
    return pd.DataFrame([
        dict(EDOCVE=1, MPIOCVE=1, AELEC=2015, tipo_eleccion="intermedia",
             NV=40, SV=40, NS=20, LN=100, conocidos=80, pct_ns=.2),
        dict(EDOCVE=1, MPIOCVE=1, AELEC=2021, tipo_eleccion="intermedia",
             NV=20, SV=60, NS=20, LN=100, conocidos=80, pct_ns=.2),
        dict(EDOCVE=1, MPIOCVE=2, AELEC=2021, tipo_eleccion="intermedia",
             NV=60, SV=140, NS=0, LN=200, conocidos=200, pct_ns=0),
    ])


class DatosModeloTest(unittest.TestCase):
    def test_nacional_desde_sumas_y_distancia(self):
        base = base_ejemplo()
        nacional = niveles_pais(base)
        self.assertAlmostEqual(nacional.loc[2021], 80 / 280)
        self.assertNotAlmostEqual(nacional.loc[2021], (.25 + .30) / 2)
        foto = pd.DataFrame(dict(EDOCVE=[1], MPIOCVE=[1], eleccion_objetivo=[2021],
            tipo_objetivo=["intermedia"], abstencion_objetivo=[.25],
            abst_ultima_intermedia=[.5], abst_ultima_presidencial=[.3]))
        preparada = preparar(foto, base)
        self.assertAlmostEqual(preparada.distancia_objetivo.iloc[0], .25 - 80 / 280)
        self.assertAlmostEqual(preparada.pct_ns_objetivo.iloc[0], .2)
        self.assertEqual(preparada.es_intermedia.iloc[0], 1)
        self.assertNotIn("distancia_objetivo", foto)

    def test_bloques_explicitos_y_prohibiciones(self):
        self.assertEqual((len(BLOQUE_A), len(BLOQUE_B), len(BLOQUE_C)), (39, 8, 28))
        self.assertTrue(CONTEOS_CALENDARIO <= PROHIBIDAS)
        for columnas in bloques().values():
            self.assertFalse(set(columnas) & PROHIBIDAS)
            self.assertEqual(len(columnas), len(set(columnas)))
        self.assertNotIn("A+B+C", bloques(sin_censo=True))
        with self.assertRaises(ValueError):
            matriz(pd.DataFrame({"EDOCVE": [1]}), ["EDOCVE"])
        with self.assertRaises(ValueError):
            matriz(pd.DataFrame({"x": [np.inf]}), ["x"])

    def test_referencia_por_tipo_y_sin_imputacion(self):
        foto = pd.DataFrame(dict(tipo_objetivo=["intermedia", "presidencial", "intermedia"],
            abst_ultima_intermedia=[.5, .6, np.nan], abst_ultima_presidencial=[.3, .4, .2]))
        np.testing.assert_allclose(punto_partida(foto), [.5, .4, np.nan], equal_nan=True)

    def test_filtros_sin_respuesta_minimo_y_ns(self):
        f = pd.DataFrame(dict(abstencion_objetivo=[.2, np.nan, .3, .4],
            distancia_objetivo=[.1, np.nan, .1, .2], conocidos_objetivo=[500, 800, 499, 1000],
            pct_ns_objetivo=[.1, .1, .1, .3]))
        self.assertEqual(filas_entrenables(f).index.tolist(), [0, 3])
        self.assertEqual(filas_entrenables(f, max_ns=.2).index.tolist(), [0])
        with self.assertRaises(ValueError):
            filas_entrenables(f, minimo=0)

    def test_ns_cambia_respuesta_y_referencia_sin_rearmados(self):
        foto = pd.DataFrame(dict(EDOCVE=[1, 1], MPIOCVE=[1, 2], eleccion_objetivo=[2021, 2021],
            tipo_objetivo=["intermedia", "intermedia"], historial_rearmado=[False, True],
            historial_incompleto=[False, False], abstencion_objetivo=[.25, .3]))
        variante = variante_ns(foto, base_ejemplo())
        self.assertEqual(len(variante), 1)
        self.assertAlmostEqual(variante.abstencion_objetivo.iloc[0], .4)
        self.assertAlmostEqual(variante.referencia.iloc[0], .6)
        self.assertAlmostEqual(variante.distancia_objetivo.iloc[0], .4 - 1 / 3)
        foto.loc[0, "abstencion_objetivo"] = np.nan
        self.assertTrue(variante_ns(foto, base_ejemplo()).empty)

    def test_sin_2012_no_conserva_features_contaminadas(self):
        _, columnas = sin_2012(pd.DataFrame(), bloques()["A+B+C"])
        self.assertIn("abst_ultima_presidencial_sin_2012", columnas)
        self.assertIn("abst_18_24_ui", columnas)
        for prohibida in ("abst_ultima_presidencial", "cambio_presidenciales", "pct_ns_prom",
                          "pct_18_24", "ln_ultima", "pct_hueco_2012", "cambio_presidenciales_vs_pais",
                          *CONTEOS_CALENDARIO):
            self.assertNotIn(prohibida, columnas)
        self.assertEqual(len(columnas), len(set(columnas)))


class ValidacionTest(unittest.TestCase):
    def test_futuro_rechazado_antes_de_entrenar(self):
        for anios in ([2015, 2018, 2021], [2024], []):
            with self.assertRaises(ValueError):
                solo_seleccion(pd.DataFrame({"eleccion_objetivo": anios}))
        with patch("validacion.entrenar") as entrenar_mock:
            with self.assertRaises(ValueError):
                seleccionar(pd.DataFrame({"eleccion_objetivo": [2021]}), {"A": ["x"]})
            entrenar_mock.assert_not_called()

    def test_estados_no_se_mezclan_y_cada_fila_se_prueba_una_vez(self):
        foto = pd.DataFrame({"EDOCVE": np.repeat(np.arange(1, 33), np.arange(1, 33))})
        vistos = []
        for i, j in particiones_estados(foto, 8):
            self.assertFalse(set(foto.iloc[i].EDOCVE) & set(foto.iloc[j].EDOCVE))
            vistos.extend(j)
        self.assertEqual(sorted(vistos), list(range(len(foto))))

    def test_centrado_pesado_incluye_recorte_y_complemento(self):
        p, _ = centrar([-3, -.1, .2, 4], [1, 4, 10, 1], .4816)
        self.assertAlmostEqual(np.average(p, weights=[1, 4, 10, 1]), .4816, places=13)
        self.assertTrue(((p >= 0) & (p <= 1)).all())
        np.testing.assert_allclose(p + (1 - p), 1)
        with self.assertRaises(ValueError):
            centrar([.1], [0], .5)

    def test_metricas_y_comparacion_mismas_filas(self):
        m = metricas([.2, .4], [.3, .7], [1, 3])
        self.assertAlmostEqual(m["mae_pts"], 20)
        self.assertAlmostEqual(m["mae_ponderado_pts"], 25)
        foto = pd.DataFrame(dict(abstencion_objetivo=[.2, .4, np.nan],
            referencia=[.3, .7, .9], conocidos_objetivo=[1, 3, 0],
            historial_rearmado=[False, True, False], historial_incompleto=[False, False, False]))
        e = evaluar(foto, [.3, .5, .8], "A_2021")
        self.assertEqual(e.loc[e.segmento.eq("todos"), "n"].tolist(), [2, 2])
        self.assertEqual(e.loc[e.segmento.eq("rearmado"), "n"].tolist(), [1, 1])

    def test_color_por_tercios_propios_no_cambia_con_el_nivel_nacional(self):
        y = np.linspace(.2, .8, 9)
        base = metricas(y, y + .02 * np.sin(np.arange(9)), np.ones(9))
        movida = metricas(y, y + .02 * np.sin(np.arange(9)) + .05, np.ones(9))
        for columna in ("mismo_tercio_pct", "rojos_detectados_pct", "spearman"):
            self.assertAlmostEqual(base[columna], movida[columna])
        perfecta = metricas(y, y + .1, np.ones(9))
        self.assertEqual((perfecta["mismo_tercio_pct"], perfecta["rojos_detectados_pct"]), (100, 100))

    def test_se_exigen_las_cuatro_mejoras_y_empate_no_gana(self):
        filas = [dict(prueba=p, segmento="todos", metodo=m, mae_pts=e, mae_ponderado_pts=e)
                 for p in ("A_2021", "B_estados") for m, e in (("modelo", 5), ("punto de partida", 6))]
        v = pd.DataFrame(filas)
        self.assertTrue(gana(v))
        for fila in (0, 2):
            for columna in ("mae_pts", "mae_ponderado_pts"):
                copia = v.copy()
                copia.loc[fila, columna] = 6
                self.assertFalse(gana(copia))
        self.assertFalse(gana(v.iloc[:2]))

    def test_rango_sesgado_contiene_punto_e_invierte_participacion(self):
        foto = pd.DataFrame(dict(conocidos_ultima=np.arange(1, 31),
                                 abstencion_objetivo=np.repeat(.8, 30)))
        calibracion = calibrar_rango(foto, np.repeat(.4, 30))
        minimo, maximo = aplicar_rango([.4, .99], [5, 25], calibracion)
        self.assertTrue((minimo <= [.4, .99]).all())
        self.assertTrue((maximo >= [.4, .99]).all())
        self.assertEqual(maximo[1], 1)
        self.assertTrue(((1 - maximo) <= (1 - minimo)).all())

    def test_rango_descuenta_el_error_nacional_conocido(self):
        error = np.tile(np.linspace(-.03, .03, 10), 3)
        foto = pd.DataFrame(dict(conocidos_ultima=np.arange(1, 31), abstencion_objetivo=.5 + error - .05))
        centrado = calibrar_rango(foto, np.repeat(.5, 30), error_nacional=-.05)
        self.assertEqual(centrado["error_nacional"], -.05)
        for grupo in centrado["grupos"]:
            self.assertAlmostEqual(grupo["margen_min"], -grupo["margen_max"])
            self.assertGreater(grupo["margen_max"], 0)
        # Sin descontarlo, el cambio nacional de la prueba se queda en el rango.
        sesgado = calibrar_rango(foto, np.repeat(.5, 30))
        self.assertTrue(all(g["margen_max"] == 0 for g in sesgado["grupos"]))


class ExplicacionTest(unittest.TestCase):
    def test_aportes_reconstruyen_y_razones_son_locales(self):
        rng = np.random.default_rng(2027)
        x = rng.uniform(size=(120, 3))
        foto = pd.DataFrame(x, columns=["pct_18_24", "pct_rural", "edad_promedio"])
        foto["distancia_objetivo"] = .2 * x[:, 0] - .1 * x[:, 1]
        modelo = entrenar(foto, list(foto.columns[:3]), INICIALES, 25)
        razones, globales, base = explicar(modelo, foto, list(foto.columns[:3]))
        self.assertEqual(razones.shape, (120, 3))
        self.assertEqual(set(globales.columna), set(foto.columns[:3]))
        self.assertTrue(razones.razon_1.str.contains("pp").all())
        self.assertTrue(np.isfinite(base))

    def test_referencia_no_usa_shap_del_modelo_descartado(self):
        razones = explicar_referencia(pd.DataFrame({"referencia": [.4]}))
        self.assertIn("40.00%", razones.razon_1.iloc[0])
        self.assertIn("punto de partida", razones.razon_2.iloc[0])


class InsumosRealesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base, cls.train, cls.pred, cls.fuentes = cargar()

    def test_conteos_esperados_sin_alterar_tablas(self):
        self.assertEqual(len(self.train), 9866)
        self.assertEqual(len(self.pred), 2477)
        self.assertEqual(self.train.abstencion_objetivo.isna().sum(), 65)
        self.assertEqual([len(filas_entrenables(s)) for _, s in self.train.groupby("eleccion_objetivo")],
                         [2364, 2378, 2394, 2395])
        for ruta, sha in self.fuentes.items():
            self.assertEqual(huella(RAIZ / ruta), sha)

    def test_salida_completa_preserva_originales_y_respaldo(self):
        p, _ = centrar(self.pred.referencia, self.pred.conocidos_ultima, .4816)
        foto_a = self.train.loc[self.train.eleccion_objetivo.eq(2021)
            & self.train.abstencion_objetivo.notna() & self.train.referencia.notna()]
        calibracion = calibrar_rango(foto_a, foto_a.referencia)
        salida = construir_salida(self.pred, p, calibracion, "modelo", .4816,
                                   explicar_referencia(self.pred), False)
        validar_salida(salida, .4816, "modelo")
        fuente = pd.read_parquet(RAIZ / "data/processed/tabla_municipios_2027.parquet")
        columnas = fuente.columns.drop("abstencion_objetivo")
        pd.testing.assert_frame_equal(fuente[columnas], salida[columnas])
        respaldo = construir_salida(self.pred, self.pred.referencia.to_numpy(), calibracion,
            "punto de partida", .4816, explicar_referencia(self.pred), False)
        np.testing.assert_array_equal(respaldo.abstencion_pred, self.pred.referencia)
        self.assertEqual(salida.ns_alto.sum(), 38)
        rota = salida.copy()
        rota.loc[0, "participacion_pred"] = 0
        with self.assertRaises(ValueError):
            validar_salida(rota, .4816, "modelo")


@unittest.skipUnless((ARTIFACTOS / "modelo_config.json").is_file(), "Ejecutar Fase 7 para comprobar artefactos")
class ArtefactosTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ARTIFACTOS / "modelo_config.json").read_text())
        cls.predicciones = pd.read_parquet(ARTIFACTOS / "predicciones_2027.parquet")

    def test_huellas_de_insumos_codigo_y_salidas(self):
        for grupo in ("fuentes_sha256", "codigo_sha256"):
            for nombre, esperado in self.config[grupo].items():
                self.assertEqual(huella(RAIZ / nombre), esperado, nombre)
        for nombre, esperado in self.config["artefactos_sha256"].items():
            self.assertEqual(huella(ARTIFACTOS / nombre), esperado, nombre)

    def test_metricas_se_reconstruyen_desde_predicciones_guardadas(self):
        pred = pd.read_csv(ARTIFACTOS / "predicciones_pruebas.csv")
        real = pd.read_csv(ARTIFACTOS / "validacion.csv")
        for prueba, foto in pred.groupby("prueba", sort=False):
            calculada = evaluar(foto, foto.modelo_pred, prueba).reset_index(drop=True)
            esperada = real.loc[real.prueba.eq(prueba)].reset_index(drop=True)
            pd.testing.assert_frame_equal(calculada, esperada, check_exact=False, atol=1e-10, rtol=1e-10)
        self.assertEqual(gana(real), self.config["gana"])
        estados_b = pred.loc[pred.prueba.eq("B_estados")].groupby("EDOCVE").fold.nunique()
        self.assertTrue(estados_b.eq(1).all())
        oaxaca = pred.loc[pred.prueba.eq("B_estados") & pred.EDOCVE.eq(20), "fold"].unique()
        self.assertEqual(len(oaxaca), 1)
        self.assertEqual(pred.loc[pred.prueba.eq("B_estados") & pred.fold.eq(oaxaca[0]), "EDOCVE"].nunique(), 1)

    def test_modelo_guardado_reproduce_la_salida(self):
        _, _, foto, _ = cargar()
        modelo = lightgbm().Booster(model_file=str(ARTIFACTOS / "modelo_2027.txt"))
        pred, _ = predecir(modelo, foto, self.config["columnas"], self.config["nivel_pais_supuesto"])
        if self.config["metodo"] == "punto de partida":
            pred = foto.referencia
        np.testing.assert_allclose(pred, self.predicciones.abstencion_pred, atol=1e-12, rtol=0)
        validar_salida(self.predicciones, self.config["nivel_pais_supuesto"], self.config["metodo"])
        seleccion = pd.read_csv(ARTIFACTOS / "seleccion_columnas.csv")
        self.assertTrue(seleccion.fotos.eq("2015 2018").all())
        self.assertEqual(self.config["fotos_seleccion"], [2015, 2018])

    def test_reporte_se_reconstruye_desde_archivos(self):
        self.assertEqual(reporte_desde_archivos(ARTIFACTOS),
            (RAIZ / "docs/reports/reporte_modelo.md").read_text())

    def test_csv_y_parquet_contienen_las_mismas_predicciones(self):
        csv = pd.read_csv(ARTIFACTOS / "predicciones_2027.csv")
        self.assertEqual(csv.shape, self.predicciones.shape)
        for c in ("abstencion_pred", "abstencion_min", "abstencion_max", "participacion_pred"):
            np.testing.assert_allclose(csv[c], self.predicciones[c], atol=1e-15, rtol=0)
        self.assertEqual(csv.razon_1.tolist(), self.predicciones.razon_1.tolist())


if __name__ == "__main__":
    unittest.main()
