from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class PaginaNoEncontradaTests(SimpleTestCase):
    @override_settings(DEBUG=False)
    def test_conserva_404_y_ofrece_acceso(self):
        respuesta = self.client.get('/ruta-qa-inexistente/')
        self.assertContains(respuesta, 'Página no encontrada', status_code=404)
        self.assertContains(respuesta, f'href="{reverse("cuentas:login")}"', status_code=404)
