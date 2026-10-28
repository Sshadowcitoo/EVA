from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.captura.models import Servicio
from apps.catalogo.models import Componente, Plato, PlatoComponente, TipoPorcion


class CargaInicialTests(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)

    def test_carga_catalogo_coherente(self):
        self.assertEqual(Plato.objects.count(), 3)
        self.assertEqual(Componente.objects.count(), 8)
        self.assertEqual(TipoPorcion.objects.count(), 1)
        self.assertEqual(PlatoComponente.objects.count(), 9)

    def test_arroz_compartido_sin_duplicar(self):
        self.assertEqual(Componente.objects.filter(codigo="arroz").count(), 1)
        arroz = Componente.objects.get(codigo="arroz")
        self.assertEqual(arroz.platos.count(), 2)

    def test_carga_repetible_no_sobrescribe_cambios(self):
        plato = Plato.objects.get(codigo="encebollado")
        plato.nombre = "Encebollado mixto"
        plato.activo = False
        plato.save()
        PlatoComponente.objects.filter(plato=plato).update(activo=False)

        call_command("cargar_catalogo_demo", verbosity=0)

        plato.refresh_from_db()
        self.assertEqual(plato.nombre, "Encebollado mixto")
        self.assertFalse(plato.activo)
        self.assertEqual(Plato.objects.count(), 3)
        self.assertEqual(PlatoComponente.objects.count(), 9)
        self.assertFalse(PlatoComponente.objects.filter(plato=plato, activo=True).exists())

    def test_restablecer_restaura_demostracion(self):
        plato = Plato.objects.get(codigo="encebollado")
        plato.nombre = "Otro"
        plato.activo = False
        plato.save()

        call_command("cargar_catalogo_demo", "--restablecer", verbosity=0)

        plato.refresh_from_db()
        self.assertEqual(plato.nombre, "Encebollado")
        self.assertTrue(plato.activo)


class RestriccionesTests(TestCase):
    def test_codigo_de_plato_duplicado(self):
        Plato.objects.create(codigo="a", nombre="A")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Plato.objects.create(codigo="a", nombre="Otro A")

    def test_relacion_plato_componente_duplicada(self):
        plato = Plato.objects.create(codigo="p", nombre="P")
        comp = Componente.objects.create(codigo="c", nombre="C")
        PlatoComponente.objects.create(plato=plato, componente=comp)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PlatoComponente.objects.create(plato=plato, componente=comp)

    def test_no_se_borra_plato_referenciado(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        plato = Plato.objects.get(codigo="seco_de_pollo")
        porcion = TipoPorcion.objects.get(codigo="estandar")
        Servicio.registrar(plato=plato, porcion=porcion)
        with self.assertRaises(ProtectedError):
            plato.delete()


class ServicioCatalogoTests(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        self.plato = Plato.objects.get(codigo="seco_de_pollo")
        self.porcion = TipoPorcion.objects.get(codigo="estandar")

    def test_alta_guarda_referencias_e_instantanea(self):
        servicio = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.assertEqual(servicio.plato_catalogo, self.plato)
        self.assertEqual(servicio.porcion_catalogo, self.porcion)
        self.assertEqual(servicio.plato, "seco_de_pollo")
        self.assertEqual(servicio.get_plato_display(), "Seco de pollo")
        self.assertEqual(
            set(servicio.composicion.values_list("componente_codigo", flat=True)),
            {"arroz", "pollo", "maduro"},
        )

    def test_editar_catalogo_no_reescribe_servicios_anteriores(self):
        servicio = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.plato.nombre = "Seco renombrado"
        self.plato.save()
        Componente.objects.filter(codigo="pollo").update(nombre="Pollo guisado")
        PlatoComponente.objects.filter(
            plato=self.plato, componente__codigo="maduro"
        ).update(activo=False)

        servicio.refresh_from_db()
        self.assertEqual(servicio.get_plato_display(), "Seco de pollo")
        self.assertEqual(
            set(servicio.composicion.values_list("componente_nombre", flat=True)),
            {"Arroz", "Pollo", "Maduro"},
        )

    def test_desactivar_conserva_servicio_y_bloquea_nuevas_altas(self):
        servicio = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.plato.activo = False
        self.plato.save()

        servicio.refresh_from_db()
        self.assertEqual(servicio.plato_catalogo_id, self.plato.pk)
        with self.assertRaises(ValidationError):
            Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.assertEqual(Servicio.objects.count(), 1)

    def test_porcion_inactiva_no_crea_filas(self):
        self.porcion.activo = False
        self.porcion.save()
        with self.assertRaises(ValidationError):
            Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.assertEqual(Servicio.objects.count(), 0)

    def test_componente_inactivo_no_entra_en_la_composicion(self):
        Componente.objects.filter(codigo="maduro").update(activo=False)
        servicio = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.assertEqual(
            set(servicio.composicion.values_list("componente_codigo", flat=True)),
            {"arroz", "pollo"},
        )

    def test_registro_anterior_sigue_legible(self):
        antiguo = Servicio.objects.create(
            plato="arroz_con_pollo",
            plato_nombre="Arroz con pollo",
            tipo_porcion="grande",
            porcion_nombre="Grande",
        )
        self.assertIsNone(antiguo.plato_catalogo)
        self.assertEqual(antiguo.get_plato_display(), "Arroz con pollo")
        self.assertEqual(antiguo.get_tipo_porcion_display(), "Grande")
