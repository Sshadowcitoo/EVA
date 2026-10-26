"""Pruebas complementarias al contrato publicado por Isaac en 80f90d6.

Requieren sus modelos, migraciones y comando de carga, y catalogo registrado.
No sustituyen ni duplican la suite test_models.py publicada por Isaac.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.captura.models import Servicio, ServicioComponente
from apps.catalogo.models import Componente, Plato, PlatoComponente, TipoPorcion


class ServicioCatalogoComplementarioTests(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        self.plato = Plato.objects.get(codigo="seco_de_pollo")
        self.porcion = TipoPorcion.objects.get(codigo="estandar")

    def test_alta_conserva_usuario_creador(self):
        usuario = get_user_model().objects.create_user(username="registro_prueba")

        servicio = Servicio.registrar(
            plato=self.plato, porcion=self.porcion, usuario=usuario
        )

        servicio.refresh_from_db()
        self.assertEqual(Servicio.objects.count(), 1)
        self.assertEqual(servicio.creado_por_id, usuario.pk)

    def test_fallo_de_composicion_revierte_servicio_e_instantaneas(self):
        # Simula una escritura parcial antes del fallo para comprobar el rollback.
        def escribir_parcial_y_fallar(objetos):
            primero = next(iter(objetos))
            primero.save()
            raise RuntimeError("Fallo simulado al guardar la composición")

        with patch.object(
            ServicioComponente.objects,
            "bulk_create",
            side_effect=escribir_parcial_y_fallar,
        ):
            with self.assertRaisesMessage(RuntimeError, "Fallo simulado"):
                Servicio.registrar(plato=self.plato, porcion=self.porcion)

        self.assertEqual(Servicio.objects.count(), 0)
        self.assertEqual(ServicioComponente.objects.count(), 0)
        self.assertEqual(Plato.objects.count(), 3)

    def test_renombrar_porcion_no_reescribe_etiqueta_previa(self):
        anterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.porcion.nombre = "Estándar revisada"
        self.porcion.save(update_fields=["nombre"])

        posterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)

        anterior.refresh_from_db()
        posterior.refresh_from_db()
        self.assertEqual(anterior.get_tipo_porcion_display(), "Estándar")
        self.assertEqual(posterior.get_tipo_porcion_display(), "Estándar revisada")
        self.assertEqual(anterior.porcion_catalogo_id, posterior.porcion_catalogo_id)
        self.assertEqual(Servicio.objects.count(), 2)

    def test_relacion_inactiva_excluida_solo_de_servicios_nuevos(self):
        anterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        PlatoComponente.objects.filter(
            plato=self.plato, componente__codigo="maduro"
        ).update(activo=False)

        posterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)

        self.assertSetEqual(
            set(anterior.composicion.values_list("componente_codigo", flat=True)),
            {"arroz", "pollo", "maduro"},
        )
        self.assertSetEqual(
            set(posterior.composicion.values_list("componente_codigo", flat=True)),
            {"arroz", "pollo"},
        )


class CargaDemoComplementariaTests(TestCase):
    def test_repetir_carga_conserva_elementos_y_composicion_personalizados(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        plato = Plato.objects.get(codigo="seco_de_pollo")
        adicional = Componente.objects.create(codigo="aguacate", nombre="Aguacate")
        relacion = PlatoComponente.objects.create(plato=plato, componente=adicional)
        porcion = TipoPorcion.objects.get(codigo="estandar")
        porcion.nombre = "Porción de la casa"
        porcion.activo = False
        porcion.save()

        call_command("cargar_catalogo_demo", verbosity=0)

        porcion.refresh_from_db()
        self.assertEqual(porcion.nombre, "Porción de la casa")
        self.assertFalse(porcion.activo)
        self.assertTrue(PlatoComponente.objects.filter(pk=relacion.pk).exists())
        self.assertEqual(Plato.objects.count(), 3)
        self.assertEqual(Componente.objects.count(), 9)
        self.assertEqual(PlatoComponente.objects.count(), 10)
        self.assertEqual(TipoPorcion.objects.count(), 1)
