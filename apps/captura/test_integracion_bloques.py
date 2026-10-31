"""Verifica las entregas combinadas; solo usa SQLite y archivos temporales."""
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
import tempfile
from unittest.mock import patch

from PIL import Image
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.catalogo.models import Plato, TipoPorcion
from . import services, storage
from .forms import procesar_imagen
from .models import Bandeja, FotografiaServicio, Servicio, SesionCaptura
from . import test_dominio_bandejas as dominio


def foto(exif=False):
    image = Image.new('RGB', (8, 6), 'green')
    output = BytesIO()
    metadata = Image.Exif()
    if exif:
        metadata[274] = 6
        metadata[315] = 'Autor privado de prueba'
    image.save(output, 'PNG', exif=metadata)
    return SimpleUploadedFile('prueba.png', output.getvalue(), content_type='image/png')


class ValidacionIntegradaTests(SimpleTestCase):
    def test_png_no_conserva_exif_y_respeta_orientacion(self):
        imagen = procesar_imagen(foto(exif=True))
        self.assertEqual((imagen.ancho, imagen.alto), (6, 8))
        with Image.open(BytesIO(imagen.contenido)) as decoded:
            self.assertFalse(decoded.getexif())
            self.assertNotIn('exif', decoded.info)
        self.assertNotIn(b'Autor privado', imagen.contenido)

    @override_settings(EVA_CAPTURE_MAX_PIXELS=4)
    def test_validador_usa_limite_de_settings(self):
        with self.assertRaises(forms.ValidationError):
            procesar_imagen(foto())


class RecorridoCapturaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for command in ('cargar_catalogo_demo', 'cargar_bandejas_demo', 'configurar_roles'):
            call_command(command, stdout=StringIO())
        cls.operador = get_user_model().objects.create_user(username='integracion_registro_a')
        cls.otro = get_user_model().objects.create_user(username='integracion_registro_b')
        for user in (cls.operador, cls.otro):
            user.groups.add(Group.objects.get(name='Registro'))
        cls.cocina = get_user_model().objects.create_user(username='integracion_cocina')
        cls.cocina.groups.add(Group.objects.get(name='Cocina'))
        cls.plato = Plato.objects.get(codigo='seco_de_pollo')
        cls.porcion = TipoPorcion.objects.get(codigo='estandar')

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / 'fotos'
        settings = self.settings(EVA_CAPTURE_PRIVATE_ROOT=self.root, EVA_STORAGE_BACKEND='local')
        settings.enable()
        self.addCleanup(settings.disable)
        self.client.force_login(self.operador)

    def crear(self):
        response = self.client.post(reverse('captura:resolver_bandeja') + '?numero=1', {
            'plato': self.plato.pk, 'tipo_porcion': self.porcion.pk,
        })
        self.assertEqual(response.status_code, 302)
        return Servicio.objects.get(estado_captura='PENDIENTE_SERVIDO')

    def servido(self, servicio):
        return self.client.post(reverse('captura:foto_servido', args=[servicio.pk]), {'foto': foto()})

    def test_recorrido_dos_operadores_con_lectura_privada_y_liberacion(self):
        servicio = self.crear()
        self.assertEqual(self.servido(servicio).status_code, 302)
        self.client.force_login(self.otro)
        search = reverse('captura:buscar_retorno') + '?numero=1'
        response = self.client.get(search)
        self.assertContains(response, 'Seco de pollo')
        self.assertEqual(self.client.post(search, {'confirmar': True}).status_code, 302)
        self.assertEqual(self.client.post(reverse('captura:foto_retorno', args=[servicio.pk]), {'foto': foto()}).status_code, 302)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, 'PAR_COMPLETO')
        self.assertEqual(servicio.creado_por, self.operador)
        self.assertEqual(servicio.fotografias.get(etapa='RETORNO').autor, self.otro)
        self.assertFalse(servicio.asignaciones.filter(fin__isnull=True).exists())
        self.assertEqual(self.client.get(reverse('captura:confirmacion', args=[servicio.pk])).status_code, 404)
        image_url = reverse('captura:imagen', args=[servicio.fotografias.get(etapa='SERVIDO').pk])
        response = self.client.get(image_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        response.close()
        self.client.force_login(self.cocina)
        self.assertEqual(self.client.get(image_url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(image_url).status_code, 302)

    def test_retorno_sin_servido_no_muestra_formulario_ni_acepta_foto(self):
        servicio = self.crear()
        url = reverse('captura:foto_retorno', args=[servicio.pk])
        response = self.client.post(url, {'foto': foto()})
        self.assertContains(response, 'Primero debe registrarse')
        self.assertNotContains(response, 'type="file"')
        self.assertFalse(servicio.fotografias.exists())

    def test_duplicado_no_sobrescribe(self):
        servicio = self.crear()
        self.servido(servicio)
        original = servicio.fotografias.get()
        self.servido(servicio)
        self.assertEqual(servicio.fotografias.count(), 1)
        self.assertEqual(servicio.fotografias.get().clave_archivo, original.clave_archivo)

    def test_error_de_storage_no_avanza_estado(self):
        servicio = self.crear()
        with patch('apps.captura.storage.guardar', side_effect=storage.ErrorAlmacenamiento):
            response = self.servido(servicio)
        self.assertContains(response, 'No se pudo guardar')
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, 'PENDIENTE_SERVIDO')
        self.assertFalse(servicio.fotografias.exists())

    def test_rechazo_de_bd_elimina_archivo_huerfano(self):
        servicio = self.crear()
        with patch('apps.captura.services.registrar_captura', side_effect=ValidationError('Rechazo de prueba')):
            response = self.servido(servicio)
        self.assertContains(response, 'Rechazo de prueba')
        self.assertFalse(list(self.root.rglob('*.png')))

    def test_limpieza_fallida_se_registra_para_reintentar(self):
        servicio = self.crear()
        with patch('apps.captura.services.registrar_captura', side_effect=ValidationError('Rechazo de prueba')):
            with patch('apps.captura.storage.eliminar', side_effect=storage.ErrorAlmacenamiento):
                with self.assertLogs('apps.captura.views', level='ERROR') as logs:
                    self.servido(servicio)
        self.assertIn('EVA_CAPTURE_ORPHAN', logs.output[0])
        self.assertFalse(servicio.fotografias.exists())

    def test_csrf_y_roles_se_comprueban_en_post(self):
        url = reverse('captura:resolver_bandeja') + '?numero=1'
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.operador)
        self.assertEqual(csrf.post(url, {}).status_code, 403)
        self.client.force_login(self.cocina)
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.assertFalse(Servicio.objects.exists())

    def test_s3_sin_adaptador_no_escribe_en_local(self):
        servicio = self.crear()
        with override_settings(EVA_STORAGE_BACKEND='s3'):
            response = self.servido(servicio)
        self.assertContains(response, 'No se pudo guardar')
        self.assertFalse(self.root.exists())
        self.assertFalse(servicio.fotografias.exists())


class SesionIntegradaTests(dominio.BaseDominio):
    @override_settings(EVA_CAPTURE_LINK_TTL_SECONDS=45)
    def test_sesion_respeta_ttl_configurado(self):
        sesion, _ = services.crear_sesion_captura(
            servicio=self.nuevo_servicio(), etapa='SERVIDO', usuario=self.usuario,
        )
        self.assertEqual(sesion.expira_en - sesion.creada_en, timedelta(seconds=45))

    def test_expiracion_entre_consulta_y_consumo_revierte_la_captura(self):
        servicio = self.nuevo_servicio()
        sesion, token = services.crear_sesion_captura(servicio=servicio, etapa='SERVIDO', usuario=self.usuario)
        registrar = services.registrar_captura

        def vence_durante_registro(**kwargs):
            foto = registrar(**kwargs)
            SesionCaptura.objects.filter(pk=sesion.pk).update(expira_en=timezone.now() - timedelta(seconds=1))
            return foto

        with patch('apps.captura.services.registrar_captura', side_effect=vence_durante_registro):
            with self.assertRaises(ValidationError):
                services.consumir_sesion(token=token, autor=self.usuario, clave_archivo='prueba/foto.png',
                                        tipo_contenido='image/png', tamano_bytes=10, ancho=8, alto=6)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, 'PENDIENTE_SERVIDO')
        self.assertFalse(FotografiaServicio.objects.filter(servicio=servicio).exists())
