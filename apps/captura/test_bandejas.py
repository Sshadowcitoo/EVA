"""Casos complementarios contra los servicios de Isaac, no contra endpoints."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.captura import services
from apps.captura.models import Bandeja, EtiquetaBandeja, FotografiaServicio, Servicio
from apps.catalogo.models import Plato, TipoPorcion


class ConsistenciaBandejasTests(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        call_command("cargar_bandejas_demo", verbosity=0)
        self.usuario = get_user_model().objects.create_user(username="operador_b2")
        self.bandeja = Bandeja.objects.get(numero=1)
        self.servicio = Servicio.registrar(
            plato=Plato.objects.get(codigo="seco_de_pollo"),
            porcion=TipoPorcion.objects.get(codigo="estandar"),
            usuario=self.usuario, bandeja=self.bandeja,
        )

    def capturar(self, etapa="SERVIDO", **cambios):
        datos = dict(servicio=self.servicio, etapa=etapa, clave_archivo="prueba/foto.png",
                     tipo_contenido="image/png", tamano_bytes=100, ancho=10, alto=10,
                     autor=self.usuario)
        datos.update(cambios)
        return services.registrar_captura(**datos)

    def test_fallo_metadatos_revierte_estado_y_conserva_asignacion(self):
        with patch.object(FotografiaServicio.objects, "create", side_effect=RuntimeError("BD simulada")):
            with self.assertRaisesMessage(RuntimeError, "BD simulada"):
                self.capturar()
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, "PENDIENTE_SERVIDO")
        self.assertEqual(self.servicio.fotografias.count(), 0)
        self.assertEqual(self.servicio.asignaciones.filter(fin__isnull=True).count(), 1)

    def test_fallo_al_cerrar_retorno_revierte_foto_y_estado(self):
        self.capturar()
        with patch("apps.captura.services._cerrar_asignacion", side_effect=RuntimeError("cierre simulado")):
            with self.assertRaisesMessage(RuntimeError, "cierre simulado"):
                self.capturar("RETORNO")
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, "EN_ESPERA_RETORNO")
        self.assertSetEqual(set(self.servicio.fotografias.values_list("etapa", flat=True)), {"SERVIDO"})
        self.assertEqual(self.servicio.asignaciones.filter(fin__isnull=True).count(), 1)

    def test_fallo_emision_revierte_revocacion(self):
        anterior = self.bandeja.etiquetas.get(revocada_en__isnull=True)
        with patch("apps.captura.services.emitir_etiqueta", side_effect=RuntimeError("emisión simulada")):
            with self.assertRaisesMessage(RuntimeError, "emisión simulada"):
                services.reemplazar_etiqueta(bandeja=self.bandeja, motivo="Dañada", usuario=self.usuario)
        anterior.refresh_from_db()
        self.assertIsNone(anterior.revocada_en)
        self.assertEqual(EtiquetaBandeja.objects.filter(bandeja=self.bandeja).count(), 1)

    def test_carga_repetida_conserva_asignacion_operativa(self):
        asignacion = self.servicio.asignaciones.get()
        codigos = list(self.bandeja.etiquetas.values_list("codigo", flat=True))
        call_command("cargar_bandejas_demo", verbosity=0)
        asignacion.refresh_from_db()
        self.assertIsNone(asignacion.fin)
        self.assertEqual(asignacion.servicio_id, self.servicio.pk)
        self.assertEqual(list(self.bandeja.etiquetas.values_list("codigo", flat=True)), codigos)

    def test_anulado_no_acepta_foto_y_conserva_auditoria(self):
        services.anular_servicio(servicio=self.servicio, motivo="Prueba", usuario=self.usuario)
        with self.assertRaises(ValidationError):
            self.capturar()
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, "ANULADO")
        self.assertEqual(self.servicio.anulado_motivo, "Prueba")
        self.assertEqual(self.servicio.anulado_por_id, self.usuario.pk)
        self.assertEqual(self.servicio.fotografias.count(), 0)
