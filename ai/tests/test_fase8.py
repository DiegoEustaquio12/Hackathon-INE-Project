"""Pruebas de los escenarios con intervención: python -m unittest ai/tests/test_fase8.py."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "ai/src/models"))
from fase8 import (
    EFECTOS, INTERVENCIONES, LLAVE, PRIMARIO, asignar_colores, cargar,
    color_por_corte, grupo, reduccion, regla_rural, resumen, tabla_ancha, tabla_larga,
    validar, verificar_fuentes,
)

SALIDA = RAIZ / "ai/artifacts/fase8"


def foto_ejemplo():
    """13 municipios: 12 clasificables (4 por tercio) y uno sin personas con dato."""
    valores = [.60, .58, .56, .54, .52, .50, .48, .46, .44, .42, .40, .38, .40]
    filas = []
    for i, valor in enumerate(valores, start=1):
        filas.append(dict(
            EDOCVE=1, MPIOCVE=i, nombre_estado="ESTADO", nombre_municipio=f"Municipio {i}",
            eleccion_objetivo=2027, abstencion_pred=valor,
            abstencion_min=valor - .1, abstencion_max=valor + .1,
            participacion_pred=1 - valor,
            conocidos_ultima=0 if i == 13 else 1000, ln_ultima=1100,
            pct_ns_ultima=.02, pct_18_24=.15, pct_25_34=.20,
            abst_18_24_ui=.60, abst_25_34_ui=.50,
            pct_mujeres=.52, abst_hombres_ui=.55,
            pct_rural=.30, abst_rural_ui=.45,
            pocos_casos=False, ns_alto=False,
        ))
    foto = pd.DataFrame(filas)
    foto.loc[0, "pct_rural"] = 0.0          # sin secciones rurales
    foto.loc[1, "abst_rural_ui"] = np.nan   # con rural, pero sin tasa
    return foto


def escenarios(foto=None, efectos=EFECTOS, primario=PRIMARIO):
    foto = foto_ejemplo() if foto is None else foto
    colores, cortes = asignar_colores(foto)
    ancha = tabla_ancha(foto, colores, cortes, primario)
    larga = tabla_larga(foto, colores, cortes, efectos)
    return foto, colores, cortes, ancha, larga


class SemaforoTest(unittest.TestCase):
    def test_terciles_y_sin_clasificar(self):
        foto = foto_ejemplo()
        colores, cortes = asignar_colores(foto)
        self.assertEqual(colores.value_counts().to_dict(),
                         {"rojo": 4, "amarillo": 4, "verde": 4, "sin_clasificar": 1})
        self.assertAlmostEqual(cortes["rojo"], .54)
        self.assertAlmostEqual(cortes["amarillo"], .46)
        self.assertEqual(colores.iloc[12], "sin_clasificar")
        self.assertEqual(colores.iloc[0], "rojo")
        self.assertEqual(colores.iloc[11], "verde")

    def test_los_cortes_reproducen_el_reparto(self):
        foto = foto_ejemplo()
        colores, cortes = asignar_colores(foto)
        otro = color_por_corte(foto["abstencion_pred"], cortes,
                               foto["conocidos_ultima"].gt(0), foto.index)
        pd.testing.assert_series_equal(otro, colores)

    def test_empates_se_rompen_por_clave(self):
        foto = foto_ejemplo()
        foto.loc[3, "abstencion_pred"] = foto.loc[4, "abstencion_pred"]
        colores, _ = asignar_colores(foto)
        self.assertEqual(colores.value_counts()["rojo"], 4)
        self.assertEqual(colores.iloc[3], "rojo")  # clave menor


class IntervencionTest(unittest.TestCase):
    def test_formula_de_jovenes(self):
        foto = foto_ejemplo()
        g = grupo(foto, "jovenes").iloc[0]
        self.assertAlmostEqual(g["grupo_pct"], .35)
        self.assertAlmostEqual(g["abst_grupo"], (.15 * .60 + .20 * .50) / .35)
        red = reduccion(foto, "jovenes", .10).iloc[0]
        self.assertAlmostEqual(red, .10 * .35 * ((.15 * .60 + .20 * .50) / .35))
        self.assertAlmostEqual(red * 100, 1.9)

    def test_solo_cambian_los_rojos(self):
        foto, colores, cortes, ancha, larga = escenarios()
        fuera = larga[~larga["aplica"]]
        self.assertTrue(np.allclose(fuera["abstencion_con"], fuera["abstencion_sin"]))
        self.assertTrue((fuera["reduccion_pts"] == 0).all())
        self.assertTrue((fuera["color_con"] == fuera["color_sin"]).all())
        rojos = larga[larga["aplica"]]
        self.assertTrue((rojos["abstencion_con"] <= rojos["abstencion_sin"]).all())
        con_efecto = rojos[rojos["reduccion_pts"] > 0]
        self.assertFalse(con_efecto.empty)
        self.assertTrue((con_efecto["abstencion_con"] < con_efecto["abstencion_sin"]).all())

    def test_reduccion_crece_con_el_efecto(self):
        foto = foto_ejemplo()
        base = reduccion(foto, "hombres", .05)
        medio = reduccion(foto, "hombres", .10)
        alto = reduccion(foto, "hombres", .15)
        self.assertTrue((base < medio).all())
        self.assertTrue((medio < alto).all())
        self.assertTrue((reduccion(foto, "hombres", 0) == 0).all())

    def test_reduccion_no_excede_la_abstencion(self):
        foto = foto_ejemplo()
        foto["abstencion_pred"] = .01
        for nombre in INTERVENCIONES:
            self.assertTrue((reduccion(foto, nombre, 1) <= foto["abstencion_pred"] + 1e-12).all())

    def test_rural_sin_secciones_es_cero(self):
        foto = foto_ejemplo()
        red = reduccion(foto, "rural", .10)
        self.assertEqual(red.iloc[0], 0.0)
        self.assertTrue(grupo(foto, "rural").iloc[0]["grupo_imputado"] == False)  # noqa: E712

    def test_rural_sin_tasa_usa_la_municipal(self):
        foto = foto_ejemplo()
        g = grupo(foto, "rural").iloc[1]
        self.assertTrue(g["grupo_imputado"])
        self.assertAlmostEqual(g["abst_grupo"], foto.loc[1, "abstencion_pred"])
        self.assertAlmostEqual(reduccion(foto, "rural", .10).iloc[1], .10 * .30 * .58)

    def test_sin_clasificar_no_recibe_intervencion(self):
        foto, colores, cortes, ancha, larga = escenarios()
        gris = ancha[ancha["sin_clasificar"]]
        self.assertEqual(len(gris), 1)
        self.assertEqual(gris.iloc[0]["color_sin"], "sin_clasificar")
        for nombre in INTERVENCIONES:
            self.assertEqual(gris.iloc[0][f"reduccion_{nombre}_pts"], 0.0)
            self.assertEqual(gris.iloc[0][f"color_{nombre}"], "sin_clasificar")

    def test_tabla_larga_tiene_todas_las_combinaciones(self):
        foto, colores, cortes, ancha, larga = escenarios()
        self.assertEqual(len(larga), len(foto) * len(INTERVENCIONES) * len(EFECTOS))
        self.assertFalse(larga.duplicated(["EDOCVE", "MPIOCVE", "intervencion", "efecto_pct"]).any())
        self.assertEqual(set(larga["efecto_pct"]), {5.0, 10.0, 15.0})

    def test_resumen_reconcilia_con_la_larga(self):
        foto, colores, cortes, ancha, larga = escenarios()
        res = resumen(larga)
        self.assertEqual(len(res), len(INTERVENCIONES) * len(EFECTOS))
        for fila in res.itertuples():
            d = larga[(larga["intervencion"] == fila.intervencion)
                      & np.isclose(larga["efecto_pct"], fila.efecto_pct)]
            self.assertEqual(fila.salen_de_rojo, int(d["cambio_color"].sum()))
            self.assertEqual(fila.municipios_rojos, int(d["aplica"].sum()))

    def test_validar_acepta_el_caso_base(self):
        foto, colores, cortes, ancha, larga = escenarios()
        validar(ancha, larga, EFECTOS, cortes)

    def test_validar_rechaza_cambio_fuera_de_rojo(self):
        foto, colores, cortes, ancha, larga = escenarios()
        larga.loc[~larga["aplica"], "abstencion_con"] += .01
        with self.assertRaises(ValueError):
            validar(ancha, larga, EFECTOS, cortes)

    def test_validar_rechaza_no_monotonia(self):
        foto, colores, cortes, ancha, larga = escenarios()
        fila = larga.index[(larga["intervencion"] == "hombres")
                           & np.isclose(larga["efecto_pct"], 15.0)][0]
        larga.loc[fila, "reduccion_pts"] = 0.0
        with self.assertRaises(ValueError):
            validar(ancha, larga, EFECTOS, cortes)


class ArtefactosTest(unittest.TestCase):
    def test_fuentes_intactas(self):
        _, cfg = cargar()
        verificar_fuentes(cfg)

    def test_artefactos_publicados(self):
        if not (SALIDA / "escenarios_municipio.parquet").exists():
            self.skipTest("Fase 8 todavía no se ha corrido")
        ancha = pd.read_parquet(SALIDA / "escenarios_municipio.parquet")
        larga = pd.read_csv(SALIDA / "escenarios_detalle.csv", encoding="utf-8-sig")
        res = pd.read_csv(SALIDA / "resumen_intervenciones.csv", encoding="utf-8-sig")
        self.assertEqual(len(ancha), 2477)
        self.assertFalse(ancha.duplicated(LLAVE).any())
        self.assertEqual(ancha["color_sin"].eq("rojo").sum(), 821)
        self.assertEqual(ancha["color_sin"].eq("sin_clasificar").sum(), 12)
        self.assertEqual(len(larga), 2477 * len(INTERVENCIONES) * len(EFECTOS))
        self.assertEqual(len(res), len(INTERVENCIONES) * len(EFECTOS))
        self.assertTrue(ancha["abstencion_pred"].between(0, 1).all())
        self.assertTrue(larga["abstencion_con"].between(0, 1).all())
        for nombre in INTERVENCIONES:
            self.assertTrue((ancha.loc[ancha["color_sin"] != "rojo",
                                       f"reduccion_{nombre}_pts"] == 0).all())

    def test_regla_rural_se_conserva(self):
        foto, cfg = cargar()
        colores, _ = asignar_colores(foto)
        info = regla_rural(foto, colores)
        self.assertEqual(info["rojos"], 821)
        self.assertEqual(info["cumplen"], 145)
        self.assertTrue(info["conserva"])


if __name__ == "__main__":
    unittest.main()
