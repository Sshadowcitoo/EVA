from datetime import date
from unittest.mock import patch
from uuid import UUID
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import include, path
from .contracts import BackendRecomendacionesNoDisponible, CasoNoDisponible, ConflictoRecomendacion, EvidenciaDesactualizada, ParametrosInvalidos
from .testing.fixtures import EID, RID, PID, detalle_fixture, lista_fixture, opciones_fixture_recomendaciones, prueba_fixture

urlpatterns = [path('recomendaciones/', include('apps.recomendaciones.urls')), path('', include('config.urls'))]
LISTA='/recomendaciones/'
EVALUAR=LISTA+'evaluar/'
EVALUACION=LISTA+f'evaluaciones/{EID}/'
GENERAR=EVALUACION+'generar/'
DETALLE=LISTA+RID+'/'
DECIDIR=DETALLE+'decidir/'
REGISTRAR=DETALLE+'pruebas/'
PRUEBA=LISTA+f'pruebas/{PID}/'
EVALUAR_PRUEBA=PRUEBA+'evaluar/'
FILTROS=dict(plato='seco_de_pollo',componente='arroz',porcion='estandar',desde='2026-10-01',hasta='2026-10-14')
DECISION=dict(decision='ACEPTADA',justificacion='Razón de prueba',version_esperada=0)
ENSAYO=dict(cambio='Cambio supervisado',responsable_id=1,referencia_desde='2026-10-17',referencia_hasta='2026-10-23',intervencion_desde='2026-10-24',intervencion_hasta='2026-10-30')
LECTURAS=[LISTA,EVALUACION,DETALLE,PRUEBA]
ESCRITURAS=[(EVALUAR,{**FILTROS,'version_criterios':'fixture-v1'}),(GENERAR,{}),(DECIDIR,DECISION),(REGISTRAR,ENSAYO),(EVALUAR_PRUEBA,{'version_esperada':1})]


@override_settings(ROOT_URLCONF=__name__)
class RecomendacionesWebTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuarios={}
        for rol in ('Registro','Cocina','Administración','Sin rol'):
            user=get_user_model().objects.create_user(username=rol)
            if rol!='Sin rol':user.groups.add(Group.objects.get_or_create(name=rol)[0])
            cls.usuarios[rol]=user

    def setUp(self):
        self.client.force_login(self.usuarios['Administración'])
        valores=dict(opciones_recomendaciones=opciones_fixture_recomendaciones(),consultar_recomendaciones=lista_fixture(),evaluar_evidencia=detalle_fixture('sin_propuesta'),obtener_evaluacion=detalle_fixture('sin_propuesta'),generar_recomendacion=detalle_fixture(),obtener_recomendacion=detalle_fixture(),decidir_recomendacion=detalle_fixture('aceptada'),registrar_prueba=prueba_fixture('REGISTRADA'),obtener_prueba=prueba_fixture(),evaluar_prueba=prueba_fixture())
        self.servicios={}
        for nombre, valor in valores.items():
            parche=patch('apps.recomendaciones.services.'+nombre,return_value=valor)
            self.servicios[nombre]=parche.start()
            self.addCleanup(parche.stop)

    def test_roles_aislados_en_cada_endpoint(self):
        for rol,user in self.usuarios.items():
            self.client.force_login(user)
            for url in LECTURAS:
                with self.subTest(rol=rol,url=url):self.assertEqual(self.client.get(url).status_code,200 if rol == 'Administración' else 403)
            for url,datos in ESCRITURAS:
                with self.subTest(rol=rol,url=url):self.assertEqual(self.client.post(url,datos).status_code,302 if rol=='Administración' else 403)

    def test_staff_inactivo_anonimo_superusuario_y_multirrol(self):
        user=self.usuarios['Sin rol'];user.is_staff=True;user.save();self.client.force_login(user)
        self.assertEqual(self.client.get(LISTA).status_code,403)
        self.client.logout();self.assertEqual(self.client.get(LISTA).status_code,302)
        user.is_active=False;user.save();self.client.force_login(user);self.assertEqual(self.client.get(LISTA).status_code,302)
        user.is_active=True;user.is_superuser=True;user.save();self.client.force_login(user);self.assertEqual(self.client.post(GENERAR).status_code,302)
        user=self.usuarios['Registro'];user.groups.add(Group.objects.get(name='Administración'));self.client.force_login(user);self.assertEqual(self.client.post(GENERAR).status_code,302)

    def test_get_no_escribe_y_metodos_rechazados(self):
        for url,_ in ESCRITURAS:self.assertEqual(self.client.get(url).status_code,405)
        for url in LECTURAS:
            self.assertEqual(self.client.post(url).status_code,405)
            self.assertEqual(self.client.get(url).status_code,200)
        for nombre in ('evaluar_evidencia','generar_recomendacion','decidir_recomendacion','registrar_prueba','evaluar_prueba'):
            self.servicios[nombre].assert_not_called()

    def test_cache_privada_y_cocina_sin_acciones_administrativas(self):
        self.client.force_login(self.usuarios['Cocina'])
        for url in LECTURAS:
            r=self.client.get(url);self.assertEqual(r.status_code,403)
            for accion in ('Evaluar evidencia</button>','Guardar decisión con justificación','Generar recomendación</button>','Registrar prueba controlada</button>','Evaluar prueba</button>'):
                self.assertNotContains(r,accion,status_code=403)
        self.client.force_login(self.usuarios['Administración'])
        for url in LECTURAS:
            respuesta=self.client.get(url)
            self.assertEqual(respuesta.status_code,200)
            self.assertIn('no-store',respuesta['Cache-Control'])
            self.assertIn('private',respuesta['Cache-Control'])

    def test_capacidades_del_servidor_controlan_acciones(self):
        caso=detalle_fixture('aceptada');caso['capacidades']={k:False for k in caso['capacidades']}
        self.servicios['obtener_recomendacion'].return_value=caso
        r=self.client.get(DETALLE);self.assertNotContains(r,'Guardar decisión con justificación');self.assertNotContains(r,'Registrar prueba controlada</button>')
        self.servicios['obtener_evaluacion'].return_value=detalle_fixture('sin_propuesta')
        self.assertContains(self.client.get(EVALUACION),'Generar recomendación</button>')

    def test_lista_vacia_y_contadores_no_son_servicios(self):
        self.servicios['consultar_recomendaciones'].return_value=lista_fixture(True)
        r=self.client.get(LISTA);self.assertContains(r,'No hay evaluaciones');self.assertContains(r,'Se cuentan evaluaciones, no servicios');self.assertContains(r,'Datos de ejemplo')

    def test_filtros_paginacion_y_valores_conservados(self):
        datos=lista_fixture();datos['paginacion'].update(pagina=2,paginas=3,total_filas=65);self.servicios['consultar_recomendaciones'].return_value=datos
        r=self.client.get(LISTA,{**FILTROS,'categoria':'REVISAR_PORCION','page':2})
        self.assertEqual(r.status_code,200);llamada=self.servicios['consultar_recomendaciones'].call_args
        self.assertEqual(llamada.args[0]['historico']['fin'].day,15);self.assertEqual(llamada.kwargs,{'pagina':2})
        self.assertIn('categoria=REVISAR_PORCION',r.context['enlaces']['siguiente']);self.assertIn('page=3',r.context['enlaces']['siguiente'])

    def test_filtros_invalidos_no_llaman_consulta(self):
        for cambio in ({'page':0},{'desde':'2026-02-30'},{'hora_desde':'23:00','hora_hasta':'01:00'},{'origen':'SIMULADO'},{'categoria':'OTRA'},{'plato':'desconocido'}):
            self.servicios['consultar_recomendaciones'].reset_mock()
            r=self.client.get(LISTA,{**FILTROS,**cambio});self.assertEqual(r.status_code,400);self.servicios['consultar_recomendaciones'].assert_not_called()
        r=self.client.get(LISTA,{**FILTROS,'hasta':'2026-09-01'});self.assertContains(r,'value="2026-10-01"',status_code=400)

    def test_evaluar_normaliza_sin_aceptar_cifras_del_navegador(self):
        r=self.client.post(EVALUAR,{**FILTROS,'version_criterios':'fixture-v1','usuario':'otro','n':999,'suficiencia':'SUFICIENTE'})
        self.assertRedirects(r,EVALUACION,fetch_redirect_response=False)
        args=self.servicios['evaluar_evidencia'].call_args.args
        self.assertEqual(args[1],'fixture-v1');self.assertEqual(args[2],self.usuarios['Administración']);self.assertNotIn('n',args[0])
        self.assertEqual(args[0]['fin'].day,15)

    def test_evaluar_sin_version_o_fechas_invalidas(self):
        self.servicios['opciones_recomendaciones'].return_value['versiones_criterios']=[]
        self.assertEqual(self.client.post(EVALUAR,FILTROS).status_code,302)
        self.assertIsNone(self.servicios['evaluar_evidencia'].call_args.args[1])
        for datos in ({**FILTROS,'desde':''},{**FILTROS,'hasta':'2026-09-01'},{**FILTROS,'version_criterios':'inventada'}):
            self.servicios['evaluar_evidencia'].reset_mock();self.assertEqual(self.client.post(EVALUAR,datos).status_code,400);self.servicios['evaluar_evidencia'].assert_not_called()

    def test_escenarios_insuficientes_no_generan_ajuste(self):
        for escenario in ('insuficiente','configuracion_pendiente','sin_datos','simulada'):
            self.servicios['obtener_evaluacion'].return_value=detalle_fixture(escenario)
            r=self.client.get(EVALUACION);self.assertContains(r,'Evidencia insuficiente');self.assertNotContains(r,'Generar recomendación</button>');self.assertNotContains(r,'Propuesta: MANTENER')
            self.assertContains(r,'Datos de ejemplo')

    def test_obsoleta_historial_y_ceros_distintos_de_ausencias(self):
        self.servicios['obtener_recomendacion'].return_value=detalle_fixture('obsoleta')
        r=self.client.get(DETALLE);self.assertContains(r,'Evidencia desactualizada');self.assertNotContains(r,'Guardar decisión con justificación')
        for escenario in ('aceptada','descartada','en_observacion'):
            self.servicios['obtener_recomendacion'].return_value=detalle_fixture(escenario)
            r=self.client.get(DETALLE);self.assertContains(r,'Ver decisiones anteriores');self.assertContains(r,'Justificación humana de prueba.');self.assertContains(r,'administracion_fixture')
        caso=detalle_fixture('sin_datos');caso['evaluacion']['indicadores']['intensidad']=0
        self.servicios['obtener_evaluacion'].return_value=caso;r=self.client.get(EVALUACION);self.assertContains(r,'0,00 %');self.assertContains(r,'No disponible')

    def test_decisiones_justificadas_y_usuario_objetivo_de_ruta(self):
        for estado in ('ACEPTADA','DESCARTADA','EN_OBSERVACION'):
            r=self.client.post(DECIDIR,{**DECISION,'decision':estado,'usuario':'otro','recomendacion_id':EID})
            self.assertEqual(r.status_code,302)
            self.servicios['decidir_recomendacion'].assert_called_with(UUID(RID),estado,'Razón de prueba',self.usuarios['Administración'],0)

    def test_decision_invalida_sin_javascript(self):
        for cambios in ({'justificacion':''},{'justificacion':'   '},{'justificacion':'x'*1001},{'decision':'CONFIRMADO'},{'version_esperada':-1},{'version_esperada':'no'},{'version_esperada':2**31}):
            self.servicios['decidir_recomendacion'].reset_mock();r=self.client.post(DECIDIR,{**DECISION,**cambios});self.assertEqual(r.status_code,400);self.servicios['decidir_recomendacion'].assert_not_called()

    def test_conflicto_y_evidencia_desactualizada_conservan_borrador_sin_reintento(self):
        for exc in (ConflictoRecomendacion(),EvidenciaDesactualizada()):
            self.servicios['decidir_recomendacion'].side_effect=exc;self.servicios['decidir_recomendacion'].reset_mock()
            self.servicios['obtener_recomendacion'].return_value=detalle_fixture('obsoleta')
            r=self.client.post(DECIDIR,{**DECISION,'justificacion':'<borrador>'})
            self.assertContains(r,'&lt;borrador&gt;',status_code=409);self.assertContains(r,'Recargar el caso vigente',status_code=409)
            self.assertContains(r,'data-bloqueado="true"',status_code=409);self.servicios['decidir_recomendacion'].assert_called_once()

    def test_registro_prueba_responsable_y_periodos_normalizados(self):
        self.assertEqual(self.client.post(REGISTRAR,ENSAYO).status_code,302)
        args=self.servicios['registrar_prueba'].call_args.args
        self.assertEqual(args[:3],(UUID(RID),'Cambio supervisado',1));self.assertEqual(args[3]['intervencion_desde'],date(2026,10,24));self.assertEqual(args[4],self.usuarios['Administración'])

    def test_prueba_rechaza_periodos_responsable_y_cambio_invalidos(self):
        for cambios in ({'cambio':''},{'responsable_id':999},{'intervencion_desde':'2026-10-23'},{'referencia_hasta':'2026-10-01'},{'intervencion_hasta':'invalida'}):
            self.servicios['registrar_prueba'].reset_mock();r=self.client.post(REGISTRAR,{**ENSAYO,**cambios});self.assertEqual(r.status_code,400);self.servicios['registrar_prueba'].assert_not_called()

    def test_detalles_de_prueba_sin_comparacion_y_no_evaluable(self):
        for estado,texto in [('REGISTRADA','todavía sin evaluación'),('NO_EVALUABLE','No evaluable'),('EVALUADA','0,00 pp')]:
            self.servicios['obtener_prueba'].return_value=prueba_fixture(estado)
            r=self.client.get(PRUEBA);self.assertContains(r,texto)
        self.servicios['obtener_prueba'].return_value=prueba_fixture('NO_EVALUABLE')
        self.assertNotContains(self.client.get(PRUEBA),'0,00 pp')

    def test_evaluar_prueba_version_y_conflicto(self):
        self.assertEqual(self.client.post(EVALUAR_PRUEBA,{'version_esperada':1}).status_code,302)
        self.servicios['evaluar_prueba'].assert_called_once_with(UUID(PID),self.usuarios['Administración'],1)
        self.servicios['evaluar_prueba'].side_effect=ConflictoRecomendacion()
        r=self.client.post(EVALUAR_PRUEBA,{'version_esperada':1});self.assertContains(r,'Recargar versión de la prueba',status_code=409)
        self.assertEqual(self.client.post(EVALUAR_PRUEBA,{'version_esperada':-1}).status_code,400)

    def test_cada_servicio_pendiente_es_503_explicito(self):
        casos=[('opciones_recomendaciones',LISTA,None),('consultar_recomendaciones',LISTA,None),('obtener_evaluacion',EVALUACION,None),('obtener_recomendacion',DETALLE,None),('obtener_prueba',PRUEBA,None),('evaluar_evidencia',EVALUAR,FILTROS),('generar_recomendacion',GENERAR,{}),('decidir_recomendacion',DECIDIR,DECISION),('registrar_prueba',REGISTRAR,ENSAYO),('evaluar_prueba',EVALUAR_PRUEBA,{'version_esperada':1})]
        for nombre,url,datos in casos:
            with self.subTest(nombre=nombre):
                self.servicios[nombre].side_effect=BackendRecomendacionesNoDisponible()
                r=self.client.get(url) if datos is None else self.client.post(url,datos)
                self.assertContains(r,'pendiente de conexión',status_code=503);self.assertNotContains(r,'guardada correctamente',status_code=503)
                self.servicios[nombre].side_effect=None

    def test_404_403_validacion_escapada_y_excepcion_desconocida(self):
        for exc,codigo in [(CasoNoDisponible(),404),(PermissionDenied(),403),(ParametrosInvalidos({'__all__':'<error>'}),400),(ValidationError('<error>'),400)]:
            self.servicios['obtener_evaluacion'].side_effect=exc
            self.assertEqual(self.client.get(EVALUACION).status_code,codigo)
        self.servicios['obtener_evaluacion'].side_effect=RuntimeError('error no previsto')
        with self.assertRaises(RuntimeError):self.client.get(EVALUACION)
        self.servicios['obtener_evaluacion'].side_effect=None
        self.servicios['decidir_recomendacion'].side_effect=ValidationError({'justificacion':'<error>'})
        self.assertContains(self.client.post(DECIDIR,DECISION),'&lt;error&gt;',status_code=400)

    def test_csrf_en_todos_los_post_y_con_token(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.usuarios['Administración'])
        for url,datos in ESCRITURAS:self.assertEqual(client.post(url,datos).status_code,403)
        client.get(LISTA);token=client.cookies['csrftoken'].value
        for url,datos in ESCRITURAS:self.assertEqual(client.post(url,{**datos,'csrfmiddlewaretoken':token}).status_code,302)

    def test_textos_escapados_y_exito_no_fabricado_por_get(self):
        caso=detalle_fixture('aceptada');caso['recomendacion']['explicacion']='<script>mal</script>';caso['evaluacion']['criterios']['parametros']={'<clave>':'<valor>'}
        self.servicios['obtener_recomendacion'].return_value=caso
        r=self.client.get(DETALLE+'?guardada=1');self.assertContains(r,'&lt;script&gt;');self.assertNotContains(r,'<script>mal</script>');self.assertNotContains(r,'Decisión guardada.')
        self.assertContains(r,'&lt;valor&gt;')

    def test_guardado_prg_y_reenvio_pasa_a_idempotencia_del_servidor(self):
        for _ in range(2):self.assertEqual(self.client.post(DECIDIR,DECISION).status_code,302)
        self.assertEqual(self.servicios['decidir_recomendacion'].call_count,2)
        self.assertContains(self.client.get(DETALLE),'Decisión guardada.')

    def test_opciones_pendientes_conservan_selecciones_del_borrador(self):
        self.servicios['opciones_recomendaciones'].side_effect=BackendRecomendacionesNoDisponible()
        r=self.client.post(EVALUAR,{**FILTROS,'version_criterios':'fixture-v1'})
        self.assertContains(r,'Selección enviada: seco_de_pollo',status_code=503)
        self.assertContains(r,'Selección enviada: fixture-v1',status_code=503)
        self.servicios['evaluar_evidencia'].assert_not_called()
        r=self.client.post(REGISTRAR,ENSAYO)
        self.assertContains(r,'Cambio supervisado',status_code=503)
        self.assertContains(r,'Selección enviada: 1',status_code=503)
        self.servicios['registrar_prueba'].assert_not_called()

    def test_conflicto_no_se_pierde_si_falla_la_lectura_actualizada(self):
        self.servicios['decidir_recomendacion'].side_effect=EvidenciaDesactualizada()
        self.servicios['obtener_recomendacion'].side_effect=BackendRecomendacionesNoDisponible()
        r=self.client.post(DECIDIR,{**DECISION,'justificacion':'Mi borrador conservado'})
        self.assertContains(r,'Mi borrador conservado',status_code=409)
        self.assertContains(r,'vuelve a decidir',status_code=409)

    def test_conflictos_de_generacion_registro_y_evaluacion_sin_reintento(self):
        for nombre,url,datos in [('generar_recomendacion',GENERAR,{}),('registrar_prueba',REGISTRAR,ENSAYO),('evaluar_evidencia',EVALUAR,FILTROS),('evaluar_prueba',EVALUAR_PRUEBA,{'version_esperada':1})]:
            with self.subTest(nombre=nombre):
                self.servicios[nombre].side_effect=ConflictoRecomendacion()
                self.servicios[nombre].reset_mock()
                r=self.client.post(url,datos)
                self.assertEqual(r.status_code,409)
                self.servicios[nombre].assert_called_once()
                self.servicios[nombre].side_effect=None

    def test_formularios_de_filtro_y_evaluacion_tienen_ids_unicos(self):
        from html.parser import HTMLParser
        class Identificadores(HTMLParser):
            def __init__(self):
                super().__init__();self.ids=[]
            def handle_starttag(self, tag, attrs):
                self.ids.extend(valor for clave,valor in attrs if clave=='id')
        parser=Identificadores();parser.feed(self.client.get(LISTA).content.decode())
        self.assertEqual(len(parser.ids),len(set(parser.ids)))
        self.assertIn('evaluar_desde',parser.ids)
        self.assertIn('id_desde',parser.ids)
