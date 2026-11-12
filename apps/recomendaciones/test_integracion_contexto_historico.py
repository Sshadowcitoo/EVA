"""Captura HTTP -> resultados históricos de ensayo -> histórico/recomendaciones reales.

No ejecuta un motor ni acredita precisión. La entrada de resultados/revisión es un
oráculo ORM sintético de mediciones históricas conocidas; no aprueba settings.
No sustituye services, selectores ni contexto. Solo se controla el reloj de captura.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.analisis import services as analisis_services
from apps.analisis.models import AnalisisServicio, IntentoAnalisis, ResultadoComponente, RevisionAnalisis
from apps.captura import storage
from apps.captura.models import Bandeja, Servicio, FotografiaServicio
from apps.captura.protocolo import CRITERIOS
from apps.catalogo.models import Plato, TipoPorcion
from .models import EvaluacionEvidencia, Recomendacion

ZONA=ZoneInfo('America/Guayaquil')
FILTROS=dict(plato='seco_de_pollo',componente='arroz',porcion='estandar',desde='2026-11-01',hasta='2026-11-14')


class IntegracionContextoHistoricoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('cargar_catalogo_demo',verbosity=0)
        call_command('configurar_roles',stdout=StringIO())
        cls.registro=get_user_model().objects.create_user('registro_integracion_contexto')
        cls.registro.groups.add(Group.objects.get(name='Registro'))
        cls.cocina=get_user_model().objects.create_user('cocina_integracion_contexto')
        cls.cocina.groups.add(Group.objects.get(name='Cocina'))
        cls.admin=get_user_model().objects.create_user('admin_integracion_contexto')
        cls.admin.groups.add(Group.objects.get(name='Administración'))

    def setUp(self):
        carpeta=TemporaryDirectory();self.addCleanup(carpeta.cleanup)
        config=override_settings(EVA_CAPTURE_PRIVATE_ROOT=Path(carpeta.name),EVA_STORAGE_BACKEND='local')
        config.enable();self.addCleanup(config.disable)

    def foto(self,color):
        salida=BytesIO();Image.new('RGB',(4,4),color).save(salida,'PNG')
        return dict(foto=SimpleUploadedFile('ensayo.png',salida.getvalue(),content_type='image/png'),**dict.fromkeys(CRITERIOS,True))

    def capturar(self,*,lote='preparacion-uno',modalidad='mesa',sede='principal',dia=3,hora=12,contexto=True,retorno=True):
        self.client.force_login(self.registro)
        b=Bandeja.objects.create(numero=1000+Bandeja.objects.count())
        datos=dict(plato=Plato.objects.get(codigo='seco_de_pollo').pk,tipo_porcion=TipoPorcion.objects.get(codigo='estandar').pk,
                   sede=sede if contexto else '',modalidad=modalidad if contexto else '',lote_preparacion=lote if contexto else '')
        respuesta=self.client.post(reverse('captura:resolver_bandeja')+'?numero='+str(b.numero),datos)
        self.assertEqual(respuesta.status_code,302)
        s=Servicio.objects.get(asignaciones__bandeja=b)
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,dia,hora,15,tzinfo=ZONA)):
            self.assertEqual(self.client.post(respuesta.url,self.foto('red')).status_code,302)
        s.refresh_from_db();snapshot=deepcopy(s.contexto_snapshot);clave=s.contexto_clave
        if retorno:
            with patch('django.utils.timezone.now',return_value=datetime(2026,11,dia,18,15,tzinfo=ZONA)):
                self.assertEqual(self.client.post(reverse('captura:foto_retorno',args=[s.pk]),self.foto('green')).status_code,302)
            s.refresh_from_db()
            self.assertEqual(s.contexto_snapshot,snapshot);self.assertEqual(s.contexto_clave,clave)
        return s

    def medicion_historica(self,servicio,porcentaje=25):
        # Oráculo de resultado previamente revisado. No llama YOLO, no aprueba
        # configuración vigente ni salta la guarda de generación de recomendaciones.
        a,i,_=analisis_services.solicitar_analisis(servicio=servicio,solicitante=self.cocina,
            version_modelo='oraculo-historico-test',version_configuracion='oraculo-criterios-test',origen='REAL')
        i.estado='COMPLETADO';i.save(update_fields=['estado'])
        a.intento_vigente=i;a.save(update_fields=['intento_vigente'])
        for comp in servicio.composicion.all():
            ResultadoComponente.objects.create(intento=i,servicio_componente=comp,area_inicial=100,area_residual=porcentaje,
                porcentaje=Decimal(porcentaje),confianza=.9,umbral_aplicado=.7,configuracion_aprobada=True,
                criterio='oraculo-criterios-test',estado='CONCLUYENTE',motivo='')
        RevisionAnalisis.objects.create(intento=i,decision='CONFIRMADO',motivo='',autor=self.cocina,version=1)
        return a,i

    def historico(self,**extra):
        self.client.force_login(self.admin)
        respuesta=self.client.get(reverse('historico:lista'),{**FILTROS,**extra})
        self.assertEqual(respuesta.status_code,200)
        return respuesta.context['datos']

    def evaluar(self):
        self.client.force_login(self.admin)
        respuesta=self.client.post(reverse('recomendaciones:evaluar'),FILTROS)
        self.assertEqual(respuesta.status_code,302)
        detalle=self.client.get(respuesta.url);self.assertEqual(detalle.status_code,200)
        return EvaluacionEvidencia.objects.get(pk=detalle.context['caso']['evaluacion']['id']),detalle.context['caso']

    def comprobar_obsoleta(self,e,snapshot):
        self.client.force_login(self.admin)
        detalle=self.client.get(reverse('recomendaciones:evaluacion',args=[e.pk]))
        self.assertContains(detalle,'Evidencia desactualizada')
        self.assertFalse(detalle.context['caso']['evaluacion']['vigente'])
        self.assertFalse(detalle.context['caso']['capacidades']['puede_generar'])
        rechazo=self.client.post(reverse('recomendaciones:generar',args=[e.pk]))
        self.assertEqual(rechazo.status_code,409)
        e.refresh_from_db();self.assertEqual(e.snapshot,snapshot)
        self.assertFalse(Recomendacion.objects.exists())

    def test_contexto_capturado_llega_a_grupos_y_evaluacion_sin_aprobar_criterios(self):
        s=self.capturar();_,i=self.medicion_historica(s)
        contexto=deepcopy(s.contexto_snapshot)
        datos=self.historico()
        self.assertEqual(datos['resumen']['aptos'],1)
        self.assertEqual(datos['grupos'][0]['contexto_clave'],s.contexto_clave)
        self.assertTrue(datos['grupos'][0]['comparable'])
        self.assertEqual(datos['indicadores']['intensidad'],Decimal(25))
        self.assertIsNone(datos['indicadores']['prevalencia'])
        e,caso=self.evaluar()
        self.assertEqual(caso['evaluacion']['grupos'][0]['contexto_clave'],s.contexto_clave)
        self.assertEqual(caso['evaluacion']['referencias'][0]['intento_id'],str(i.pk))
        self.assertEqual(caso['evaluacion']['suficiencia'],'INSUFICIENTE')
        self.assertFalse(caso['evaluacion']['criterios']['aprobada'])
        self.assertIsNone(caso['recomendacion'])
        s.refresh_from_db();self.assertEqual(s.contexto_snapshot,contexto)
        self.assertFalse(settings.EVA_RECOMENDACIONES_CRITERIOS['aprobada'])
        self.assertFalse(settings.EVA_HISTORICO_CRITERIOS['aprobada'])

    def test_lotes_compatibles_no_mezclan_desconocidos_sedes_modalidades_o_franjas(self):
        config=deepcopy(settings.EVA_CONTEXTO_SERVICIO)
        config['sedes'].append(dict(codigo='secundaria-test',nombre='Sede de ensayo'))
        with override_settings(EVA_CONTEXTO_SERVICIO=config):
            datos=[(dict(lote='lote-uno'),20),(dict(lote='lote-dos'),40),(dict(contexto=False),90),
                   (dict(modalidad='autoservicio'),60),(dict(sede='secundaria-test'),70),(dict(hora=13),80)]
            servicios=[]
            for opciones,porcentaje in datos:
                s=self.capturar(**opciones);self.medicion_historica(s,porcentaje);servicios.append(s)
        h=self.historico()
        self.assertEqual(servicios[0].contexto_clave,servicios[1].contexto_clave)
        self.assertEqual(h['resumen']['aptos'],6);self.assertEqual(len(h['grupos']),5)
        grupos={g['contexto_clave']:g for g in h['grupos']}
        self.assertEqual(grupos[servicios[0].contexto_clave]['indicadores']['n'],2)
        self.assertEqual(grupos[servicios[0].contexto_clave]['indicadores']['intensidad'],Decimal(30))
        self.assertEqual(grupos[None]['indicadores']['intensidad'],Decimal(90))
        self.assertFalse(grupos[None]['comparable'])
        self.assertEqual(h['indicadores']['motivos_no_disponible'],['MULTIPLES_GRUPOS'])
        self.assertIsNone(h['indicadores']['intensidad'])
        _,caso=self.evaluar()
        self.assertEqual(len(caso['evaluacion']['grupos']),5)
        self.assertEqual(caso['evaluacion']['suficiencia'],'INSUFICIENTE')
        servicios[2].refresh_from_db();self.assertEqual(servicios[2].contexto_snapshot,{})

    def test_registros_sin_contexto_son_descriptivos_y_no_habilitan_propuestas(self):
        for porcentaje in (10,90):
            s=self.capturar(contexto=False);self.medicion_historica(s,porcentaje)
        h=self.historico()
        self.assertEqual(h['grupos'][0]['indicadores']['n'],2)
        self.assertFalse(h['grupos'][0]['comparable'])
        self.assertIn('SIN_CONTEXTO_HISTORICO',h['grupos'][0]['motivos'])
        e,caso=self.evaluar()
        self.assertEqual(caso['evaluacion']['suficiencia'],'INSUFICIENTE')
        self.assertEqual(self.client.post(reverse('recomendaciones:generar',args=[e.pk])).status_code,409)
        self.assertFalse(Recomendacion.objects.exists())

    def test_comparacion_periodos_con_lotes_distintos_y_contexto_igual(self):
        for dia,lote,porcentaje in [(3,'lote-referencia',40),(10,'lote-comparado',20)]:
            s=self.capturar(dia=dia,lote=lote);self.medicion_historica(s,porcentaje)
        self.client.force_login(self.admin)
        respuesta=self.client.get(reverse('historico:comparar'),dict(plato='seco_de_pollo',componente='arroz',porcion='estandar',
            referencia_desde='2026-11-01',referencia_hasta='2026-11-07',comparado_desde='2026-11-08',comparado_hasta='2026-11-14'))
        self.assertEqual(respuesta.status_code,200)
        comparacion=respuesta.context['comparacion']
        self.assertEqual(comparacion['referencia']['grupos'][0]['contexto_clave'],comparacion['comparado']['grupos'][0]['contexto_clave'])
        self.assertEqual(comparacion['diferencias']['intensidad_pp'],Decimal(-20))
        self.assertIsNone(comparacion['diferencias']['prevalencia_pp'])

    def test_revision_rectificada_invalida_evaluacion_y_recalcula_indicadores(self):
        s=self.capturar();a,i=self.medicion_historica(s)
        e,_=self.evaluar();snapshot=deepcopy(e.snapshot);contexto=deepcopy(s.contexto_snapshot)
        self.client.force_login(self.cocina)
        respuesta=self.client.post(reverse('analisis:revisar',args=[a.pk,i.pk]),dict(decision='RECHAZADO',motivo='Rectificación de ensayo',version_esperada=1))
        self.assertEqual(respuesta.status_code,302)
        self.comprobar_obsoleta(e,snapshot)
        datos=self.historico()
        self.assertEqual(datos['resumen']['aptos'],0);self.assertEqual(datos['resumen']['motivos'],{'RECHAZADO':1})
        nuevo,caso=self.evaluar();self.assertNotEqual(nuevo.pk,e.pk)
        self.assertTrue(caso['evaluacion']['vigente']);self.assertEqual(caso['evaluacion']['resumen']['aptos'],0)
        self.assertEqual(i.revisiones.count(),2)
        s.refresh_from_db();self.assertEqual(s.contexto_snapshot,contexto)

    def test_analisis_nuevo_pendiente_no_hereda_revision_y_desactualiza_evaluacion(self):
        s=self.capturar();a,_=self.medicion_historica(s)
        e,_=self.evaluar();snapshot=deepcopy(e.snapshot)
        nuevo,intento,creado=analisis_services.solicitar_analisis(servicio=s,solicitante=self.cocina,
            version_modelo='oraculo-nueva-version-test',version_configuracion=a.version_configuracion,origen='REAL')
        self.assertTrue(creado);self.assertEqual(intento.estado,'PENDIENTE');self.assertNotEqual(nuevo.pk,a.pk)
        self.comprobar_obsoleta(e,snapshot)
        datos=self.historico();self.assertEqual(datos['resumen']['aptos'],0)
        self.assertEqual(datos['resumen']['motivos'],{'INTENTO_NO_COMPLETADO':1})
        self.assertFalse(intento.revisiones.exists())

    def test_anular_servicio_incompleto_desactualiza_evaluacion_sin_reescribir_historia(self):
        s=self.capturar(retorno=False)
        e,_=self.evaluar();snapshot=deepcopy(e.snapshot);contexto=deepcopy(s.contexto_snapshot)
        self.client.force_login(self.admin)
        respuesta=self.client.post(reverse('captura:anular_servicio',args=[s.pk]),dict(motivo='Anulación de ensayo',confirmar=True))
        self.assertEqual(respuesta.status_code,302)
        self.comprobar_obsoleta(e,snapshot)
        datos=self.historico();self.assertEqual(datos['resumen']['motivos'],{'ANULADO':1})
        s.refresh_from_db();self.assertEqual(s.contexto_snapshot,contexto)

    def test_cambio_de_lote_invalida_evaluacion_aunque_no_cambie_grupo(self):
        s=self.capturar();self.medicion_historica(s)
        e,_=self.evaluar();snapshot=deepcopy(e.snapshot);clave=s.contexto_clave
        # Emula una corrección de fuente en BD de test, no un endpoint de edición
        # nuevo ni una instrucción para modificar datos operativos.
        contexto=deepcopy(s.contexto_snapshot);contexto['lote_preparacion']='lote-corregido-test'
        Servicio.objects.filter(pk=s.pk).update(contexto_snapshot=contexto)
        datos=self.historico();self.assertEqual(datos['grupos'][0]['contexto_clave'],clave)
        self.assertEqual(datos['indicadores']['intensidad'],Decimal(25))
        self.comprobar_obsoleta(e,snapshot)

    def test_retencion_de_fotos_no_borra_medicion_ni_invalida_snapshot_confirmado(self):
        s=self.capturar();self.medicion_historica(s)
        e,caso=self.evaluar();snapshot=deepcopy(e.snapshot)
        antes=self.historico()
        for foto in s.fotografias.all():
            storage.eliminar(foto.clave_archivo,backend=foto.backend)
            FotografiaServicio.objects.filter(pk=foto.pk).update(eliminada_en=timezone.now())
        despues=self.historico();self.assertEqual(despues,antes)
        self.client.force_login(self.admin)
        respuesta=self.client.get(reverse('recomendaciones:evaluacion',args=[e.pk]))
        self.assertTrue(respuesta.context['caso']['evaluacion']['vigente'])
        e.refresh_from_db();self.assertEqual(e.snapshot,snapshot)
