"""Casos numéricos complementarios al dominio de Isaac; umbrales ficticios."""

from decimal import Decimal
from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.analisis.services import evaluar_componente, total_ponderado


class CalculosComplementariosTests(SimpleTestCase):
    def evaluar(self, **cambios):
        datos = dict(area_inicial=100, area_residual=25, confianza=0.8,
                     umbral_confianza=0.8, comparable=True, oculto=False)
        datos.update(cambios)
        return evaluar_componente(**datos)

    def test_confianza_exactamente_en_umbral_y_debajo(self):
        self.assertEqual(self.evaluar()["estado"], "CONCLUYENTE")
        inferior = self.evaluar(confianza=0.7999)
        self.assertEqual(inferior["estado"], "NO_CONCLUYENTE")
        self.assertEqual(inferior["motivo"], "BAJA_CONFIANZA")

    def test_porcentaje_100_es_valido_y_superior_no_se_recorta(self):
        self.assertEqual(self.evaluar(area_residual=100)["porcentaje"], Decimal("100.0000"))
        superior = self.evaluar(area_residual=100.01)
        self.assertEqual(superior["porcentaje"], Decimal("100.0100"))
        self.assertEqual(superior["estado"], "NO_CONCLUYENTE")

    def test_fraccion_se_redondea_a_cuatro_decimales(self):
        self.assertEqual(self.evaluar(area_inicial=3, area_residual=1)["porcentaje"], Decimal("33.3333"))

    def test_no_finitos_en_cada_entrada_se_rechazan(self):
        for campo in ("area_inicial", "area_residual", "confianza", "umbral_confianza"):
            for valor in (float("nan"), float("inf"), float("-inf")):
                with self.subTest(campo=campo, valor=valor):
                    with self.assertRaises(ValidationError):
                        self.evaluar(**{campo: valor})

    def test_cero_residual_no_supera_ocultacion_o_incomparabilidad(self):
        for cambios in (dict(oculto=True), dict(comparable=False)):
            with self.subTest(cambios=cambios):
                resultado = self.evaluar(area_residual=0, **cambios)
                self.assertEqual(resultado["estado"], "NO_CONCLUYENTE")
                self.assertIsNone(resultado["porcentaje"])

    def test_total_vacio_y_todos_excluidos_no_inventan_cero(self):
        vacio = total_ponderado([])
        self.assertIsNone(vacio["porcentaje"])
        self.assertFalse(vacio["completo"])
        excluido = SimpleNamespace(
            estado="NO_CONCLUYENTE", area_inicial=100, area_residual=None,
            servicio_componente=SimpleNamespace(componente_codigo="yuca"),
            motivo="SIN_DETECCION",
        )
        total = total_ponderado([excluido])
        self.assertIsNone(total["porcentaje"])
        self.assertEqual(total["cobertura"], "0/1")
        self.assertFalse(total["completo"])
        self.assertEqual(total["excluidos"], [{"componente": "yuca", "motivo": "SIN_DETECCION"}])
