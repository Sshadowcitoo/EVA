"""Recorridos HTTP con ORM real sobre las rutas globales integradas."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, override_settings
from django.urls import reverse
from apps.historico.test_dominio_historico import BaseHistorico
from . import models as m
from . import test_dominio_recomendaciones as dominio


class IntegracionRecomendacionesTests(BaseHistorico):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = get_user_model().objects.create_user('admin_integracion_b7')
        cls.admin.groups.add(Group.objects.get(name='Administración'))

    def evaluar_http(self, version=''):
        self.client.force_login(self.admin)
        return self.client.post(reverse('recomendaciones:evaluar'), dict(plato='seco_de_pollo',
            componente='arroz', desde='2026-10-01', hasta='2026-10-07', version_criterios=version))

    def test_evaluar_guardar_recuperar_insuficiente_sin_mocks(self):
        self.caso()
        respuesta = self.evaluar_http()
        self.assertEqual(respuesta.status_code, 302)
        e = m.EvaluacionEvidencia.objects.get()
        self.assertRedirects(respuesta, reverse('recomendaciones:evaluacion', args=[e.pk]))
        detalle = self.client.get(respuesta.url)
        self.assertContains(detalle, 'Evidencia insuficiente')
        self.assertEqual(self.client.post(reverse('recomendaciones:generar', args=[e.pk])).status_code, 409)
        self.assertEqual(m.Recomendacion.objects.count(), 0)
        self.assertContains(self.client.get(reverse('recomendaciones:lista')), 'seco')

    def test_get_roles_navegacion_y_no_escritura(self):
        self.caso()
        self.client.force_login(self.cocina)
        self.assertEqual(self.client.get(reverse('recomendaciones:lista')).status_code, 403)
        self.assertEqual(self.client.get(reverse('historico:lista')).status_code, 403)
        self.assertEqual(self.client.get(reverse('recomendaciones:evaluar')).status_code, 403)
        self.assertEqual(m.EvaluacionEvidencia.objects.count(), 0)
        self.client.force_login(self.registro)
        self.assertEqual(self.client.get(reverse('recomendaciones:lista')).status_code, 403)
        self.assertNotContains(self.client.get(reverse('captura:nueva_bandeja')), 'href="/recomendaciones/"')

    def test_post_csrf_sin_token_no_escribe(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        self.assertEqual(cliente.post(reverse('recomendaciones:evaluar'), {}).status_code, 403)
        self.assertEqual(m.EvaluacionEvidencia.objects.count(), 0)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=dominio.CONFIG, EVA_HISTORICO_CRITERIOS=dominio.PRESENCIA)
    def test_generar_decidir_y_registrar_prueba_con_persistencia_real(self):
        self.caso()
        # Solo contexto hipotético de prueba; servicios, vistas y ORM son reales.
        with dominio.DominioRecomendacionesTests.contexto(self):
            self.assertEqual(self.evaluar_http('fixture-v1').status_code, 302)
            e = m.EvaluacionEvidencia.objects.get()
            respuesta = self.client.post(reverse('recomendaciones:generar', args=[e.pk]))
            self.assertEqual(respuesta.status_code, 302)
            r = m.Recomendacion.objects.get()
            decidir = reverse('recomendaciones:decidir', args=[r.pk])
            aceptada = self.client.post(decidir, dict(decision='ACEPTADA', justificacion='Ensayo supervisado', version_esperada=0))
            self.assertEqual(aceptada.status_code, 302)
            self.assertEqual(r.decisiones.get().autor, self.admin)
            registro = self.client.post(reverse('recomendaciones:registrar_prueba', args=[r.pk]),
                dict(cambio='Cambio controlado', responsable_id=self.cocina.pk,
                     referencia_desde='2026-10-01', referencia_hasta='2026-10-07',
                     intervencion_desde='2026-10-08', intervencion_hasta='2026-10-14'))
            self.assertEqual(registro.status_code, 302)
            p = m.PruebaControlada.objects.get()
            self.assertContains(self.client.get(registro.url), 'Cambio controlado')
            resultado = self.client.post(reverse('recomendaciones:evaluar_prueba', args=[p.pk]), dict(version_esperada=0))
            self.assertEqual(resultado.status_code, 302)
            self.assertContains(self.client.get(resultado.url), 'No evaluable')
            self.assertEqual(p.evaluaciones.count(), 1)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=dominio.CONFIG, EVA_HISTORICO_CRITERIOS=dominio.PRESENCIA)
    def test_conflicto_http_conserva_borrador_y_no_sobrescribe(self):
        self.caso()
        with dominio.DominioRecomendacionesTests.contexto(self):
            self.evaluar_http('fixture-v1')
            e = m.EvaluacionEvidencia.objects.get()
            self.client.post(reverse('recomendaciones:generar', args=[e.pk]))
            r = m.Recomendacion.objects.get()
            url = reverse('recomendaciones:decidir', args=[r.pk])
            self.client.post(url, dict(decision='ACEPTADA', justificacion='Primera decisión', version_esperada=0))
            respuesta = self.client.post(url, dict(decision='DESCARTADA', justificacion='Borrador conservado', version_esperada=0))
            self.assertContains(respuesta, 'Borrador conservado', status_code=409)
            self.assertEqual(r.decisiones.count(), 1)
