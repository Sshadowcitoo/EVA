from datetime import timedelta
from unittest.mock import patch
from django.contrib.auth.models import Group
from django.test import Client, override_settings
from django.db import OperationalError
from django.urls import reverse
from django.utils import timezone

from apps.analisis import services
from apps.analisis.models import RevisionAnalisis, ArtefactoAnalisis
from apps.analisis.test_integracion_lino_b4 import BaseWebMotor
from apps.captura import storage
from apps.captura.models import FotografiaServicio


class RevisionHTTPTests(BaseWebMotor):
    def setUp(self):
        super().setUp()
        self.intento = self.ejecutar()
        self.analisis = self.intento.analisis
        self.url = reverse('analisis:revisar', args=[self.analisis.pk, self.intento.pk])
        self.detalle = reverse('analisis:revision_detalle', args=[self.analisis.pk])

    def decidir(self, decision='CONFIRMADO', motivo='', version=0, **extras):
        return self.client.post(self.url, dict(decision=decision, motivo=motivo,
                                             version_esperada=version, **extras))

    def test_flujo_real_con_evidencia_y_confirmacion_idempotente(self):
        respuesta = self.client.get(self.detalle)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['puede_confirmar'])
        self.assertIn(str(self.intento.pk), respuesta.context['decision_url'])
        self.assertEqual(self.decidir().status_code, 302)
        self.assertEqual(self.decidir().status_code, 302)
        self.assertEqual(RevisionAnalisis.objects.count(), 1)
        self.assertTrue(services.apto_historico(self.intento))
        self.assertEqual(self.client.get(reverse('analisis:pendientes_revision')).context['resumen']['por_revisar'], 0)

    def test_motivo_sin_javascript_rectificacion_e_historial(self):
        for decision in ('RECHAZADO', 'NO_CONCLUYENTE'):
            self.assertEqual(self.decidir(decision, '   ').status_code, 400)
        antes = list(self.intento.resultados.values_list('pk', 'porcentaje'))
        self.assertEqual(self.decidir().status_code, 302)
        self.assertEqual(self.decidir(version=1).status_code, 302)  # Repetición idéntica, no rectificación.
        self.assertEqual(RevisionAnalisis.objects.count(), 1)
        self.assertEqual(self.decidir('RECHAZADO', 'La máscara es incorrecta', 1).status_code, 302)
        self.assertEqual(self.decidir(version=2).status_code, 400)  # Cambiar la decisión sí exige motivo.
        self.assertEqual(RevisionAnalisis.objects.count(), 2)
        self.assertEqual(services.revision_vigente(self.intento).version, 2)
        self.assertFalse(services.apto_historico(self.intento))
        self.assertEqual(antes, list(self.intento.resultados.values_list('pk', 'porcentaje')))
        self.assertContains(self.client.get(self.detalle), 'Sustituida')

    def test_version_obsoleta_devuelve_conflicto_sin_sobrescribir(self):
        self.decidir()
        respuesta = self.decidir('RECHAZADO', 'Otra persona revisó', version=0)
        self.assertEqual(respuesta.status_code, 409)
        self.assertContains(respuesta, 'Otra persona revisó</textarea>', status_code=409)
        self.assertEqual(services.revision_vigente(self.intento).decision, 'CONFIRMADO')

    def test_bloqueo_concurrente_no_produce_reintento_ciego(self):
        with patch('apps.analisis.revision_views.services.revisar_resultado', side_effect=OperationalError('database is locked')):
            self.assertEqual(self.decidir().status_code, 409)
        self.assertFalse(RevisionAnalisis.objects.exists())

    def test_resultado_anterior_no_recibe_decisiones_nuevas(self):
        services.solicitar_analisis(servicio=self.servicio, solicitante=self.usuario,
            version_modelo='m2', version_configuracion='c1', origen='REAL')
        self.assertEqual(self.decidir().status_code, 409)
        self.assertNotIn('decision_url', self.client.get(self.detalle).context)
        self.assertFalse(RevisionAnalisis.objects.exists())

    def test_sin_mascara_o_bytes_modificados_no_se_confirma(self):
        art = ArtefactoAnalisis.objects.first()
        storage.eliminar(art.clave_archivo, backend=art.backend)
        self.assertFalse(self.client.get(self.detalle).context['puede_confirmar'])
        self.assertEqual(self.decidir(evidencia_disponible='true').status_code, 400)
        self.assertFalse(RevisionAnalisis.objects.exists())
        self.assertEqual(self.decidir('RECHAZADO', 'No hay evidencia disponible').status_code, 302)

    def test_hash_de_foto_cambiado_no_es_evidencia(self):
        storage.eliminar(self.servido.clave_archivo)
        storage.guardar(b'bytes distintos', self.servido.clave_archivo)
        self.assertFalse(self.client.get(self.detalle).context['puede_confirmar'])
        self.assertEqual(self.decidir().status_code, 400)

    def test_retencion_no_borra_revision_anterior_y_bloquea_confirmacion_nueva(self):
        self.decidir()
        FotografiaServicio.objects.filter(pk=self.servido.pk).update(fecha=timezone.now() - timedelta(days=91))
        self.assertTrue(services.apto_historico(self.intento))
        self.assertEqual(self.decidir(motivo='Rectificación', version=1).status_code, 400)
        self.assertFalse(self.client.get(self.detalle).context['puede_confirmar'])

    def test_simulado_no_se_convierte_en_real_desde_el_post(self):
        type(self.analisis).objects.filter(pk=self.analisis.pk).update(origen='SIMULADO')
        self.assertEqual(self.decidir(origen='REAL', evidencia_disponible=True).status_code, 400)
        self.assertFalse(RevisionAnalisis.objects.exists())

    def test_permiso_roles_csrf_y_get_no_escribe(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        for rol in ('Registro', 'Administración'):
            self.usuario.groups.set([Group.objects.get(name=rol)])
            self.assertEqual(self.client.get(self.detalle).status_code, 403)
            self.assertEqual(self.decidir().status_code, 403)
        self.usuario.groups.set([Group.objects.get(name='Cocina')])
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post(self.url, dict(decision='CONFIRMADO', version_esperada=0)).status_code, 403)
        self.assertFalse(RevisionAnalisis.objects.exists())

    def test_conteos_son_servicios_y_separan_simulados(self):
        self.intento.resultados.update(estado='NO_CONCLUYENTE', motivo='BAJA_CONFIANZA')
        resumen = self.client.get(reverse('analisis:lista')).context['resumen']
        self.assertEqual(resumen, dict(no_concluyentes=1, por_revisar=1))
        type(self.analisis).objects.filter(pk=self.analisis.pk).update(origen='SIMULADO')
        resumen = self.client.get(reverse('analisis:lista')).context['resumen']
        self.assertEqual(resumen, dict(no_concluyentes=0, por_revisar=0))

    def test_validacion_escapa_motivo_y_limita_longitud(self):
        respuesta = self.decidir('RECHAZADO', '<script>alert(1)</script>', version='incorrecta')
        self.assertEqual(respuesta.status_code, 400)
        self.assertNotContains(respuesta, '<script>alert(1)</script>', status_code=400)
        self.assertContains(respuesta, '&lt;script&gt;', status_code=400)
        self.assertEqual(self.decidir('RECHAZADO', 'x' * 1001).status_code, 400)

    def test_inicio_cocina_llega_a_revision_sin_bucles(self):
        respuesta = self.client.get(reverse('cuentas:cocina_pendiente'))
        self.assertRedirects(respuesta, reverse('analisis:pendientes_revision'))
