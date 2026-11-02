from django.test import SimpleTestCase
from .elegibilidad import evaluar_elegibilidad


class ElegibilidadTests(SimpleTestCase):
    def datos(self, **cambios):
        datos = dict(origen="REAL", estado_intento="COMPLETADO", estados_componentes=["CONCLUYENTE"],
            configuracion_aprobada=True, evidencia_disponible=True, decision="CONFIRMADO", intento_id="a", intento_revisado_id="a")
        datos.update(cambios)
        return evaluar_elegibilidad(**datos)

    def test_confirmacion_no_levanta_bloqueos_tecnicos(self):
        for cambios in ({"origen":"SIMULADO"}, {"estado_intento":"FALLIDO"},
                        {"estados_componentes":[]}, {"estados_componentes":["NO_CONCLUYENTE"]},
                        {"configuracion_aprobada":False}):
            self.assertFalse(self.datos(**cambios)["puede_confirmar"])
            self.assertFalse(self.datos(**cambios)["apto_historico"])

    def test_versiones_y_decisiones_se_respetan(self):
        self.assertTrue(self.datos()["apto_historico"])
        for cambios in ({"decision":"RECHAZADO"}, {"decision":"NO_CONCLUYENTE"},
                        {"intento_revisado_id":"b"}, {"intento_id":None, "intento_revisado_id":None}):
            self.assertFalse(self.datos(**cambios)["apto_historico"])

    def test_sin_imagen_no_hay_confirmacion_nueva_pero_se_conserva_revision_anterior(self):
        resultado = self.datos(evidencia_disponible=False)
        self.assertFalse(resultado["puede_confirmar"])
        self.assertTrue(resultado["apto_historico"])
