from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.core.management import call_command
from django.test import TestCase
from apps.captura.models import Servicio
from .models import Componente, Plato, PlatoComponente, TipoPorcion


class RetiroMaduroTests(TestCase):
    def test_retiro_conserva_instantanea_y_no_reaparece_al_restablecer(self):
        call_command('cargar_catalogo_demo', verbosity=0)
        plato = Plato.objects.get(codigo='seco_de_pollo')
        porcion = TipoPorcion.objects.get(codigo='estandar')
        maduro = Componente.objects.create(codigo='maduro', nombre='Maduro')
        relacion = PlatoComponente.objects.create(plato=plato, componente=maduro)
        anterior = Servicio.registrar(plato=plato, porcion=porcion)
        retirar = import_module('apps.catalogo.migrations.0002_retirar_maduro_piloto').retirar
        retirar(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        call_command('cargar_catalogo_demo', '--restablecer', verbosity=0)
        posterior = Servicio.registrar(plato=plato, porcion=porcion)
        self.assertSetEqual(set(anterior.composicion.values_list('componente_codigo', flat=True)), {'arroz','pollo','maduro'})
        self.assertSetEqual(set(posterior.composicion.values_list('componente_codigo', flat=True)), {'arroz','pollo'})
        relacion.refresh_from_db(); maduro.refresh_from_db()
        self.assertFalse(relacion.activo)
        self.assertFalse(maduro.activo)
