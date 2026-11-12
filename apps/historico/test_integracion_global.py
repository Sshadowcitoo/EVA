from django.urls import reverse
from django.test import Client
from .test_dominio_historico import BaseHistorico


class IntegracionGlobalTests(BaseHistorico):
    def test_rutas_reales_y_navegacion_por_roles(self):
        self.caso()
        self.client.force_login(self.cocina)
        r = self.client.get(reverse('analisis:lista'))
        self.assertNotContains(r, 'href="/historico/"')
        self.assertEqual(self.client.get(reverse('historico:lista')).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('historico:lista')).status_code, 200)
        self.client.force_login(self.registro)
        r = self.client.get(reverse('captura:nueva_bandeja'))
        self.assertNotContains(r, 'href="/historico/"')
        self.assertEqual(self.client.get(reverse('historico:lista')).status_code, 403)

    def test_enlace_percepcion_y_persistencia_sin_sustituir_servicios(self):
        servicio, _, _ = self.caso()
        self.client.force_login(self.registro)
        enlace = reverse('historico:percepcion', args=[servicio.pk])
        r = self.client.get(reverse('captura:foto_retorno', args=[servicio.pk]))
        self.assertContains(r, enlace)
        r = self.client.post(enlace, dict(categoria='ADECUADA', motivo='', version_esperada=0))
        self.assertRedirects(r, enlace)
        self.assertEqual(servicio.percepciones.get(vigente=True).categoria, 'ADECUADA')
