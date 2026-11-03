from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.apps import apps
from django.test import SimpleTestCase

from . import contracts, services
from .filtros import normalizar_filtros
from .testing.fixtures import comparacion_fixture, historico_fixture, opciones_fixture, percepcion_fixture


class FiltrosTests(SimpleTestCase):
    def test_limites_inclusivos_de_fecha_se_convierten_a_fin_exclusivo_local(self):
        filtro = normalizar_filtros({'desde': '2026-11-03', 'hasta': '2026-11-03'})
        self.assertEqual(filtro['inicio'].hour, 0)
        self.assertEqual(filtro['fin'].date(), date(2026, 11, 4))
        self.assertEqual(filtro['inicio'].utcoffset(), timedelta(hours=-5))
        self.assertEqual(filtro['fin'] - filtro['inicio'], timedelta(days=1))
        self.assertEqual(filtro['origen'], 'REAL')

    def test_acepta_valores_limpiados_por_formulario(self):
        filtro = normalizar_filtros(dict(desde=date(2026, 11, 3), hora_desde=time(12), hora_hasta=time(14), plato='seco_de_pollo'))
        self.assertEqual(filtro['hora_desde'], time(12))
        self.assertEqual(filtro['plato'], 'seco_de_pollo')

    def test_errores_por_campo_y_sin_conversion_silenciosa(self):
        casos = [({'desde': '2026-02-30'}, 'desde'), ({'hasta': '9999-12-31'}, 'hasta'),
                 ({'desde': '2026-11-04', 'hasta': '2026-11-03'}, 'hasta'),
                 ({'hora_desde': '20:00', 'hora_hasta': '08:00'}, 'hora_hasta'),
                 ({'hora_desde': '08:00'}, 'hora_hasta'), ({'hora_desde': '24:00'}, 'hora_desde'),
                 ({'plato': '../../archivo'}, 'plato'), ({'porcion': 1}, 'porcion'),
                 ({'desde': datetime(2026, 11, 3)}, 'desde'), ({'origen': 'SIMULADO'}, 'origen')]
        for datos, campo in casos:
            with self.subTest(datos=datos), self.assertRaises(contracts.FiltrosInvalidos) as exc:
                normalizar_filtros(datos)
            self.assertIn(campo, exc.exception.errores)


class ContratoFixturesTests(SimpleTestCase):
    def test_esqueleto_registrado_sin_dependencias_nuevas(self):
        self.assertEqual(apps.get_app_config('historico').name, 'apps.historico')
        self.assertEqual(contracts.CONTRACT_VERSION, 1)

    def test_fixtures_respetan_dto_y_ejemplo_manual_de_indicadores(self):
        datos = historico_fixture()
        self.assertEqual(set(datos), set(contracts.ResumenHistorico.__annotations__))
        self.assertEqual(set(datos['filas'][0]), set(contracts.FilaHistorico.__annotations__))
        self.assertEqual(set(datos['grupos'][0]), set(contracts.GrupoHistorico.__annotations__))
        aptos = [f['porcentaje_visual'] for f in datos['filas'] if f['estado'] == 'APTO']
        self.assertEqual(sum(aptos) / len(aptos), datos['indicadores']['intensidad'])
        prevalencia = Decimal(100) * sum(p > datos['indicadores']['t'] for p in aptos) / len(aptos)
        self.assertEqual(prevalencia, datos['indicadores']['prevalencia'])
        self.assertEqual(datos['resumen']['candidatos'], datos['resumen']['aptos'] + datos['resumen']['excluidos'])
        self.assertTrue(datos['solo_pruebas'])

    def test_no_confunde_falta_de_datos_con_cero(self):
        for escenario in ('sin_datos', 'sin_aptos'):
            datos = historico_fixture(escenario)
            self.assertIsNone(datos['indicadores']['prevalencia'])
            self.assertIsNone(datos['indicadores']['intensidad'])
        self.assertIsNone(historico_fixture('sin_datos')['resumen']['proporcion_excluidos'])
        self.assertEqual(historico_fixture()['filas'][0]['porcentaje_visual'], Decimal(0))

    def test_configuracion_pendiente_no_inventa_t(self):
        indicadores = historico_fixture('configuracion_pendiente')['indicadores']
        self.assertIsNone(indicadores['t'])
        self.assertIsNone(indicadores['prevalencia'])
        self.assertEqual(indicadores['intensidad'], Decimal(25))

    def test_comparacion_incompatible_no_inventa_diferencias(self):
        datos = comparacion_fixture(False)
        self.assertEqual(set(datos), set(contracts.Comparacion.__annotations__))
        self.assertFalse(datos['comparable'])
        self.assertIsNone(datos['diferencias']['intensidad_pp'])
        self.assertEqual(comparacion_fixture()['diferencias']['intensidad_pp'], Decimal(0))

    def test_no_informado_y_copias_independientes(self):
        self.assertEqual(percepcion_fixture()['categoria'], 'NO_INFORMADO')
        self.assertEqual(percepcion_fixture()['version'], 0)
        self.assertEqual(percepcion_fixture(True)['categoria'], 'ADECUADA')
        self.assertEqual(set(percepcion_fixture()), set(contracts.Percepcion.__annotations__))
        datos = historico_fixture()
        datos['indicadores']['n'] = 999
        self.assertEqual(historico_fixture()['indicadores']['n'], 4)
        self.assertEqual(set(opciones_fixture()), set(contracts.OpcionesHistorico.__annotations__))

    def test_servicios_sin_backend_nunca_devuelven_fixtures(self):
        filtro = normalizar_filtros({})
        llamadas = [(services.opciones_historico, ()), (services.consultar_historico, (filtro,)),
                    (services.comparar_periodos, (filtro, filtro)),
                    (services.obtener_percepcion, ('servicio', None)),
                    (services.registrar_percepcion, ('servicio', 'ADECUADA', '', None, 0))]
        for funcion, argumentos in llamadas:
            with self.subTest(funcion=funcion.__name__), self.assertRaises(contracts.BackendHistoricoNoDisponible):
                funcion(*argumentos)
