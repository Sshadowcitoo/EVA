from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import SesionCaptura
from .protocolo import CRITERIOS, VERSION
from .test_dominio_bandejas import BaseDominio
from .test_integracion_bloques import foto


class VinculacionHTTPTests(BaseDominio):
    def setUp(self):
        super().setUp()
        call_command("configurar_roles", stdout=StringIO())
        self.usuario.groups.add(Group.objects.get(name="Registro"))
        self.client.force_login(self.usuario)
        self.telefono = Client()
        self.telefono.force_login(self.usuario)
        self.servicio = self.nuevo_servicio()
        self.directa = reverse("captura:foto_servido", args=[self.servicio.pk])
        self.pc = reverse("captura:vincular", args=[self.servicio.pk, "SERVIDO"])
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        ajuste = self.settings(EVA_STORAGE_BACKEND="local", EVA_CAPTURE_PRIVATE_ROOT=Path(self.temporal.name))
        ajuste.enable()
        self.addCleanup(ajuste.disable)

    def crear(self):
        respuesta = self.client.post(self.pc)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "data:image/svg+xml;base64,")
        return respuesta.context["captura_url"], SesionCaptura.objects.latest("creada_en")

    def datos(self):
        return {"foto": foto(), **dict.fromkeys(CRITERIOS, True)}

    def test_pc_telefono_checklist_persistido_y_reintento_no_duplica(self):
        url, sesion = self.crear()
        self.assertNotIn(url.split("token=")[1], sesion.token_digest)
        self.assertEqual(self.telefono.get(url).status_code, 200)
        respuesta = self.telefono.post(url, self.datos())
        self.assertEqual(respuesta.status_code, 302)
        fotografia = self.servicio.fotografias.get()
        self.assertEqual(fotografia.checklist, dict.fromkeys(CRITERIOS, True))
        self.assertEqual(fotografia.protocolo_version, VERSION)
        self.assertEqual(fotografia.autor, self.usuario)
        self.assertIsNotNone(fotografia.fecha)
        estado = self.client.get(reverse("captura:estado_vinculacion", args=[sesion.pk]))
        self.assertEqual(estado.json()["estado"], "COMPLETADA")
        self.assertIn("no-store", estado["Cache-Control"])
        self.assertContains(self.telefono.post(url, self.datos()), "Captura ya completada")
        self.assertEqual(self.servicio.fotografias.count(), 1)
        self.assertContains(self.client.get(self.directa), "hora de Ecuador")

    def test_checklist_obligatorio_en_ambos_recorridos(self):
        url, _ = self.crear()
        for destino in (self.directa, url):
            with patch("apps.captura.storage.guardar") as guardar:
                self.assertEqual(self.client.post(destino, {"foto": foto()}).status_code, 200)
                guardar.assert_not_called()
        self.assertFalse(self.servicio.fotografias.exists())

    def test_cancelar_caducar_regenerar_y_captura_directa_invalidan(self):
        anterior, sesion = self.crear()
        nuevo, segunda = self.crear()
        self.assertContains(self.telefono.get(anterior), "Enlace cancelado")
        SesionCaptura.objects.filter(pk=segunda.pk).update(expira_en=timezone.now() - timedelta(seconds=1))
        self.assertContains(self.telefono.post(nuevo, self.datos()), "Enlace caducado")
        tercero, sesion = self.crear()
        self.assertEqual(self.client.get(reverse("captura:cancelar_vinculacion", args=[sesion.pk])).status_code, 405)
        self.client.post(reverse("captura:cancelar_vinculacion", args=[sesion.pk]))
        self.assertContains(self.telefono.get(tercero), "Enlace cancelado")
        cuarto, sesion = self.crear()
        self.assertEqual(self.client.post(self.directa, self.datos()).status_code, 302)
        self.assertContains(self.telefono.get(cuarto), "Enlace cancelado")

    def test_login_rol_csrf_y_token_invalido(self):
        url, sesion = self.crear()
        anonimo = Client()
        self.assertEqual(anonimo.get(url).status_code, 302)
        self.usuario.groups.clear()
        self.assertEqual(self.telefono.get(url).status_code, 403)
        self.usuario.groups.add(Group.objects.get(name="Registro"))
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.usuario)
        self.assertEqual(csrf.post(self.pc).status_code, 403)
        self.assertEqual(csrf.post(url, self.datos()).status_code, 403)
        self.assertEqual(self.telefono.get(reverse("captura:captura_vinculada") + "?token=invalido").status_code, 404)

    def test_fallo_bd_compensa_archivo_y_no_consume_enlace(self):
        from django.core.exceptions import ValidationError
        url, sesion = self.crear()
        with patch("apps.captura.services.consumir_sesion", side_effect=ValidationError("Prueba")):
            self.assertEqual(self.telefono.post(url, self.datos()).status_code, 200)
        self.assertFalse(list(Path(self.temporal.name).rglob("*.png")))
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, "PENDIENTE")

    def test_datos_historicos_no_reciben_confirmaciones_inventadas(self):
        fotografia = self.capturar(self.servicio, "SERVIDO")
        self.assertEqual(fotografia.checklist, {})
        self.assertEqual(fotografia.protocolo_version, "")

    def test_retorno_vinculado_por_otro_operador_libera_bandeja(self):
        from django.contrib.auth import get_user_model
        otro = get_user_model().objects.create_user(username="otro_registro_vinculado")
        otro.groups.add(Group.objects.get(name="Registro"))
        self.telefono.force_login(otro)
        self.client.post(self.directa, self.datos())
        self.pc = reverse("captura:vincular", args=[self.servicio.pk, "RETORNO"])
        url, sesion = self.crear()
        self.assertContains(self.telefono.get(url), "Foto del servido")
        self.assertEqual(self.telefono.post(url, self.datos()).status_code, 302)
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, "PAR_COMPLETO")
        self.assertEqual(self.servicio.fotografias.get(etapa="RETORNO").autor, otro)
        self.assertFalse(self.bandeja.asignaciones.filter(fin__isnull=True).exists())

    def test_log_no_expone_token_en_url_ni_next_codificado(self):
        import logging
        from .logging import OcultarTokenCaptura
        record = logging.LogRecord("django.server", 20, __file__, 1,
            'GET %s', ("/vinculada/?token=secreto HTTP/1.1 /login/?next=%2Fvinculada%2F%3Ftoken%3Dsecreto",), None)
        OcultarTokenCaptura().filter(record)
        self.assertNotIn("secreto", record.getMessage())
