"""Persistencia y transiciones del dominio de Isaac, no worker HTTP de Lino.

Las fotos son filas sintéticas; no se leen ni escriben archivos operativos.
"""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.analisis import services
from apps.analisis.models import ArtefactoAnalisis, IntentoAnalisis, ResultadoComponente
from apps.captura.models import FotografiaServicio, Servicio
from apps.catalogo.models import Plato, TipoPorcion, Componente, PlatoComponente


class PersistenciaIntentosComplementariaTests(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        # Composición histórica explícita, independiente del catálogo actual.
        maduro, _ = Componente.objects.get_or_create(codigo="maduro", defaults={"nombre":"Maduro"})
        PlatoComponente.objects.get_or_create(plato=Plato.objects.get(codigo="seco_de_pollo"), componente=maduro)
        self.usuario = get_user_model().objects.create_user(username="fixture_analisis")
        self.servicio = Servicio.registrar(
            plato=Plato.objects.get(codigo="seco_de_pollo"),
            porcion=TipoPorcion.objects.get(codigo="estandar"), usuario=self.usuario,
        )
        self.fotos = {}
        for etapa in ("SERVIDO", "RETORNO"):
            self.fotos[etapa] = FotografiaServicio.objects.create(
                servicio=self.servicio, etapa=etapa, clave_archivo=f"fixture/{etapa}",
                tipo_contenido="image/png", tamano_bytes=10, ancho=4, alto=4,
                autor=self.usuario,
            )
        Servicio.objects.filter(pk=self.servicio.pk).update(estado_captura="PAR_COMPLETO")
        self.servicio.refresh_from_db()
        self.analisis, _, _ = services.solicitar_analisis(
            servicio=self.servicio, solicitante=self.usuario,
            version_modelo="fixture-m1", version_configuracion="fixture-c1",
            origen="SIMULADO",
        )
        self.intento = services.reclamar_siguiente_intento()
        self.componentes = list(self.servicio.composicion.all())

    def completar(self, intento=None, **cambios):
        intento = intento or self.intento
        datos = dict(
            intento=intento, request_id=str(intento.pk), version_modelo="fixture-m1",
            version_configuracion="fixture-c1", origen="SIMULADO",
            resultados=[dict(servicio_componente=c, area_inicial=100, area_residual=25,
                             confianza=0.9, umbral_confianza=0.8, comparable=True,
                             oculto=False, criterio="fixture-no-aprobado")
                        for c in self.componentes],
            artefactos=[dict(servicio_componente=self.componentes[0], etapa="SERVIDO",
                            clave_archivo="fixture/mascara.png", hash_sha256="a" * 64,
                            ancho=4, alto=4)],
        )
        datos.update(cambios)
        return services.completar_intento(**datos)

    def verificar_sin_publicar(self):
        self.intento.refresh_from_db()
        self.analisis.refresh_from_db()
        self.assertEqual(self.intento.estado, "EN_PROCESO")
        self.assertIsNone(self.analisis.intento_vigente_id)
        self.assertEqual(ResultadoComponente.objects.count(), 0)
        self.assertEqual(ArtefactoAnalisis.objects.count(), 0)

    def test_fallo_segundo_resultado_revierte_la_primera_fila(self):
        original = ResultadoComponente.objects.create
        llamadas = 0

        def crear(**datos):
            nonlocal llamadas
            llamadas += 1
            if llamadas == 2:
                raise RuntimeError("fallo de persistencia simulado")
            return original(**datos)

        with patch.object(ResultadoComponente.objects, "create", side_effect=crear):
            with self.assertRaisesMessage(RuntimeError, "fallo de persistencia"):
                self.completar()
        self.assertEqual(llamadas, 2)
        self.verificar_sin_publicar()

    def test_fallo_metadatos_mascara_revierte_resultados_y_cierre(self):
        with patch.object(ArtefactoAnalisis.objects, "create", side_effect=RuntimeError("máscara simulada")):
            with self.assertRaisesMessage(RuntimeError, "máscara simulada"):
                self.completar()
        self.verificar_sin_publicar()

    def test_componente_duplicado_rechaza_respuesta_completa(self):
        fila = dict(servicio_componente=self.componentes[0], area_inicial=100,
                    area_residual=1, comparable=True, oculto=False)
        with self.assertRaises(ValidationError):
            self.completar(resultados=[fila, fila])
        self.verificar_sin_publicar()

    def test_respuesta_antigua_no_altera_reintento_actual(self):
        services.fallar_intento(intento=self.intento, tipo_error="ERROR_MOTOR")
        nuevo = services.reintentar_analisis(analisis=self.analisis)
        reclamado = services.reclamar_siguiente_intento()
        self.assertEqual(reclamado.pk, nuevo.pk)
        with self.assertRaises(ValidationError):
            self.completar()
        nuevo.refresh_from_db()
        self.assertEqual(nuevo.estado, "EN_PROCESO")
        self.assertEqual(ResultadoComponente.objects.count(), 0)
        self.completar(intento=nuevo)
        self.intento.refresh_from_db()
        self.analisis.refresh_from_db()
        self.assertEqual(self.intento.estado, "FALLIDO")
        self.assertEqual(self.analisis.intento_vigente_id, nuevo.pk)
        self.assertFalse(ResultadoComponente.objects.filter(intento=self.intento).exists())

    def test_exactamente_en_limite_y_despues(self):
        limite = self.intento.limite_en
        with patch("apps.analisis.services.timezone.now", return_value=limite):
            hecho = self.completar()
        self.assertEqual(hecho.estado, "COMPLETADO")
        self.assertEqual(hecho.duracion_ms, 30000)

    def test_un_microsegundo_tarde_no_publica(self):
        tarde = self.intento.limite_en + timedelta(microseconds=1)
        with patch("apps.analisis.services.timezone.now", return_value=tarde):
            with self.assertRaises(ValidationError):
                self.completar()
        self.intento.refresh_from_db()
        self.assertEqual(self.intento.estado, "TIEMPO_AGOTADO")
        self.assertEqual(ResultadoComponente.objects.count(), 0)
        self.assertEqual(ArtefactoAnalisis.objects.count(), 0)

    def test_retencion_exacta_usa_foto_padre_y_no_fecha_analisis(self):
        self.completar()
        mascara = ArtefactoAnalisis.objects.get()
        vencimiento = self.fotos["SERVIDO"].fecha + timedelta(days=90)
        self.assertFalse(services.artefactos_vencidos(
            ahora=vencimiento - timedelta(microseconds=1)).filter(pk=mascara.pk).exists())
        self.assertTrue(services.artefactos_vencidos(
            ahora=vencimiento).filter(pk=mascara.pk).exists())
        self.assertTrue(services.artefactos_vencidos(
            ahora=vencimiento + timedelta(microseconds=1)).filter(pk=mascara.pk).exists())
