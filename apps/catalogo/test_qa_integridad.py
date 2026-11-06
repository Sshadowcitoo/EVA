import sqlite3
from unittest.mock import patch

from django.db import OperationalError
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.catalogo.forms import PlatoForm
from apps.catalogo.models import Plato, TipoPorcion
from apps.captura.models import Servicio, ServicioComponente, Bandeja, AsignacionBandeja


class ComposicionObligatoriaTests(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        self.plato = Plato.objects.get(codigo="seco_de_pollo")
        self.porcion = TipoPorcion.objects.get(codigo="estandar")

    def test_formulario_no_crea_plato_sin_componentes(self):
        form = PlatoForm(data={"codigo": "vacio", "nombre": "Vacío"})
        self.assertFalse(form.is_valid())
        self.assertIn("composicion", form.errors)
        self.assertFalse(Plato.objects.filter(codigo="vacio").exists())

    def test_edicion_no_vacia_composicion_ni_instantanea(self):
        servicio = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        anteriores = list(servicio.composicion.values_list("componente_codigo", flat=True))
        form = PlatoForm(instance=self.plato, data={"nombre": "Otro"})
        self.assertFalse(form.is_valid())
        self.assertIn("composicion", form.errors)
        self.assertEqual(list(servicio.composicion.values_list("componente_codigo", flat=True)), anteriores)
        self.assertEqual(self.plato.relaciones.filter(activo=True).count(), 2)

    def test_dominio_rechaza_composicion_vacia_sin_filas_parciales(self):
        for causa in ("sin_relaciones", "componentes_inactivos"):
            with self.subTest(causa=causa):
                if causa == "sin_relaciones":
                    self.plato.relaciones.update(activo=False)
                else:
                    self.plato.relaciones.update(activo=True)
                    for relacion in self.plato.relaciones.select_related("componente"):
                        relacion.componente.activo = False
                        relacion.componente.save(update_fields=["activo"])
                bandeja = Bandeja.objects.create(numero=100 if causa == "sin_relaciones" else 101)
                for soporte in (None, bandeja):
                    with self.subTest(bandeja=soporte), self.assertRaisesMessage(ValidationError, "componente activo"):
                        Servicio.registrar(plato=self.plato, porcion=self.porcion, bandeja=soporte)
                self.assertEqual(Servicio.objects.count(), 0)
                self.assertEqual(ServicioComponente.objects.count(), 0)
                self.assertEqual(AsignacionBandeja.objects.count(), 0)

    def test_bloqueo_sqlite_rechaza_y_revierte_servicio_parcial(self):
        original = ServicioComponente.objects.bulk_create
        def bloquear(*args, **kwargs):
            original(*args, **kwargs)
            causa = sqlite3.OperationalError("database is locked")
            causa.sqlite_errorcode = sqlite3.SQLITE_BUSY
            raise OperationalError("database is locked") from causa
        with patch.object(ServicioComponente.objects, "bulk_create", side_effect=bloquear):
            with self.assertRaisesMessage(ValidationError, "otro registro en curso"):
                Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.assertEqual(Servicio.objects.count(), 0)
        self.assertEqual(ServicioComponente.objects.count(), 0)

    def test_no_oculta_otros_errores_de_base_de_datos(self):
        with patch.object(Servicio.objects, "create", side_effect=OperationalError("disk I/O error")):
            with self.assertRaisesMessage(OperationalError, "disk I/O error"):
                Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.assertEqual(Servicio.objects.count(), 0)
