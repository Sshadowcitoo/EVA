"""Fixtures ORM sintéticas: prueban cálculos y selección, no precisión de IA."""
from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.analisis import services as analisis_services
from apps.analisis.models import AnalisisServicio, IntentoAnalisis, ResultadoComponente, RevisionAnalisis
from apps.captura.models import Servicio, FotografiaServicio
from apps.captura.protocolo import CRITERIOS, VERSION
from apps.catalogo.models import Plato, TipoPorcion, Componente
from . import services, indicadores
from .contracts import FiltrosInvalidos, ResumenHistorico
from .testing.fixtures import historico_fixture

ZONA = ZoneInfo('America/Guayaquil')


class BaseHistorico(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_catalogo_demo', verbosity=0)
        call_command('configurar_roles', stdout=StringIO())
        cls.cocina = get_user_model().objects.create_user('cocina_fixture')
        cls.cocina.groups.add(Group.objects.get(name='Cocina'))
        cls.registro = get_user_model().objects.create_user('registro_fixture')
        cls.registro.groups.add(Group.objects.get(name='Registro'))

    def caso(self, porcentaje=25, *, decision='CONFIRMADO', fecha=None, origen='REAL', modelo='fixture-m1', configuracion='fixture-c1'):
        servicio = Servicio.registrar(plato=Plato.objects.get(codigo='seco_de_pollo'),
            porcion=TipoPorcion.objects.get(codigo='estandar'), usuario=self.registro)
        Servicio.objects.filter(pk=servicio.pk).update(estado_captura='PAR_COMPLETO')
        servicio.refresh_from_db()
        fecha = fecha or datetime(2026, 10, 3, 12, tzinfo=ZONA)
        fotos = {}
        for etapa in ('SERVIDO', 'RETORNO'):
            f = FotografiaServicio.objects.create(servicio=servicio, etapa=etapa,
                clave_archivo=f'fixture/sin-bytes/{servicio.pk}/{etapa}.png', tipo_contenido='image/png',
                tamano_bytes=10, ancho=4, alto=4, autor=self.registro, protocolo_version=VERSION,
                checklist=dict.fromkeys(CRITERIOS, True))
            FotografiaServicio.objects.filter(pk=f.pk).update(fecha=fecha)
            f.refresh_from_db()
            fotos[etapa] = f
        a = AnalisisServicio.objects.create(servicio=servicio, foto_servido=fotos['SERVIDO'], foto_retorno=fotos['RETORNO'],
            version_modelo=modelo, version_configuracion=configuracion, origen=origen, solicitante=self.cocina)
        intento = IntentoAnalisis.objects.create(analisis=a, numero=1, estado='COMPLETADO')
        a.intento_vigente = intento
        a.save(update_fields=['intento_vigente'])
        for comp in servicio.composicion.all():
            ResultadoComponente.objects.create(intento=intento, servicio_componente=comp,
                area_inicial=100, area_residual=porcentaje, porcentaje=Decimal(porcentaje), confianza=.9,
                umbral_aplicado=.7, configuracion_aprobada=True, criterio=configuracion,
                estado='CONCLUYENTE', motivo='')
        if decision:
            RevisionAnalisis.objects.create(intento=intento, decision=decision,
                motivo='Fixture' if decision != 'CONFIRMADO' else '', autor=self.cocina, version=1)
        return servicio, a, intento

    def consulta(self, **filtros):
        return services.consultar_historico(services.normalizar_filtros(dict(plato='seco_de_pollo', componente='arroz', **filtros)))


@override_settings(EVA_HISTORICO_CRITERIOS=dict(version='fixture-t20', aprobada=True, presencia_t=20))
class SeleccionCalculoTests(BaseHistorico):
    def test_formulas_ceros_muestra_y_exclusion_sin_leer_archivos(self):
        for p in (0, 10, 30, 60):
            self.caso(p)
        self.caso(80, decision='RECHAZADO')
        with patch('apps.captura.storage.abrir', side_effect=AssertionError('No leer archivos en histórico')):
            datos = self.consulta()
        self.assertEqual(set(datos), set(ResumenHistorico.__annotations__))
        self.assertEqual(datos['indicadores']['n'], 4)
        self.assertEqual(datos['indicadores']['prevalencia'], Decimal(50))
        self.assertEqual(datos['indicadores']['intensidad'], Decimal(25))
        self.assertEqual(datos['resumen'], dict(candidatos=5, aptos=4, excluidos=1,
            proporcion_excluidos=Decimal(20), motivos={'RECHAZADO': 1}))
        self.assertFalse(datos['solo_pruebas'])

    def test_limite_de_presencia_es_estrictamente_mayor(self):
        self.caso(20)
        self.caso(21)
        datos = self.consulta()
        self.assertEqual(datos['indicadores']['prevalencia'], Decimal(50))
        self.assertEqual(datos['indicadores']['intensidad'], Decimal('20.5'))

    def test_sin_aprobacion_o_valor_valido_no_inventa_t(self):
        self.caso(25)
        for config in ({}, dict(version='x', aprobada=False, presencia_t=20),
                       dict(version='x', aprobada=True, presencia_t=True),
                       dict(version='x', aprobada=True, presencia_t='NaN'),
                       dict(version='x', aprobada=True, presencia_t=-1),
                       dict(version='', aprobada=True, presencia_t=20)):
            with self.subTest(config=config), override_settings(EVA_HISTORICO_CRITERIOS=config):
                indicador = self.consulta()['indicadores']
                self.assertIsNone(indicador['t'])
                self.assertIsNone(indicador['prevalencia'])
                self.assertEqual(indicador['intensidad'], Decimal(25))

    def test_componentes_no_duplican_servicios_ni_se_promedian_juntos(self):
        self.caso(25)
        self.caso(80, decision='RECHAZADO')
        datos = services.consultar_historico(services.normalizar_filtros({}))
        self.assertEqual(datos['resumen']['candidatos'], 2)
        self.assertEqual(datos['resumen']['excluidos'], 1)
        self.assertEqual(len(datos['filas']), 6)
        self.assertEqual(len(datos['grupos']), 3)
        self.assertEqual(datos['indicadores']['motivos_no_disponible'], ['MULTIPLES_GRUPOS'])
        self.assertIsNone(datos['indicadores']['intensidad'])
        self.assertTrue(all(g['indicadores']['n'] == 1 for g in datos['grupos']))

    def test_catalogo_editado_no_cambia_registros_y_opciones_historicas(self):
        servicio, _, _ = self.caso()
        Plato.objects.filter(pk=servicio.plato_catalogo_id).update(nombre='Nombre nuevo', activo=False)
        Componente.objects.filter(codigo='arroz').update(nombre='Arroz cambiado', activo=False)
        datos = self.consulta()
        self.assertEqual(datos['filas'][0]['plato_nombre'], 'Seco de pollo')
        self.assertEqual(datos['filas'][0]['componente_nombre'], 'Arroz')
        self.assertIn(dict(codigo='seco_de_pollo', nombre='Seco de pollo'), services.opciones_historico()['platos'])

    def test_filtros_codigos_desconocidos_o_incompatibles(self):
        self.caso()
        Servicio.registrar(plato=Plato.objects.get(codigo='encebollado'),
            porcion=TipoPorcion.objects.get(codigo='estandar'), usuario=self.registro)
        for cambios in [dict(plato='no_existe'), dict(componente='pescado', plato='seco_de_pollo')]:
            with self.subTest(cambios=cambios), self.assertRaises(FiltrosInvalidos):
                services.consultar_historico(services.normalizar_filtros(cambios))

    def test_otro_modelo_o_configuracion_no_se_mezcla(self):
        self.caso(modelo='m1')
        self.caso(modelo='m2')
        datos = self.consulta()
        self.assertEqual(len(datos['grupos']), 2)
        self.assertEqual(datos['resumen']['aptos'], 2)
        self.assertIsNone(datos['indicadores']['prevalencia'])

    def test_paginacion_no_recorta_los_indicadores(self):
        for i in range(11):
            self.caso(i)
        filtro = services.normalizar_filtros({})
        a = services.consultar_historico(filtro)
        b = services.consultar_historico(filtro, pagina=2)
        self.assertEqual(a['paginacion']['total_filas'], 33)
        self.assertEqual(len(a['filas']), 30)
        self.assertEqual(len(b['filas']), 3)
        self.assertEqual(a['resumen'], b['resumen'])
        self.assertEqual(a['grupos'], b['grupos'])
        for pagina in (0, -1, True, '2'):
            with self.assertRaises(FiltrosInvalidos):
                services.consultar_historico(filtro, pagina)

    def test_numero_de_consultas_no_crece_por_servicio(self):
        self.caso()
        with CaptureQueriesContext(connection) as primera:
            self.consulta()
        for _ in range(6):
            self.caso()
        with CaptureQueriesContext(connection) as segunda:
            self.consulta()
        self.assertEqual(len(primera), len(segunda))


class VigenciaTests(BaseHistorico):
    def test_rechazo_posterior_se_refleja_sin_borrar_resultado(self):
        _, _, intento = self.caso()
        self.assertEqual(self.consulta()['resumen']['aptos'], 1)
        analisis_services.revisar_resultado(intento, 'RECHAZADO', 'Corrección de fixture', self.cocina, 1)
        self.assertEqual(self.consulta()['resumen']['motivos'], {'RECHAZADO': 1})
        self.assertEqual(intento.resultados.count(), 3)

    def test_intento_nuevo_no_hereda_aprobacion(self):
        servicio, a, _ = self.caso()
        IntentoAnalisis.objects.create(analisis=a, numero=2, estado='PENDIENTE')
        self.assertEqual(self.consulta()['resumen']['motivos'], {'INTENTO_NO_COMPLETADO': 1})
        nuevo = AnalisisServicio.objects.create(servicio=servicio, foto_servido=a.foto_servido,
            foto_retorno=a.foto_retorno, version_modelo='m2', version_configuracion='c2', origen='REAL', solicitante=self.cocina)
        self.assertEqual(self.consulta()['resumen']['aptos'], 0)
        self.assertNotEqual(nuevo.pk, a.pk)

    def test_ultimo_simulado_no_reutiliza_resultados_reales_anteriores(self):
        servicio, a, _ = self.caso()
        AnalisisServicio.objects.create(servicio=servicio, foto_servido=a.foto_servido, foto_retorno=a.foto_retorno,
            version_modelo='fixture-simulado', version_configuracion='c1', origen='SIMULADO', solicitante=self.cocina)
        self.assertEqual(self.consulta()['resumen']['candidatos'], 0)

    def test_falta_componente_no_habilita_indicador_parcial(self):
        _, _, intento = self.caso()
        intento.resultados.filter(servicio_componente__componente_codigo='pollo').delete()
        datos = self.consulta()
        self.assertEqual(datos['resumen']['motivos'], {'COMPONENTES_INVALIDOS': 1})
        self.assertIsNone(datos['indicadores']['intensidad'])

    def test_protocolo_o_numero_invalido_no_superan_aprobacion(self):
        _, a, intento = self.caso()
        resultado = intento.resultados.get(servicio_componente__componente_codigo='arroz')
        for cambios in [dict(confianza=.2), dict(porcentaje=120), dict(configuracion_aprobada=False)]:
            original = {campo: getattr(resultado, campo) for campo in cambios}
            ResultadoComponente.objects.filter(pk=resultado.pk).update(**cambios)
            self.assertEqual(self.consulta()['resumen']['aptos'], 0)
            ResultadoComponente.objects.filter(pk=resultado.pk).update(**original)
        FotografiaServicio.objects.filter(pk=a.foto_servido_id).update(checklist={})
        self.assertEqual(self.consulta()['resumen']['motivos'], {'CRITERIOS_INVALIDOS': 1})

    def test_retencion_posterior_no_borra_historia_ni_usa_criterios_actuales(self):
        _, a, _ = self.caso()
        FotografiaServicio.objects.filter(pk__in=[a.foto_servido_id, a.foto_retorno_id]).update(
            fecha=timezone.now() - timedelta(days=91), eliminada_en=timezone.now())
        with override_settings(EVA_ANALISIS_CRITERIOS=dict(aprobada=False, umbrales={})), patch(
                'apps.captura.storage.abrir', side_effect=AssertionError('No necesita bytes')):
            self.assertEqual(self.consulta()['resumen']['aptos'], 1)

    def test_anulado_tiene_prioridad_y_sin_revision_queda_fuera(self):
        servicio, _, _ = self.caso(decision=None)
        self.assertEqual(self.consulta()['resumen']['motivos'], {'SIN_REVISION': 1})
        Servicio.objects.filter(pk=servicio.pk).update(estado_captura='ANULADO')
        self.assertEqual(self.consulta()['resumen']['motivos'], {'ANULADO': 1})


class TiempoComparacionTests(BaseHistorico):
    def test_fecha_hora_local_y_limite_exclusivo(self):
        self.caso(fecha=datetime(2026, 10, 3, 11, 59, tzinfo=ZONA))
        self.caso(fecha=datetime(2026, 10, 3, 12, 0, tzinfo=ZONA))
        self.caso(fecha=datetime(2026, 10, 3, 13, 0, tzinfo=ZONA))
        self.caso(fecha=datetime(2026, 10, 4, 12, 0, tzinfo=ZONA))
        datos = self.consulta(desde='2026-10-03', hasta='2026-10-03', hora_desde='12:00', hora_hasta='13:00')
        self.assertEqual(datos['resumen']['candidatos'], 1)
        self.assertEqual(datos['filas'][0]['fecha_servido'].hour, 12)

    def test_sin_fecha_no_se_asigna_a_un_periodo(self):
        Servicio.registrar(plato=Plato.objects.get(codigo='seco_de_pollo'),
            porcion=TipoPorcion.objects.get(codigo='estandar'), usuario=self.registro)
        self.assertEqual(self.consulta()['resumen']['motivos'], {'SIN_FECHA_SERVIDO': 1})
        datos = self.consulta(desde='2026-10-01', hasta='2026-10-31')
        self.assertEqual(datos['resumen']['candidatos'], 0)
        self.assertTrue(datos['advertencias'])

    def test_comparacion_no_inventa_contexto_historico(self):
        self.caso(fecha=datetime(2026, 10, 3, 12, tzinfo=ZONA))
        self.caso(fecha=datetime(2026, 10, 10, 12, tzinfo=ZONA))
        a = services.normalizar_filtros(dict(componente='arroz', desde='2026-10-01', hasta='2026-10-07'))
        b = services.normalizar_filtros(dict(componente='arroz', desde='2026-10-08', hasta='2026-10-14'))
        resultado = services.comparar_periodos(a, b)
        self.assertFalse(resultado['comparable'])
        self.assertIn('SIN_CONTEXTO_HISTORICO', resultado['motivos'])
        self.assertIsNone(resultado['diferencias']['intensidad_pp'])

    def test_periodos_superpuestos_abiertos_o_filtros_distintos_se_rechazan(self):
        a = services.normalizar_filtros(dict(desde='2026-10-01', hasta='2026-10-07'))
        b = services.normalizar_filtros(dict(desde='2026-10-08', hasta='2026-10-14'))
        for otra in [a, services.normalizar_filtros({}), dict(b, componente='arroz')]:
            with self.assertRaises(FiltrosInvalidos):
                services.comparar_periodos(a, otra)

    def test_diferencias_en_puntos_y_cero_no_es_sin_datos(self):
        a, b = historico_fixture(), historico_fixture()
        b['indicadores'] = deepcopy(b['indicadores'])
        b['indicadores'].update(intensidad=Decimal(20), prevalencia=Decimal(25))
        resultado = indicadores.comparar_resumenes(a, b)
        self.assertTrue(resultado['comparable'])
        self.assertEqual(resultado['diferencias'], dict(prevalencia_pp=Decimal(-25), intensidad_pp=Decimal(-5)))
        b['indicadores']['t'] = None
        b['indicadores']['prevalencia'] = None
        resultado = indicadores.comparar_resumenes(a, b)
        self.assertIsNone(resultado['diferencias']['prevalencia_pp'])
        self.assertEqual(resultado['diferencias']['intensidad_pp'], Decimal(-5))
