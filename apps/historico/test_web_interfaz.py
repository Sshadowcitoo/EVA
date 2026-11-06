from decimal import Decimal
from unittest.mock import patch
from uuid import UUID
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import include, path
from .contracts import BackendHistoricoNoDisponible, ConflictoPercepcion, FiltrosInvalidos, ServicioNoDisponible
from .testing.fixtures import historico_fixture, opciones_fixture, comparacion_fixture, percepcion_fixture

urlpatterns = [path('historico/', include('apps.historico.urls')), path('', include('config.urls'))]
SID = '00000000-0000-4000-8000-000000000001'
PERCEPCION = f'/historico/servicios/{SID}/percepcion/'
PERIODOS = dict(referencia_desde='2026-10-01', referencia_hasta='2026-10-07', comparado_desde='2026-10-08', comparado_hasta='2026-10-14')


def _panel_fixture(datos):
    grupos = datos['grupos']
    return datos, {'opciones': grupos, 'grupo': grupos[0] if len(grupos) == 1 else None}


@override_settings(ROOT_URLCONF=__name__)
class HistoricoWebTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuarios = {}
        for rol in ('Registro', 'Cocina', 'Administración', 'Sin rol'):
            user = get_user_model().objects.create_user(username=rol)
            if rol != 'Sin rol':
                user.groups.add(Group.objects.get_or_create(name=rol)[0])
            cls.usuarios[rol] = user

    def setUp(self):
        self.client.force_login(self.usuarios['Cocina'])
        self.opciones = patch('apps.historico.services.opciones_historico', return_value=opciones_fixture()).start()
        self.addCleanup(patch.stopall)

    def registro(self):
        self.client.force_login(self.usuarios['Registro'])

    def test_permisos_roles_aislados_y_staff(self):
        for rol, user in self.usuarios.items():
            self.client.force_login(user)
            with patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(historico_fixture())), patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()):
                self.assertEqual(self.client.get('/historico/').status_code, 200 if rol in ('Cocina', 'Administración') else 403)
                self.assertEqual(self.client.get('/historico/comparar/').status_code, 200 if rol in ('Cocina', 'Administración') else 403)
                self.assertEqual(self.client.get(PERCEPCION).status_code, 200 if rol == 'Registro' else 403)
                self.assertEqual(self.client.post(PERCEPCION, {}).status_code, 400 if rol == 'Registro' else 403)
        user = self.usuarios['Sin rol']
        user.is_staff = True
        user.save()
        self.client.force_login(user)
        self.assertEqual(self.client.get('/historico/').status_code, 403)

    def test_anonimo_inactivo_y_superusuario(self):
        self.client.logout()
        self.assertEqual(self.client.get('/historico/').status_code, 302)
        user = self.usuarios['Cocina']
        user.is_active = False
        user.save()
        self.client.force_login(user)
        self.assertEqual(self.client.get('/historico/').status_code, 302)
        user.is_active = True
        user.is_superuser = True
        user.save()
        self.client.force_login(user)
        with patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()):
            self.assertEqual(self.client.get(PERCEPCION).status_code, 200)

    def test_roles_multiples_suman_accesos(self):
        user = self.usuarios['Registro']
        user.groups.add(Group.objects.get(name='Cocina'))
        self.client.force_login(user)
        with patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(historico_fixture())), patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()):
            self.assertEqual(self.client.get('/historico/').status_code, 200)
            self.assertEqual(self.client.get(PERCEPCION).status_code, 200)

    def test_metodos_no_escriben_por_get(self):
        self.assertEqual(self.client.post('/historico/').status_code, 405)
        self.assertEqual(self.client.post('/historico/comparar/').status_code, 405)
        self.registro()
        with patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()), patch('apps.historico.services.registrar_percepcion') as guardar:
            self.assertEqual(self.client.get(PERCEPCION).status_code, 200)
            guardar.assert_not_called()
            self.assertEqual(self.client.delete(PERCEPCION).status_code, 405)

    def test_estados_sin_datos_sin_aptos_y_configuracion(self):
        for escenario, texto in [('con_datos', '0,00 %'), ('sin_datos', 'Esto no significa cero sobrantes'), ('sin_aptos', 'No hay servicios aptos'), ('configuracion_pendiente', 'Pendiente de aprobación')]:
            with self.subTest(escenario=escenario), patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(historico_fixture(escenario))):
                response = self.client.get('/historico/')
                self.assertContains(response, texto)
                self.assertContains(response, 'Datos de prueba')
        with patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(historico_fixture('configuracion_pendiente'))):
            self.assertContains(self.client.get('/historico/'), '25,00 %')

    def test_backend_pendiente_no_se_convierte_en_vacio(self):
        self.opciones.side_effect = BackendHistoricoNoDisponible()
        for url in ('/historico/', '/historico/comparar/'):
            response = self.client.get(url)
            self.assertContains(response, 'pendiente de conexión', status_code=503)
            self.assertNotContains(response, 'Datos de prueba', status_code=503)
        self.registro()
        with patch('apps.historico.services.obtener_percepcion', side_effect=BackendHistoricoNoDisponible()), patch('apps.historico.services.registrar_percepcion') as guardar:
            self.assertEqual(self.client.post(PERCEPCION, dict(categoria='ADECUADA', version_esperada=0)).status_code, 503)
            guardar.assert_not_called()

    def test_filtros_invalidos_conservan_entrada(self):
        for datos in [dict(desde='2026-02-30'), dict(desde='2026-10-08', hasta='2026-10-01'), dict(hora_desde='23:00', hora_hasta='01:00'), dict(hora_desde='12:00'), dict(page='0'), dict(page='nada'), dict(plato='inexistente'), dict(origen='SIMULADO')]:
            with self.subTest(datos=datos), patch('apps.historico.services.consultar_panel') as consulta:
                response = self.client.get('/historico/', datos)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.context['form'].errors)
                consulta.assert_not_called()
        response = self.client.get('/historico/', dict(desde='2026-10-08', hasta='2026-10-01'))
        self.assertContains(response, 'value="2026-10-08"', status_code=400)

    def test_filtros_paginacion_y_totales_de_backend(self):
        datos = historico_fixture()
        datos['paginacion'].update(pagina=2, paginas=3, total_filas=75)
        with patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(datos)) as consulta:
            response = self.client.get('/historico/', dict(page=2, plato='seco_de_pollo', componente='arroz', porcion='estandar', desde='2026-10-01', hasta='2026-10-07', hora_desde='12:00', hora_hasta='14:00'))
            self.assertEqual(response.status_code, 200)
            filtro = consulta.call_args.args[0]
            self.assertEqual(filtro['inicio'].hour, 0)
            self.assertEqual(filtro['fin'].day, 8)
            self.assertEqual(consulta.call_args.kwargs, {'pagina': 2, 'grupo': ''})
            self.assertEqual(response.context['datos']['indicadores']['n'], 4)
            self.assertIn('plato=seco_de_pollo', response.context['enlaces']['siguiente'])
            self.assertIn('page=3', response.context['enlaces']['siguiente'])
            self.assertContains(response, 'Página 2 de 3')

    def test_varios_grupos_sin_promedio_inventado(self):
        datos = historico_fixture()
        datos['grupos'].append({**datos['grupos'][0], 'componente_codigo': 'pollo'})
        datos['indicadores'].update(n=0, intensidad=None, prevalencia=None, motivos_no_disponible=['MULTIPLES_GRUPOS'])
        with patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(datos)):
            response = self.client.get('/historico/')
            self.assertContains(response, 'Hay varios grupos: no se combinan sus medias.')
            self.assertContains(response, 'n = 4', count=2)

    def test_campos_escapados_y_fechas_de_ecuador(self):
        datos = historico_fixture()
        datos['filas'][0]['plato_nombre'] = '<script>alert(1)</script>'
        with patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(datos)):
            response = self.client.get('/historico/')
            self.assertContains(response, '&lt;script&gt;')
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertContains(response, '01/10/2026 12:00')

    def test_error_servicio_validacion_y_excepcion_inesperada(self):
        for exc in [FiltrosInvalidos({'desde': 'Fecha rechazada'}), ValidationError({'plato': '<error>'})]:
            with patch('apps.historico.services.consultar_panel', side_effect=exc):
                self.assertEqual(self.client.get('/historico/').status_code, 400)
        with patch('apps.historico.services.consultar_panel', side_effect=BackendHistoricoNoDisponible()):
            self.assertEqual(self.client.get('/historico/').status_code, 503)
        with patch('apps.historico.services.consultar_panel', side_effect=PermissionDenied()):
            self.assertEqual(self.client.get('/historico/').status_code, 403)
        with patch('apps.historico.services.consultar_panel', side_effect=RuntimeError('fallo')):
            with self.assertRaises(RuntimeError):
                self.client.get('/historico/')

    def test_comparacion_inicial_valida_e_incompatible(self):
        self.assertEqual(self.client.get('/historico/comparar/').status_code, 200)
        for comparable in (True, False):
            with patch('apps.historico.services.comparar_periodos', return_value=comparacion_fixture(comparable)) as comparar:
                response = self.client.get('/historico/comparar/', PERIODOS)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(comparar.call_args.args[0]['desde'].day, 1)
                self.assertEqual(comparar.call_args.args[1]['desde'].day, 8)
                self.assertContains(response, '0,00 pp' if comparable else 'Periodos no comparables')

    def test_comparacion_rechaza_solapamiento_y_periodos_incompletos(self):
        for cambios in [dict(comparado_desde='2026-10-07'), dict(referencia_desde=''), dict(comparado_hasta='2026-10-01'), dict(hora_desde='22:00', hora_hasta='03:00')]:
            with patch('apps.historico.services.comparar_periodos') as comparar:
                self.assertEqual(self.client.get('/historico/comparar/', {**PERIODOS, **cambios}).status_code, 400)
                comparar.assert_not_called()

    def test_comparacion_errores_del_dominio(self):
        for exc, codigo in [(BackendHistoricoNoDisponible(), 503), (FiltrosInvalidos({'desde': 'Periodo rechazado'}), 400), (ValidationError('Datos incompatibles'), 400)]:
            with patch('apps.historico.services.comparar_periodos', side_effect=exc):
                self.assertEqual(self.client.get('/historico/comparar/', PERIODOS).status_code, codigo)

    def test_percepcion_consulta_ausencia_y_no_confirma_query_inventada(self):
        self.registro()
        with patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()):
            response = self.client.get(PERCEPCION+'?guardada=1')
            self.assertContains(response, 'Sin respuesta registrada')
            self.assertNotContains(response, 'Respuesta guardada correctamente')
            self.assertContains(response, 'datos personales')

    def test_percepcion_guardado_prg_usuario_y_servicio_no_manipulables(self):
        self.registro()
        with patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()), patch('apps.historico.services.registrar_percepcion', return_value=percepcion_fixture(True)) as guardar:
            response = self.client.post(PERCEPCION, dict(categoria='ADECUADA', motivo='Bien', version_esperada=0, usuario='otro', servicio_id='otro'))
            self.assertRedirects(response, PERCEPCION, fetch_redirect_response=False)
            guardar.assert_called_once_with(UUID(SID), 'ADECUADA', 'Bien', self.usuarios['Registro'], 0)
            self.assertContains(self.client.get(PERCEPCION), 'Respuesta guardada correctamente')

    def test_percepcion_categorias_ausencia_y_validaciones(self):
        self.registro()
        with patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()), patch('apps.historico.services.registrar_percepcion') as guardar:
            for categoria in ('INSUFICIENTE', 'ADECUADA', 'EXCESIVA', 'NO_INFORMADO', ''):
                self.assertEqual(self.client.post(PERCEPCION, dict(categoria=categoria, motivo='', version_esperada=0)).status_code, 302)
            for datos in [dict(categoria='OTRA', version_esperada=0), dict(categoria='ADECUADA', motivo='a'*1001, version_esperada=0), dict(categoria='NO_INFORMADO', motivo='texto', version_esperada=0), dict(categoria='ADECUADA', version_esperada=-1), dict(categoria='ADECUADA')]:
                guardar.reset_mock()
                self.assertEqual(self.client.post(PERCEPCION, datos).status_code, 400)
                guardar.assert_not_called()

    def test_conflicto_preserva_propuesta_y_actualiza_vigente_sin_reintentar(self):
        self.registro()
        vigente = percepcion_fixture(True)
        vigente['version'] = 2
        with patch('apps.historico.services.obtener_percepcion', side_effect=[percepcion_fixture(), vigente]), patch('apps.historico.services.registrar_percepcion', side_effect=ConflictoPercepcion()) as guardar:
            response = self.client.post(PERCEPCION, dict(categoria='EXCESIVA', motivo='<mi propuesta>', version_esperada=0))
            self.assertContains(response, 'Versión 2', status_code=409)
            self.assertContains(response, '&lt;mi propuesta&gt;', status_code=409)
            self.assertContains(response, 'data-bloqueado="true"', status_code=409)
            guardar.assert_called_once()

    def test_percepcion_servicio_no_disponible_y_error_guardado(self):
        self.registro()
        with patch('apps.historico.services.obtener_percepcion', side_effect=ServicioNoDisponible()):
            self.assertEqual(self.client.get(PERCEPCION).status_code, 404)
        for exc, codigo in [(ServicioNoDisponible(), 404), (ValidationError({'motivo': '<error>'}), 400), (BackendHistoricoNoDisponible(), 503)]:
            with patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()), patch('apps.historico.services.registrar_percepcion', side_effect=exc):
                self.assertEqual(self.client.post(PERCEPCION, dict(categoria='ADECUADA', version_esperada=0)).status_code, codigo)

    def test_csrf_efectivo_y_flujo_con_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuarios['Registro'])
        with patch('apps.historico.services.obtener_percepcion', return_value=percepcion_fixture()), patch('apps.historico.services.registrar_percepcion') as guardar:
            self.assertEqual(client.post(PERCEPCION, dict(categoria='ADECUADA', version_esperada=0)).status_code, 403)
            guardar.assert_not_called()
            client.get(PERCEPCION)
            token = client.cookies['csrftoken'].value
            self.assertEqual(client.post(PERCEPCION, dict(categoria='ADECUADA', version_esperada=0, csrfmiddlewaretoken=token)).status_code, 302)

    def test_comparacion_sin_observaciones_no_afirma_cero(self):
        datos = comparacion_fixture(False)
        datos.update(referencia=historico_fixture('sin_datos'), comparado=historico_fixture('sin_datos'), motivos=['SIN_DATOS'])
        with patch('apps.historico.services.comparar_periodos', return_value=datos):
            response = self.client.get('/historico/comparar/', PERIODOS)
            self.assertContains(response, 'SIN_DATOS')
            self.assertNotContains(response, '0,00 pp')
            self.assertContains(response, 'Esto no significa cero sobrantes', count=2)

    def test_opciones_historicas_desactivadas_se_conservan(self):
        opciones = opciones_fixture()
        opciones['platos'].append(dict(codigo='plato_anterior', nombre='Plato anterior (retirado)'))
        self.opciones.return_value = opciones
        with patch('apps.historico.services.consultar_panel', return_value=_panel_fixture(historico_fixture())) as consulta:
            response = self.client.get('/historico/', dict(plato='plato_anterior'))
            self.assertContains(response, 'Plato anterior (retirado)')
            self.assertEqual(consulta.call_args.args[0]['plato'], 'plato_anterior')
