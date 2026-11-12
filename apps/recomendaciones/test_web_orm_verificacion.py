"""HTTP sobre ORM real. Ningún caso sustituye apps.recomendaciones.services.

La clase operativa conserva los criterios reales sin aprobar y sin contexto.
La clase hipotética reutiliza SOLO el contexto técnico de tests de dominio para
alcanzar decisiones/pruebas: no certifica suficiencia ni configura la operación.
"""
from copy import deepcopy
from datetime import date, timedelta
import os
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, override_settings
from django.urls import reverse

from apps.analisis.models import RevisionAnalisis
from apps.historico.test_dominio_historico import BaseHistorico
from . import models as m
from . import test_dominio_recomendaciones as dominio


class BaseHTTP(BaseHistorico):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = get_user_model().objects.create_user('admin_verificacion')
        cls.admin.groups.add(Group.objects.get(name='Administración'))
        cls.otro = get_user_model().objects.create_user('otro_verificacion')
        cls.otro.groups.add(Group.objects.get(name='Administración'))
        cls.staff = get_user_model().objects.create_user('staff_verificacion', is_staff=True)

    def evaluar(self, version='', **extra):
        self.client.force_login(self.admin)
        return self.client.post(reverse('recomendaciones:evaluar'), dict(plato='seco_de_pollo', componente='arroz', desde='2026-10-01', hasta='2026-10-07', version_criterios=version, **extra))

    def conteos(self):
        return tuple(modelo.objects.count() for modelo in (m.EvaluacionEvidencia,m.Recomendacion,m.DecisionRecomendacion,m.PruebaControlada,m.EvaluacionPrueba))

    def captura_html(self, nombre, response):
        # Exportación opcional de respuestas reales de este ensayo, nunca proveedor productivo.
        destino = os.environ.get('EVA_VERIFY_VISUAL_DIR')
        if destino:
            ruta=Path(destino);ruta.mkdir(parents=True,exist_ok=True)
            (ruta/(nombre+'.html')).write_bytes(response.content)


class OperacionRealHTTPTests(BaseHTTP):
    def test_evaluacion_repetida_sin_aprobacion_conserva_id_y_no_propone(self):
        self.caso()
        configuracion=deepcopy(getattr(settings,'EVA_RECOMENDACIONES_CRITERIOS',{}))
        self.assertFalse(configuracion.get('aprobada',False))
        a=self.evaluar();b=self.evaluar()
        self.assertEqual(a.status_code,302);self.assertEqual(a.url,b.url)
        self.assertEqual(self.conteos(),(1,0,0,0,0))
        response=self.client.get(a.url)
        self.assertContains(response,'Evidencia insuficiente')
        self.assertFalse(response.context['caso']['evaluacion']['solo_pruebas'])
        self.assertFalse(response.context['caso']['evaluacion']['criterios']['aprobada'])
        self.assertTrue(all(g['contexto_clave'] is None for g in response.context['caso']['evaluacion']['grupos']))
        self.assertNotContains(response,'Generar recomendación</button>')
        self.assertEqual(configuracion,getattr(settings,'EVA_RECOMENDACIONES_CRITERIOS',{}))
        self.captura_html('insuficiente-operativa',response)
        self.captura_html('lista-operativa',self.client.get(reverse('recomendaciones:lista')))
        self.client.force_login(self.cocina)
        self.assertEqual(self.client.get(reverse('recomendaciones:lista')).status_code,403)
        self.client.force_login(self.admin)
        rechazo=self.client.post(reverse('recomendaciones:generar',args=[m.EvaluacionEvidencia.objects.get().pk]))
        self.assertEqual(rechazo.status_code,409)
        self.assertContains(rechazo,'La evidencia es insuficiente para generar una recomendación.',status_code=409)
        self.assertEqual(self.conteos(),(1,0,0,0,0))
        self.captura_html('generacion-rechazada',rechazo)

    def test_filtros_y_paginacion_con_conteos_del_conjunto_completo(self):
        self.caso();self.client.force_login(self.admin)
        inicio=date(2026,10,1)
        for i in range(31):
            dia=(inicio+timedelta(days=i)).isoformat()
            response=self.client.post(reverse('recomendaciones:evaluar'),dict(plato='seco_de_pollo',componente='arroz',desde=dia,hasta=dia,version_criterios=''))
            self.assertEqual(response.status_code,302)
        lista=reverse('recomendaciones:lista')
        response=self.client.get(lista,dict(plato='seco_de_pollo',suficiencia='INSUFICIENTE',page=2))
        datos=response.context['datos']
        self.assertEqual(datos['resumen']['total'],31)
        self.assertEqual(datos['paginacion']['pagina'],2)
        self.assertEqual(len(datos['filas']),1)
        self.assertIn('suficiencia=INSUFICIENTE',response.context['enlaces']['anterior'])
        filtrada=self.client.get(lista,dict(desde='2026-10-03',hasta='2026-10-03'))
        self.assertEqual(filtrada.context['datos']['resumen']['total'],1)
        for filtros in (dict(categoria='MANTENER'),dict(decision='ACEPTADA')):
            self.assertEqual(self.client.get(lista,filtros).context['datos']['resumen']['total'],0)
        for filtros in (dict(page=0),dict(plato='inexistente'),dict(origen='SIMULADO')):
            self.assertEqual(self.client.get(lista,filtros).status_code,400)
        self.assertEqual(m.EvaluacionEvidencia.objects.count(),31)

    def test_revision_nueva_invalida_snapshot_sin_borrarlo(self):
        _,_,intento=self.caso();response=self.evaluar();evaluacion=m.EvaluacionEvidencia.objects.get()
        snapshot=deepcopy(evaluacion.snapshot)
        RevisionAnalisis.objects.filter(intento=intento,vigente=True).update(vigente=False)
        RevisionAnalisis.objects.create(intento=intento,decision='RECHAZADO',motivo='Revisión posterior del ensayo',autor=self.cocina,version=2)
        vieja=self.client.get(response.url)
        self.assertContains(vieja,'Evidencia desactualizada')
        self.assertFalse(vieja.context['caso']['evaluacion']['vigente'])
        self.assertEqual(self.client.post(reverse('recomendaciones:generar',args=[evaluacion.pk])).status_code,409)
        evaluacion.refresh_from_db();self.assertEqual(evaluacion.snapshot,snapshot)
        self.assertEqual(self.evaluar().status_code,302)
        self.assertEqual(m.EvaluacionEvidencia.objects.count(),2)
        self.assertEqual(self.client.get(reverse('recomendaciones:lista')).context['datos']['resumen']['obsoletas'],1)
        self.captura_html('evidencia-obsoleta',vieja)

    def test_formulario_invalido_y_uuid_ajeno_no_fabrican_registros(self):
        self.caso();self.client.force_login(self.admin)
        for datos in (dict(desde='2026-02-30',hasta='2026-10-07'),dict(desde='2026-10-08',hasta='2026-10-01'),dict(desde='2026-10-01',hasta='2026-10-07',version_criterios='inventada')):
            response=self.client.post(reverse('recomendaciones:evaluar'),datos)
            self.assertEqual(response.status_code,400)
        for nombre,arg in [('evaluacion','evaluacion_id'),('detalle','recomendacion_id'),('prueba','prueba_id')]:
            self.assertEqual(self.client.get(reverse('recomendaciones:'+nombre,kwargs={arg:uuid4()})).status_code,404)
        self.assertEqual(self.conteos(),(0,0,0,0,0))


@override_settings(EVA_RECOMENDACIONES_CRITERIOS=dominio.CONFIG,EVA_HISTORICO_CRITERIOS=dominio.PRESENCIA)
class EscenariosHipoteticosHTTPTests(BaseHTTP):
    def contexto_hipotetico(self):
        # Único doble: contexto inexistente habilitado por el helper técnico del dominio.
        # Las funciones services, vistas, modelos y transacciones NO se sustituyen.
        return dominio.DominioRecomendacionesTests.contexto(self)

    def preparar(self, aceptar=False, prueba=False):
        self.caso();self.assertEqual(self.evaluar('fixture-v1').status_code,302)
        e=m.EvaluacionEvidencia.objects.get()
        self.assertEqual(self.client.post(reverse('recomendaciones:generar',args=[e.pk])).status_code,302)
        r=m.Recomendacion.objects.get()
        if aceptar or prueba:
            self.assertEqual(self.client.post(reverse('recomendaciones:decidir',args=[r.pk]),dict(decision='ACEPTADA',justificacion='Aceptación hipotética para verificar software',version_esperada=0)).status_code,302)
        if prueba:
            self.assertEqual(self.client.post(reverse('recomendaciones:registrar_prueba',args=[r.pk]),self.datos_prueba()).status_code,302)
        return e,r,m.PruebaControlada.objects.first()

    def datos_prueba(self):
        return dict(cambio='Ensayo hipotético, no criterio operativo',responsable_id=self.cocina.pk,referencia_desde='2026-10-01',referencia_hasta='2026-10-07',intervencion_desde='2026-10-08',intervencion_hasta='2026-10-14')

    def endpoints(self,e,r,p):
        lecturas=[reverse('recomendaciones:lista'),reverse('recomendaciones:evaluacion',args=[e.pk]),reverse('recomendaciones:detalle',args=[r.pk]),reverse('recomendaciones:prueba',args=[p.pk])]
        escrituras=[(reverse('recomendaciones:evaluar'),dict(plato='seco_de_pollo',componente='arroz',desde='2026-10-01',hasta='2026-10-07',version_criterios='fixture-v1')),(reverse('recomendaciones:generar',args=[e.pk]),{}),(reverse('recomendaciones:decidir',args=[r.pk]),dict(decision='ACEPTADA',justificacion='Aceptación hipotética para verificar software',version_esperada=0)),(reverse('recomendaciones:registrar_prueba',args=[r.pk]),self.datos_prueba()),(reverse('recomendaciones:evaluar_prueba',args=[p.pk]),dict(version_esperada=0))]
        return lecturas,escrituras

    def test_roles_reales_en_todas_las_rutas_y_csrf_en_cada_post(self):
        with self.contexto_hipotetico():
            e,r,p=self.preparar(prueba=True);lecturas,escrituras=self.endpoints(e,r,p)
            antes=self.conteos()
            for user in (self.cocina,self.registro,self.staff):
                self.client.force_login(user)
                for url in lecturas:
                    self.assertEqual(self.client.get(url).status_code,403)
                for url,datos in escrituras:self.assertEqual(self.client.post(url,datos).status_code,403)
            self.assertEqual(self.conteos(),antes)
            cliente=Client(enforce_csrf_checks=True);cliente.force_login(self.admin)
            for url,datos in escrituras:self.assertEqual(cliente.post(url,datos).status_code,403)
            self.assertEqual(self.conteos(),antes)
            cliente.get(lecturas[0]);token=cliente.cookies['csrftoken'].value
            for url,datos in escrituras:
                self.assertEqual(cliente.post(url,{**datos,'csrfmiddlewaretoken':token}).status_code,302)
            self.assertEqual(m.EvaluacionPrueba.objects.count(),1)
            self.client.force_login(self.cocina)
            consulta=self.client.get(reverse('recomendaciones:detalle',args=[r.pk]))
            self.assertNotContains(consulta,'Guardar decisión con justificación',status_code=403)
            self.assertNotContains(consulta,'Registrar prueba controlada</button>',status_code=403)

    def test_get_no_escribe_y_respuestas_privadas_con_recursos_existentes(self):
        with self.contexto_hipotetico():
            e,r,p=self.preparar(prueba=True);lecturas,escrituras=self.endpoints(e,r,p)
            antes=self.conteos()
            for _ in range(2):
                for url in lecturas:
                    response=self.client.get(url);self.assertEqual(response.status_code,200)
                    self.assertIn('no-store',response['Cache-Control'])
                for url,_ in escrituras:self.assertEqual(self.client.get(url).status_code,405)
            self.assertEqual(self.conteos(),antes)

    def test_doble_envio_decision_historial_y_conflicto_entre_operadores(self):
        with self.contexto_hipotetico():
            e,r,_=self.preparar();url=reverse('recomendaciones:decidir',args=[r.pk])
            datos=dict(decision='ACEPTADA',justificacion='Primera decisión verificable',version_esperada=0)
            for _ in range(2):self.assertEqual(self.client.post(url,datos).status_code,302)
            original=r.decisiones.get();self.assertEqual(original.autor,self.admin)
            self.client.force_login(self.otro)
            response=self.client.post(url,dict(decision='DESCARTADA',justificacion='<borrador de otro operador>',version_esperada=0))
            self.assertContains(response,'&lt;borrador de otro operador&gt;',status_code=409)
            self.assertContains(response,'data-bloqueado="true"',status_code=409)
            self.assertEqual(response.context['decision_form'].data['version_esperada'],'0')
            self.assertEqual(response.context['caso']['version_esperada'],1)
            self.assertEqual(r.decisiones.count(),1)
            self.assertEqual(self.client.post(url,dict(decision='EN_OBSERVACION',justificacion='Segunda decisión verificable',version_esperada=1)).status_code,302)
            nueva=r.decisiones.get(version=2);self.assertEqual(nueva.sustituye_id,original.pk)
            original.refresh_from_db();self.assertEqual(original.justificacion,'Primera decisión verificable')
            detalle=self.client.get(reverse('recomendaciones:detalle',args=[r.pk]))
            self.assertContains(detalle,'Primera decisión verificable');self.assertContains(detalle,'Segunda decisión verificable')
            self.assertContains(detalle,self.otro.username)
            self.assertNotContains(detalle,'Registrar prueba controlada</button>')

    def test_prueba_reenvio_historial_versiones_y_aceptacion_sustituida(self):
        with self.contexto_hipotetico():
            e,r,p=self.preparar(prueba=True)
            crear=reverse('recomendaciones:registrar_prueba',args=[r.pk])
            self.assertEqual(self.client.post(crear,self.datos_prueba()).status_code,302)
            self.assertEqual(m.PruebaControlada.objects.count(),1)
            url=reverse('recomendaciones:evaluar_prueba',args=[p.pk])
            self.assertEqual(self.client.post(url,dict(version_esperada=0)).status_code,302)
            primera=p.evaluaciones.get();snapshot=deepcopy(primera.snapshot)
            self.assertEqual(self.client.post(url,dict(version_esperada=0)).status_code,409)
            self.assertEqual(p.evaluaciones.count(),1)
            self.assertEqual(self.client.post(url,dict(version_esperada=1)).status_code,302)
            self.assertEqual(list(p.evaluaciones.order_by('version').values_list('version',flat=True)),[1,2])
            primera.refresh_from_db();self.assertEqual(primera.snapshot,snapshot)
            response=self.client.get(reverse('recomendaciones:prueba',args=[p.pk]))
            self.assertContains(response,'No evaluable');self.assertEqual(response.context['prueba']['version'],2)
            self.assertIsNone(response.context['prueba']['comparacion']['diferencias']['intensidad_pp'])
            self.assertEqual(self.client.post(reverse('recomendaciones:decidir',args=[r.pk]),dict(decision='ACEPTADA',justificacion='Aceptación posterior distinta',version_esperada=1)).status_code,302)
            self.assertEqual(self.client.post(url,dict(version_esperada=2)).status_code,409)
            p.refresh_from_db();self.assertEqual(p.aceptacion_id,r.decisiones.get(version=1).pk)
            self.assertEqual(p.evaluaciones.count(),2)
            response=self.client.get(reverse('recomendaciones:prueba',args=[p.pk]))
            self.assertFalse(response.context['prueba']['puede_evaluar'])
            self.assertNotContains(response,'Evaluar prueba</button>')
            self.assertContains(response,'Revisa la vigencia de la evidencia y la aceptación vinculada.')

    def test_formularios_invalidos_no_alteran_historial_ni_crean_pruebas(self):
        with self.contexto_hipotetico():
            _,r,_=self.preparar(aceptar=True);antes=self.conteos()
            for texto in ('','   ','x'*1001):
                self.assertEqual(self.client.post(reverse('recomendaciones:decidir',args=[r.pk]),dict(decision='DESCARTADA',justificacion=texto,version_esperada=1)).status_code,400)
            for cambios in (dict(responsable_id=self.registro.pk),dict(intervencion_desde='2026-10-07'),dict(cambio='')):
                self.assertEqual(self.client.post(reverse('recomendaciones:registrar_prueba',args=[r.pk]),{**self.datos_prueba(),**cambios}).status_code,400)
            self.assertEqual(self.conteos(),antes)

    def test_vigencia_rechaza_decision_y_conserva_borrador_sin_reenvio(self):
        with self.contexto_hipotetico():
            e,r,p=self.preparar(prueba=True)
            self.assertEqual(self.client.post(reverse('recomendaciones:evaluar_prueba',args=[p.pk]),dict(version_esperada=0)).status_code,302)
        # Se restauran los criterios operativos sin aprobar y el contexto ausente.
        with override_settings(EVA_RECOMENDACIONES_CRITERIOS={'version':None,'aprobada':False,'reglas':{}},EVA_HISTORICO_CRITERIOS={'version':None,'aprobada':False,'presencia_t':None}):
            antes=self.conteos()
            url=reverse('recomendaciones:decidir',args=[r.pk])
            response=self.client.post(url,dict(decision='DESCARTADA',justificacion='Borrador ante criterios sin aprobar',version_esperada=1))
            self.assertContains(response,'Borrador ante criterios sin aprobar',status_code=409)
            self.assertContains(response,'Evidencia desactualizada',status_code=409)
            self.assertContains(response,'Avisos de operaciones anteriores',status_code=409)
            html=response.content.decode()
            self.assertLess(html.index('Operación sin confirmar'),html.index('Avisos de operaciones anteriores'))
            self.assertEqual(self.conteos(),antes)
            self.assertEqual(r.decisiones.get().decision,'ACEPTADA')
            self.captura_html('conflicto-historico-hipotetico',response)
            prueba=self.client.get(reverse('recomendaciones:prueba',args=[p.pk]))
            self.assertContains(prueba,'Evidencia vinculada desactualizada')
            self.assertNotContains(prueba,'Evaluar prueba</button>')
            self.captura_html('prueba-historica-no-evaluable',prueba)
