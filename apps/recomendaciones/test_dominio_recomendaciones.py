"""Dominio con ORM real; el contexto hipotético solo se habilita en tests positivos."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.test import TransactionTestCase, override_settings

from apps.analisis.models import RevisionAnalisis, IntentoAnalisis
from apps.historico.test_dominio_historico import BaseHistorico
from apps.historico import indicadores
from . import services, contracts as c, models as m, selectors
from .serialization import guardar, cargar

CONFIG = dict(version='fixture-v1', aprobada=True, reglas=dict(muestra_minima=1,
    periodos_minimos=1, periodo_dias=1, presencia_t=20, cobertura_minima=80,
    calidad='REVISION_CONFIRMADA', confianza='0.7', comparabilidad='CONTEXTO_Y_GRUPO',
    categorias=[dict(categoria='PRUEBA_CONTROLADA', intensidad_desde=0, intensidad_hasta=100,
                     prevalencia_desde=0, prevalencia_hasta=100)]))
PRESENCIA = dict(version='fixture-t20', aprobada=True, presencia_t=20)


@override_settings(EVA_HISTORICO_CRITERIOS=PRESENCIA)
class DominioRecomendacionesTests(BaseHistorico):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = get_user_model().objects.create_user('admin_b7_fixture')
        cls.admin.groups.add(Group.objects.get(name='Administración'))
        cls.otro = get_user_model().objects.create_user('otro_admin_b7_fixture')
        cls.otro.groups.add(Group.objects.get(name='Administración'))

    def filtros(self, **extra):
        return services.normalizar_periodo_evaluacion(dict(plato='seco_de_pollo', componente='arroz',
            desde='2026-10-01', hasta='2026-10-07', **extra))

    def contexto(self):
        original = indicadores.resumir
        def conocido(*args, **kwargs):
            dto = original(*args, **kwargs)
            for grupo in dto['grupos']:
                grupo.update(comparable=True, contexto_clave='contexto-hipotetico-test', motivos=[])
            return dto
        return patch('apps.recomendaciones.selectors.indicadores.resumir', side_effect=conocido)

    def evaluar(self, version=None):
        return services.evaluar_evidencia(self.filtros(), version, self.admin)

    def recomendacion(self):
        caso = self.evaluar('fixture-v1')
        return services.generar_recomendacion(caso['evaluacion']['id'], self.admin)

    def aceptar(self):
        caso = self.recomendacion()
        return services.decidir_recomendacion(caso['recomendacion']['id'], 'ACEPTADA', 'Ensayo supervisado', self.admin, 0)

    def prueba(self):
        caso = self.aceptar()
        return services.registrar_prueba(caso['recomendacion']['id'], 'Cambio acotado', self.cocina.pk,
            dict(referencia_desde=date(2026,10,1), referencia_hasta=date(2026,10,7),
                 intervencion_desde=date(2026,10,8), intervencion_hasta=date(2026,10,14)), self.admin)

    def test_sin_configuracion_guarda_insuficiencia_idempotente_y_tipos(self):
        self.caso()
        primero = self.evaluar()
        segundo = self.evaluar()
        self.assertEqual(primero['evaluacion']['id'], segundo['evaluacion']['id'])
        self.assertEqual(m.EvaluacionEvidencia.objects.count(), 1)
        dto = services.obtener_evaluacion(primero['evaluacion']['id'], self.admin)
        self.assertEqual(set(dto), set(c.DetalleCaso.__annotations__))
        self.assertEqual(set(dto['evaluacion']), set(c.EvaluacionEvidencia.__annotations__))
        self.assertEqual(dto['evaluacion']['suficiencia'], 'INSUFICIENTE')
        self.assertIsInstance(dto['evaluacion']['indicadores']['intensidad'], Decimal)
        self.assertIsInstance(dto['evaluacion']['filtros']['desde'], date)
        self.assertFalse(dto['capacidades']['puede_generar'])
        with self.assertRaises(c.ConflictoRecomendacion):
            services.generar_recomendacion(dto['evaluacion']['id'], self.admin)
        self.assertEqual(m.Recomendacion.objects.count(), 0)

    def test_fuente_completa_supera_paginacion(self):
        for _ in range(32):
            self.caso()
        caso = self.evaluar()
        self.assertEqual(caso['evaluacion']['resumen']['aptos'], 32)
        self.assertEqual(len(caso['evaluacion']['referencias']), 32)
        self.assertEqual(caso['evaluacion']['indicadores']['n'], 32)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_contexto_ausente_no_se_inventa(self):
        self.caso()
        caso = self.evaluar('fixture-v1')
        self.assertEqual(caso['evaluacion']['suficiencia'], 'INSUFICIENTE')
        self.assertFalse(next(c for c in caso['evaluacion']['chequeos'] if c['codigo']=='COMPARABILIDAD')['cumple'])

    def test_sin_datos_no_ceros_y_get_no_escribe(self):
        caso = services.evaluar_evidencia(dict(desde='2026-10-01', hasta='2026-10-07'), None, self.admin)
        self.assertIsNone(caso['evaluacion']['indicadores']['intensidad'])
        servicios_antes = m.EvaluacionEvidencia.objects.count()
        services.obtener_evaluacion(caso['evaluacion']['id'], self.admin)
        services.consultar_recomendaciones({}, self.admin)
        self.assertEqual(m.EvaluacionEvidencia.objects.count(), servicios_antes)

    def test_roles_staff_inactivo_y_responsables(self):
        self.registro.is_staff = True
        self.registro.save()
        for u in (None, self.registro):
            with self.assertRaises(PermissionDenied):
                services.consultar_recomendaciones({}, u)
        with self.assertRaises(PermissionDenied):
            services.evaluar_evidencia(self.filtros(), None, self.cocina)
        ids = {r['id'] for r in services.opciones_recomendaciones(self.admin)['responsables']}
        self.assertIn(self.cocina.pk, ids)
        self.assertNotIn(self.registro.pk, ids)
        self.otro.is_active = False
        self.otro.save()
        with self.assertRaises(PermissionDenied):
            services.opciones_recomendaciones(self.otro)

    def test_version_desconocida_y_uuid_invalido(self):
        with self.assertRaises(c.ParametrosInvalidos):
            self.evaluar('inventada')
        with self.assertRaises(c.CasoNoDisponible):
            services.obtener_evaluacion('invalido', self.admin)
        self.assertEqual(m.EvaluacionEvidencia.objects.count(), 0)

    def test_revision_rechazada_o_intento_nuevo_obsoleta(self):
        _, _, intento = self.caso()
        caso = self.evaluar()
        RevisionAnalisis.objects.filter(intento=intento, vigente=True).update(decision='RECHAZADO')
        viejo = services.obtener_evaluacion(caso['evaluacion']['id'], self.admin)
        self.assertFalse(viejo['evaluacion']['vigente'])
        self.assertEqual(viejo['evaluacion']['resumen']['aptos'], 1)
        with self.assertRaises(c.EvidenciaDesactualizada):
            services.generar_recomendacion(caso['evaluacion']['id'], self.admin)
        nuevo = self.evaluar()
        self.assertNotEqual(nuevo['evaluacion']['id'], caso['evaluacion']['id'])
        self.assertEqual(nuevo['evaluacion']['resumen']['aptos'], 0)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_flujo_positivo_auditado_sin_tocar_catalogo(self):
        self.caso()
        with self.contexto():
            caso = self.recomendacion()
            self.assertEqual(caso['evaluacion']['suficiencia'], 'SUFICIENTE')
            rid = caso['recomendacion']['id']
            self.assertEqual(services.generar_recomendacion(caso['evaluacion']['id'], self.admin)['recomendacion']['id'], rid)
            primero = services.decidir_recomendacion(rid, 'ACEPTADA', 'Ensayo supervisado', self.admin, 0)
            segundo = services.decidir_recomendacion(rid, 'ACEPTADA', 'Ensayo supervisado', self.admin, 0)
            self.assertEqual(primero['decision_actual']['id'], segundo['decision_actual']['id'])
            self.assertEqual(primero['version_esperada'], 1)
            with self.assertRaises(c.ConflictoRecomendacion):
                services.decidir_recomendacion(rid, 'DESCARTADA', 'Otro criterio', self.otro, 0)
            ultimo = services.decidir_recomendacion(rid, 'EN_OBSERVACION', 'Revisar mañana', self.otro, 1)
            self.assertEqual(ultimo['decision_actual']['sustituye_id'], primero['decision_actual']['id'])
            self.assertEqual(len(ultimo['historial_decisiones']), 2)
            self.assertEqual(ultimo['version_esperada'], 2)
            self.assertFalse(ultimo['capacidades']['puede_registrar_prueba'])
            with self.assertRaises(PermissionDenied):
                services.obtener_recomendacion(rid, self.cocina)
            with self.assertRaises(PermissionDenied):
                services.decidir_recomendacion(rid, 'ACEPTADA', 'Texto', self.cocina, 2)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_justificacion_invalida_sin_escritura(self):
        self.caso()
        with self.contexto():
            r = self.recomendacion()['recomendacion']['id']
            for texto in ('', ' ', 'x'*1001):
                with self.assertRaises(c.ParametrosInvalidos):
                    services.decidir_recomendacion(r, 'ACEPTADA', texto, self.admin, 0)
            self.assertEqual(m.DecisionRecomendacion.objects.count(), 0)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_prueba_idempotente_no_evaluable_y_reevaluacion_versionada(self):
        self.caso()
        with self.contexto():
            p = self.prueba()
            otro = self.prueba()
            self.assertEqual(p['prueba']['id'], otro['prueba']['id'])
            self.assertIsNone(p['prueba']['comparacion'])
            evaluada = services.evaluar_prueba(p['prueba']['id'], self.admin, 0)
            self.assertEqual(evaluada['prueba']['estado'], 'NO_EVALUABLE')
            self.assertIsNone(evaluada['prueba']['comparacion']['diferencias']['intensidad_pp'])
            self.assertEqual(set(evaluada['prueba']), set(c.PruebaControlada.__annotations__))
            with self.assertRaises(c.ConflictoRecomendacion):
                services.evaluar_prueba(p['prueba']['id'], self.admin, 0)
            services.evaluar_prueba(p['prueba']['id'], self.admin, 1)
            self.assertEqual(m.EvaluacionPrueba.objects.count(), 2)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_aceptacion_sustituida_bloquea_prueba(self):
        self.caso()
        with self.contexto():
            p = self.prueba()
            rid = p['caso']['recomendacion']['id']
            services.decidir_recomendacion(rid, 'DESCARTADA', 'Ensayo cancelado', self.admin, 1)
            with self.assertRaises(c.ConflictoRecomendacion):
                services.evaluar_prueba(p['prueba']['id'], self.admin, 0)
            self.assertFalse(services.obtener_prueba(p['prueba']['id'], self.admin)['prueba']['puede_evaluar'])

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_responsable_y_periodos_se_validan_en_dominio(self):
        self.caso()
        with self.contexto():
            rid = self.aceptar()['recomendacion']['id']
            periodos = dict(referencia_desde=date(2026,10,1), referencia_hasta=date(2026,10,7),
                           intervencion_desde=date(2026,10,8), intervencion_hasta=date(2026,10,14))
            with self.assertRaises(c.ParametrosInvalidos):
                services.registrar_prueba(rid, 'Texto', self.registro.pk, periodos, self.admin)
            periodos['intervencion_desde'] = date(2026,10,7)
            with self.assertRaises(c.ParametrosInvalidos):
                services.registrar_prueba(rid, 'Texto', self.cocina.pk, periodos, self.admin)
            self.assertEqual(m.PruebaControlada.objects.count(), 0)

    def test_lista_filtra_y_cuenta_evaluaciones_no_servicios(self):
        self.caso()
        self.evaluar()
        lista = services.consultar_recomendaciones(services.normalizar_filtros(dict(suficiencia='INSUFICIENTE')), self.admin)
        self.assertEqual(set(lista), set(c.ListaRecomendaciones.__annotations__))
        self.assertEqual(lista['resumen']['total'], 1)
        self.assertEqual(lista['resumen']['sin_decision'], 0)
        self.assertEqual(len(lista['filas']), 1)
        self.assertEqual(services.consultar_recomendaciones(dict(suficiencia='SUFICIENTE'), self.admin)['filas'], [])

    def test_configuracion_cambia_vigencia(self):
        self.caso()
        eid = self.evaluar()['evaluacion']['id']
        with override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG):
            self.assertFalse(services.obtener_evaluacion(eid, self.admin)['evaluacion']['vigente'])

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_nuevo_intento_bloquea_decision_sin_borrar_snapshot(self):
        _, analisis, _ = self.caso()
        with self.contexto():
            caso = self.recomendacion()
            IntentoAnalisis.objects.create(analisis=analisis, numero=2, estado='PENDIENTE')
            with self.assertRaises(c.EvidenciaDesactualizada):
                services.decidir_recomendacion(caso['recomendacion']['id'], 'ACEPTADA', 'Texto', self.admin, 0)
            self.assertEqual(m.DecisionRecomendacion.objects.count(), 0)
            self.assertEqual(len(services.obtener_evaluacion(caso['evaluacion']['id'], self.admin)['evaluacion']['referencias']), 1)

    def test_reglas_malformadas_no_aprueban_evidencia(self):
        self.caso()
        for campo, valor in [('muestra_minima', True), ('confianza', 'NaN'), ('confianza', float('nan')),
                             ('categorias', [{}]), ('categorias', [dict(categoria=[])]), ('periodo_dias', 0)]:
            config = deepcopy(CONFIG)
            config['reglas'][campo] = valor
            with override_settings(EVA_RECOMENDACIONES_CRITERIOS=config), self.contexto():
                self.assertEqual(self.evaluar('fixture-v1')['evaluacion']['suficiencia'], 'INSUFICIENTE')

    def test_json_preserva_cero_y_none(self):
        datos = dict(porcentaje=Decimal('0'), ausente=None, fecha=date(2026,10,3))
        self.assertEqual(cargar(guardar(datos)), datos)

    @override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG)
    def test_comparacion_con_contexto_hipotetico_y_datos_orm(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        self.caso(40)
        self.caso(20, fecha=datetime(2026,10,10,12,tzinfo=ZoneInfo('America/Guayaquil')))
        with self.contexto():
            p = self.prueba()
            evaluada = services.evaluar_prueba(p['prueba']['id'], self.admin, 0)
            self.assertEqual(evaluada['prueba']['estado'], 'EVALUADA')
            self.assertEqual(evaluada['prueba']['comparacion']['diferencias']['intensidad_pp'], Decimal('-20'))
            self.assertEqual(m.EvaluacionPrueba.objects.get().autor, self.admin)

class ConcurrenciaDecisionTests(TransactionTestCase):
    def test_dos_decisiones_simultaneas_no_pisan_el_historial(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        # Fixtures ORM de los bloques previos; no se conectan motor ni S3.
        BaseHistorico.setUpTestData.__func__(type(self))
        admin = get_user_model().objects.create_user('admin_concurrente_b7')
        admin.groups.add(Group.objects.get(name='Administración'))
        self.cocina = type(self).cocina
        self.registro = type(self).registro
        BaseHistorico.caso(self)
        filtros = dict(plato='seco_de_pollo', componente='arroz', desde='2026-10-01', hasta='2026-10-07')
        with override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG, EVA_HISTORICO_CRITERIOS=PRESENCIA), DominioRecomendacionesTests.contexto(self):
            evaluacion = services.evaluar_evidencia(filtros, 'fixture-v1', admin)
            rid = services.generar_recomendacion(evaluacion['evaluacion']['id'], admin)['recomendacion']['id']
            original = services._vigente
            barrera = Barrier(2, timeout=15)
            def sincronizado(e):
                resultado = original(e)
                barrera.wait()
                return resultado
            def decidir(texto):
                close_old_connections()
                try:
                    u = get_user_model().objects.get(pk=admin.pk)
                    services.decidir_recomendacion(rid, 'ACEPTADA', texto, u, 0)
                    return 'guardado'
                except c.ConflictoRecomendacion:
                    return 'conflicto'
                finally:
                    close_old_connections()
            with patch('apps.recomendaciones.services._vigente', side_effect=sincronizado):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    resultados = list(pool.map(decidir, ['Justificación uno', 'Justificación dos']))
        self.assertIn('conflicto', resultados)
        guardados = resultados.count('guardado')
        self.assertLessEqual(guardados, 1)
        self.assertEqual(m.DecisionRecomendacion.objects.count(), guardados)
        self.assertEqual(m.Recomendacion.objects.get(pk=rid).version, guardados)
        # SQLite puede rechazar ambas promociones de lectura a escritura. Tras
        # refrescar, una nueva acción explícita debe poder guardarse normalmente.
        if not guardados:
            with override_settings(EVA_RECOMENDACIONES_CRITERIOS=CONFIG, EVA_HISTORICO_CRITERIOS=PRESENCIA), DominioRecomendacionesTests.contexto(self):
                services.decidir_recomendacion(rid, 'ACEPTADA', 'Decisión tras refrescar', admin, 0)
            self.assertEqual(m.DecisionRecomendacion.objects.count(), 1)
