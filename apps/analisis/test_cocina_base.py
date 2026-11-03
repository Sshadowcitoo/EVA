from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings
from django.urls import include, path, reverse
from apps.catalogo.auth_views import destino_cocina
from apps.catalogo.permissions import COCINA, REGISTRO, ADMINISTRACION, PERMISOS_POR_ROL


urlpatterns = [
    path("analisis/", include(([path("revision/", lambda request: HttpResponse("fixture"), name="pendientes_revision")], "analisis"))),
    path("cuentas/", include("apps.catalogo.cuentas_urls")),
]


class SinRevision:
    urlpatterns = [path("cuentas/", include("apps.catalogo.cuentas_urls"))]


class BaseCocinaTests(SimpleTestCase):
    @override_settings(ROOT_URLCONF=SinRevision)
    def test_navegacion_sin_endpoint_conserva_destino_actual(self):
        self.assertEqual(destino_cocina(), reverse("cuentas:cocina_pendiente"))

    @override_settings(ROOT_URLCONF=__name__)
    def test_navegacion_usa_revision_cuando_endpoint_existe(self):
        self.assertEqual(destino_cocina(), "/analisis/revision/")

    def test_sin_endpoint_no_hay_formulario_de_decision_falso(self):
        html = render_to_string("analisis/revision.html", {})
        self.assertIn("al conectar el servicio de revisión", html)
        self.assertNotIn('name="decision"', html)

    def test_confirmacion_deshabilitada_con_evidencia_insuficiente(self):
        html = render_to_string("analisis/revision.html", {"caso": {"origen": "SIMULADO"}, "decision_url": "/fixture/",
            "resultados": [{"componente": "Pescado", "motivo": "OCULTACION"}]})
        self.assertIn('value="CONFIRMADO" disabled', html)
        self.assertIn("SIMULADO", html)
        self.assertIn("No concluyente", html)

    def test_permisos_revision_no_se_heredan_por_otro_rol(self):
        self.assertIn("analisis.add_revisionanalisis", PERMISOS_POR_ROL[COCINA])
        for rol in (REGISTRO, ADMINISTRACION):
            self.assertNotIn("analisis.add_revisionanalisis", PERMISOS_POR_ROL[rol])
