from datetime import date
from django.apps import apps
from django.test import TestCase
from . import contracts as c, services
from .testing.fixtures import detalle_fixture, evaluacion_fixture, lista_fixture, prueba_fixture, opciones_fixture_recomendaciones


class ContratoBloque7Tests(TestCase):
    def test_app_y_dto_compartidos(self):
        self.assertEqual(apps.get_app_config('recomendaciones').name, 'apps.recomendaciones')
        self.assertEqual(set(detalle_fixture()), set(c.DetalleCaso.__annotations__))
        self.assertEqual(set(evaluacion_fixture()), set(c.EvaluacionEvidencia.__annotations__))
        self.assertEqual(set(prueba_fixture()['prueba']), set(c.PruebaControlada.__annotations__))
        self.assertEqual(set(lista_fixture()), set(c.ListaRecomendaciones.__annotations__))
        self.assertEqual(set(opciones_fixture_recomendaciones()), set(c.OpcionesRecomendaciones.__annotations__))

    def test_sin_evidencia_o_vigencia_no_propone_ajustes(self):
        for escenario in ('insuficiente','configuracion_pendiente','sin_datos','simulada'):
            datos = detalle_fixture(escenario)
            self.assertIsNone(datos['recomendacion'])
            self.assertFalse(datos['capacidades']['puede_generar'])
            self.assertTrue(datos['evaluacion']['solo_pruebas'])
        obsoleta = detalle_fixture('obsoleta')
        self.assertFalse(obsoleta['capacidades']['puede_decidir'])
        self.assertFalse(obsoleta['evaluacion']['vigente'])

    def test_decisiones_y_capacidades_separadas_de_cocina(self):
        for escenario in ('aceptada','descartada','en_observacion'):
            datos = detalle_fixture(escenario)
            self.assertEqual(datos['version_esperada'], 1)
            self.assertEqual(datos['capacidades']['puede_registrar_prueba'], escenario=='aceptada')
        self.assertFalse(detalle_fixture(administracion=False)['capacidades']['puede_decidir'])
        self.assertTrue(detalle_fixture(administracion=False)['capacidades']['puede_ver_analisis'])

    def test_prueba_no_evaluable_no_es_una_mejora_cero(self):
        datos = prueba_fixture()['prueba']
        self.assertIsNone(datos['comparacion']['diferencias']['intensidad_pp'])
        self.assertIsNone(prueba_fixture('REGISTRADA')['prueba']['comparacion'])
        self.assertEqual(prueba_fixture('EVALUADA')['prueba']['comparacion']['diferencias']['intensidad_pp'], 0)
        copia = detalle_fixture()
        copia['evaluacion']['motivos'].append('Cambio local')
        self.assertNotIn('Cambio local', detalle_fixture()['evaluacion']['motivos'])

    def test_filtros_y_periodo_definido(self):
        datos = services.normalizar_filtros(dict(categoria='MANTENER', decision='ACEPTADA'))
        self.assertEqual(datos['historico']['origen'], 'REAL')
        with self.assertRaises(c.ParametrosInvalidos):
            services.normalizar_filtros(dict(decision='CONFIRMADO'))
        with self.assertRaises(c.ParametrosInvalidos):
            services.normalizar_periodo_evaluacion({})
        with self.assertRaises(c.ParametrosInvalidos):
            services.normalizar_filtros(dict(origen='SIMULADO'))

    def test_justificacion_y_version_obligatorias(self):
        correcto = services.normalizar_decision(dict(decision='ACEPTADA', justificacion=' Prueba supervisada ', version_esperada='0'))
        self.assertEqual(correcto['version_esperada'], 0)
        self.assertEqual(correcto['justificacion'], 'Prueba supervisada')
        for cambios in ({'justificacion':''}, {'justificacion':'x'*1001}, {'version_esperada':True}, {'decision':'CONFIRMADO'}):
            datos = dict(decision='ACEPTADA', justificacion='Texto', version_esperada=0)
            datos.update(cambios)
            with self.assertRaises(c.ParametrosInvalidos):
                services.normalizar_decision(datos)

    def test_prueba_exige_responsable_y_periodos_no_superpuestos(self):
        datos = dict(cambio='Cambio de prueba', responsable_id='1', referencia_desde='2026-10-01',
                     referencia_hasta='2026-10-07', intervencion_desde='2026-10-08', intervencion_hasta='2026-10-14')
        limpio = services.normalizar_prueba(datos)
        self.assertEqual(limpio['responsable_id'], 1)
        self.assertEqual(limpio['periodos']['referencia_desde'], date(2026,10,1))
        for cambio in (dict(responsable_id=0), dict(intervencion_desde='2026-10-07'), dict(cambio=''), dict(referencia_desde='2026-02-30')):
            with self.assertRaises(c.ParametrosInvalidos):
                services.normalizar_prueba({**datos, **cambio})

    def test_operaciones_exigen_usuario_autorizado_antes_de_consultar(self):
        from django.core.exceptions import PermissionDenied
        llamadas = [(services.opciones_recomendaciones,(None,)), (services.consultar_recomendaciones,({},None)),
            (services.evaluar_evidencia,({},None,None)), (services.obtener_evaluacion,('id',None)),
            (services.generar_recomendacion,('id',None)), (services.obtener_recomendacion,('id',None)),
            (services.decidir_recomendacion,('id','ACEPTADA','Texto',None,0)),
            (services.registrar_prueba,('id','Cambio',1,{},None)), (services.obtener_prueba,('id',None)),
            (services.evaluar_prueba,('id',None,0))]
        for funcion, args in llamadas:
            with self.subTest(funcion=funcion.__name__), self.assertRaises(PermissionDenied):
                funcion(*args)
