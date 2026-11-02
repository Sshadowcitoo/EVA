from django.apps import apps
from django.test import SimpleTestCase, override_settings
from .configuration import criterios_componente


class ConfiguracionAnalisisTests(SimpleTestCase):
    def test_app_registrada_sin_depender_de_modelos_no_integrados(self):
        self.assertEqual(apps.get_app_config("analisis").name, "apps.analisis")

    def test_sin_evaluacion_no_inventa_umbral(self):
        self.assertIsNone(criterios_componente("arroz")["umbral_confianza"])
        self.assertFalse(criterios_componente("arroz")["comparabilidad_aprobada"])

    def test_exige_aprobacion_y_numero_finito_por_clase(self):
        config = dict(version="prueba", aprobada=True, comparabilidad_aprobada=True, umbrales={"arroz": .8})
        with override_settings(EVA_ANALISIS_CRITERIOS=config):
            self.assertEqual(criterios_componente("arroz")["umbral_confianza"], .8)
            self.assertIsNone(criterios_componente("pollo")["umbral_confianza"])
        for valor in (True, float("nan"), float("inf"), -1, 2, "0.8"):
            config["umbrales"]["arroz"] = valor
            with override_settings(EVA_ANALISIS_CRITERIOS=config):
                self.assertIsNone(criterios_componente("arroz")["umbral_confianza"])
