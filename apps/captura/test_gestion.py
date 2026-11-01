from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from . import services, test_dominio_bandejas as dominio
from .models import EtiquetaBandeja, SesionCaptura


class GestionCapturaTests(dominio.BaseDominio):
    def setUp(self):
        super().setUp()
        call_command('configurar_roles', stdout=StringIO())
        self.admin = get_user_model().objects.create_user('administrador_gestion')
        self.admin.groups.add(Group.objects.get(name='Administración'))
        self.usuario.groups.add(Group.objects.get(name='Registro'))
        self.servicio = self.nuevo_servicio()
        self.etiqueta = self.bandeja.etiquetas.get(revocada_en__isnull=True)
        self.anular_url = reverse('captura:anular_servicio', args=[self.servicio.pk])
        self.reemplazar_url = reverse('captura:reemplazar_etiqueta', args=[self.bandeja.pk])
        self.client.force_login(self.admin)

    def test_get_no_anula_ni_reemplaza_y_muestra_datos_y_qr(self):
        for url in (self.anular_url, self.reemplazar_url):
            self.assertEqual(self.client.get(url).status_code, 200)
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, 'PENDIENTE_SERVIDO')
        self.assertEqual(self.bandeja.etiquetas.count(), 1)
        response = self.client.get(reverse('captura:gestion'), {'numero': 1})
        self.assertContains(response, 'Anular servicio')
        self.assertContains(response, 'Descargar QR')
        qr = self.client.get(reverse('captura:qr_etiqueta', args=[self.etiqueta.pk]))
        self.assertEqual(qr.status_code, 200)
        self.assertEqual(qr['Content-Type'], 'image/svg+xml')
        self.assertIn(b'<svg', qr.content)
        self.assertIn('no-store', qr['Cache-Control'])

    def test_anular_exige_motivo_confirmacion_y_conserva_foto_auditoria(self):
        self.capturar(self.servicio, 'SERVIDO')
        for data in ({'motivo': 'Prueba'}, {'confirmar': True, 'motivo': '   '}):
            self.assertEqual(self.client.post(self.anular_url, data).status_code, 200)
            self.servicio.refresh_from_db()
            self.assertEqual(self.servicio.estado_captura, 'EN_ESPERA_RETORNO')
        response = self.client.post(self.anular_url, {'motivo': 'Bandeja equivocada', 'confirmar': True})
        self.assertEqual(response.status_code, 302)
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, 'ANULADO')
        self.assertEqual(self.servicio.anulado_por, self.admin)
        self.assertEqual(self.servicio.anulado_motivo, 'Bandeja equivocada')
        self.assertIsNotNone(self.servicio.anulado_en)
        self.assertEqual(self.servicio.fotografias.count(), 1)
        self.assertFalse(self.servicio.asignaciones.filter(fin__isnull=True).exists())
        self.client.post(self.anular_url, {'motivo': 'Reenvío', 'confirmar': True})
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.anulado_motivo, 'Bandeja equivocada')

    def test_anulacion_cancela_solicitudes_pendientes(self):
        sesion, _ = services.crear_sesion_captura(servicio=self.servicio, etapa='SERVIDO', usuario=self.usuario)
        self.client.post(self.anular_url, {'motivo': 'Error', 'confirmar': True})
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, SesionCaptura.Estado.CANCELADA)

    def test_reemplazo_repetido_no_revoca_la_etiqueta_nueva(self):
        asignacion = self.servicio.asignaciones.get()
        datos = {'motivo': 'QR deteriorado', 'confirmar': True, 'etiqueta_actual': self.etiqueta.codigo}
        self.assertEqual(self.client.post(self.reemplazar_url, datos).status_code, 302)
        self.etiqueta.refresh_from_db()
        self.assertEqual(self.etiqueta.revocada_por, self.admin)
        self.assertEqual(self.etiqueta.motivo_revocacion, 'QR deteriorado')
        nueva = self.bandeja.etiquetas.get(revocada_en__isnull=True)
        self.assertNotEqual(nueva.codigo, self.etiqueta.codigo)
        self.assertEqual(self.client.post(self.reemplazar_url, datos).status_code, 200)
        self.assertEqual(self.bandeja.etiquetas.count(), 2)
        self.assertEqual(self.bandeja.etiquetas.get(revocada_en__isnull=True).pk, nueva.pk)
        asignacion.refresh_from_db()
        self.assertIsNone(asignacion.fin)
        self.assertEqual(asignacion.servicio_id, self.servicio.pk)
        self.assertEqual(self.client.get(reverse('captura:qr_etiqueta', args=[self.etiqueta.pk])).status_code, 404)

    def test_rol_registro_no_puede_ver_ni_mutar_gestion(self):
        self.client.force_login(self.usuario)
        for url in (reverse('captura:gestion'), self.anular_url, self.reemplazar_url,
                    reverse('captura:qr_etiqueta', args=[self.etiqueta.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.client.post(url, {'motivo': 'No autorizado', 'confirmar': True}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.anular_url).status_code, 302)

    def test_admin_sin_permiso_especifico_y_post_sin_csrf_se_rechazan(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.admin)
        self.assertEqual(csrf.post(self.anular_url, {'motivo': 'Error', 'confirmar': True}).status_code, 403)
        grupo = Group.objects.get(name='Administración')
        grupo.permissions.clear()
        self.assertEqual(self.client.post(self.anular_url, {'motivo': 'Error', 'confirmar': True}).status_code, 403)

    def test_no_anula_par_completo_y_busqueda_invalida_no_falla(self):
        self.capturar(self.servicio, 'SERVIDO')
        self.capturar(self.servicio, 'RETORNO')
        self.client.post(self.anular_url, {'motivo': 'Error', 'confirmar': True})
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, 'PAR_COMPLETO')
        self.assertContains(self.client.get(reverse('captura:gestion'), {'numero': 'x'}), 'errorlist')
