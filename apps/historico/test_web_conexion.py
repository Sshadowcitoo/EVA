"""Recorridos HTTP con persistencia real; requieren la dependencia del PR #44."""
from datetime import datetime
from decimal import Decimal
from importlib.util import find_spec
from io import StringIO
from unittest import skipUnless
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import include, path

from apps.analisis.models import AnalisisServicio, IntentoAnalisis, ResultadoComponente, RevisionAnalisis
from apps.captura.models import Servicio, FotografiaServicio
from apps.captura.protocolo import CRITERIOS, VERSION
from apps.catalogo.models import Plato, TipoPorcion

urlpatterns = [path('historico/', include('apps.historico.urls')), path('', include('config.urls'))]


@skipUnless(find_spec('apps.historico.percepcion'), 'Requiere el dominio del PR #44; no se sustituye por mocks.')
@override_settings(ROOT_URLCONF=__name__, EVA_HISTORICO_CRITERIOS=dict(version='fixture-t20', aprobada=True, presencia_t=20))
class ConexionHistoricoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_catalogo_demo', verbosity=0)
        call_command('configurar_roles', stdout=StringIO())
        cls.admin = get_user_model().objects.create_user('admin_conexion')
        cls.admin.groups.add(Group.objects.get(name='Administración'))
        cls.registro = get_user_model().objects.create_user('registro_conexion')
        cls.registro.groups.add(Group.objects.get(name='Registro'))
        cls.cocina = get_user_model().objects.create_user('cocina_conexion')
        cls.cocina.groups.add(Group.objects.get(name='Cocina'))

    def caso(self, porcentaje, dia=3):
        servicio = Servicio.registrar(plato=Plato.objects.get(codigo='seco_de_pollo'), porcion=TipoPorcion.objects.get(codigo='estandar'), usuario=self.registro)
        Servicio.objects.filter(pk=servicio.pk).update(estado_captura='PAR_COMPLETO')
        fotos = {}
        for etapa in ('SERVIDO', 'RETORNO'):
            foto = FotografiaServicio.objects.create(servicio=servicio, etapa=etapa, clave_archivo=f'conexion/sin-bytes/{servicio.pk}/{etapa}.png', tipo_contenido='image/png', tamano_bytes=10, ancho=4, alto=4, autor=self.registro, protocolo_version=VERSION, checklist=dict.fromkeys(CRITERIOS, True))
            FotografiaServicio.objects.filter(pk=foto.pk).update(fecha=datetime(2026,10,dia,12,tzinfo=ZoneInfo('America/Guayaquil')))
            foto.refresh_from_db()
            fotos[etapa] = foto
        analisis = AnalisisServicio.objects.create(servicio=servicio, foto_servido=fotos['SERVIDO'], foto_retorno=fotos['RETORNO'], version_modelo='fixture-m1', version_configuracion='fixture-c1', origen='REAL', solicitante=self.cocina)
        intento = IntentoAnalisis.objects.create(analisis=analisis, numero=1, estado='COMPLETADO')
        analisis.intento_vigente = intento
        analisis.save(update_fields=['intento_vigente'])
        for componente in servicio.composicion.all():
            ResultadoComponente.objects.create(intento=intento, servicio_componente=componente, area_inicial=100, area_residual=porcentaje, porcentaje=Decimal(porcentaje), confianza=.9, umbral_aplicado=.7, configuracion_aprobada=True, criterio='fixture-c1', estado='CONCLUYENTE', motivo='')
        RevisionAnalisis.objects.create(intento=intento, decision='CONFIRMADO', motivo='', autor=self.cocina, version=1)
        return servicio, intento

    def test_historico_lee_orm_y_actualiza_exclusiones_tras_rechazo(self):
        for valor in (0,10,30,60):
            servicio, intento = self.caso(valor)
        self.client.force_login(self.admin)
        filtros = dict(plato='seco_de_pollo', componente='arroz', desde='2026-10-01', hasta='2026-10-07')
        response = self.client.get('/historico/', filtros)
        self.assertEqual(response.status_code, 200)
        datos = response.context['datos']
        self.assertFalse(datos['solo_pruebas'])
        self.assertEqual(datos['indicadores']['n'], 4)
        self.assertEqual(datos['indicadores']['intensidad'], Decimal(25))
        self.assertEqual(datos['indicadores']['prevalencia'], Decimal(50))
        self.assertContains(response, '0,00 %')
        RevisionAnalisis.objects.filter(intento=intento).update(vigente=False)
        RevisionAnalisis.objects.create(intento=intento, decision='RECHAZADO', motivo='Revisión posterior de prueba', autor=self.cocina, version=2)
        response = self.client.get('/historico/', filtros)
        self.assertEqual(response.context['datos']['resumen']['excluidos'], 1)
        self.assertEqual(response.context['datos']['indicadores']['n'], 3)
        self.assertContains(response, 'RECHAZADO')

    def test_presentacion_agrupa_componentes_sin_cambiar_filas_ni_totales(self):
        servicio, _ = self.caso(0)
        self.client.force_login(self.admin)
        respuesta = self.client.get('/historico/')
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.context['datos']
        presentados = list(respuesta.context['servicios_presentados'])
        self.assertEqual(len(presentados), 1)
        self.assertEqual(presentados[0]['identidad']['servicio_id'], str(servicio.pk))
        self.assertEqual(presentados[0]['componentes'], datos['filas'])
        self.assertEqual(datos['paginacion']['total_filas'], len(datos['filas']))
        self.assertContains(respuesta, '0,00 % de sobrante visual')

    def test_percepcion_guarda_reenvia_y_rechaza_version_obsoleta(self):
        from .models import PercepcionServicio
        servicio, _ = self.caso(25)
        url = f'/historico/servicios/{servicio.pk}/percepcion/'
        self.client.force_login(self.registro)
        self.assertContains(self.client.get(url), 'Sin respuesta registrada')
        datos = dict(categoria='ADECUADA', motivo='Declaración de prueba', version_esperada=0)
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.assertEqual(PercepcionServicio.objects.count(), 1)
        response = self.client.post(url, dict(categoria='EXCESIVA', motivo='Propuesta obsoleta', version_esperada=0))
        self.assertContains(response, 'Propuesta obsoleta', status_code=409)
        self.assertContains(response, 'Versión 1', status_code=409)
        self.assertEqual(PercepcionServicio.objects.get().categoria, 'ADECUADA')
        self.assertEqual(self.client.post(url, dict(categoria='EXCESIVA', motivo='', version_esperada=1)).status_code, 302)
        self.assertEqual(PercepcionServicio.objects.count(), 2)
        self.assertEqual(PercepcionServicio.objects.get(vigente=True).version, 2)

    def test_comparacion_informa_contexto_ausente_sin_fabricar_diferencias(self):
        self.caso(25, dia=3)
        self.caso(10, dia=10)
        self.client.force_login(self.admin)
        response = self.client.get('/historico/comparar/', dict(plato='seco_de_pollo', componente='arroz', referencia_desde='2026-10-01', referencia_hasta='2026-10-07', comparado_desde='2026-10-08', comparado_hasta='2026-10-14'))
        self.assertEqual(response.status_code, 200)
        datos = response.context['comparacion']
        self.assertFalse(datos['comparable'])
        self.assertIn('SIN_CONTEXTO_HISTORICO', datos['motivos'])
        self.assertIsNone(datos['diferencias']['intensidad_pp'])
        self.assertContains(response, 'Periodos no comparables')
        self.assertFalse(datos['referencia']['solo_pruebas'])
