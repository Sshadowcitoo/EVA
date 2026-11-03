"""HTTP y ORM reales de contexto, sin sustituir servicios ni almacenamiento."""
from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from PIL import Image

from apps.catalogo.models import Plato, TipoPorcion
from apps.historico.test_dominio_historico import BaseHistorico
from .models import Servicio, Bandeja, AsignacionBandeja, FotografiaServicio
from .protocolo import CRITERIOS

ZONA=ZoneInfo('America/Guayaquil')
DATOS=dict(sede='principal',modalidad='mesa',lote_preparacion='PREP-HTTP-01')


class ContextoHTTPTests(BaseHistorico):
    def setUp(self):
        self.temporal=TemporaryDirectory();self.addCleanup(self.temporal.cleanup)
        config=override_settings(EVA_STORAGE_BACKEND='local',EVA_CAPTURE_PRIVATE_ROOT=Path(self.temporal.name))
        config.enable();self.addCleanup(config.disable)
        self.client.force_login(self.registro)
        self.campos=dict(plato=Plato.objects.get(codigo='seco_de_pollo').pk,tipo_porcion=TipoPorcion.objects.get(codigo='estandar').pk)

    def datos_foto(self, **extra):
        salida=BytesIO();Image.new('RGB',(4,4),'red').save(salida,'PNG')
        return dict(foto=SimpleUploadedFile('ensayo.png',salida.getvalue(),content_type='image/png'),**dict.fromkeys(CRITERIOS,True),**extra)

    def alta(self, contexto=True, bandeja=False):
        datos={**self.campos,**(DATOS if contexto else dict(sede='',modalidad='',lote_preparacion=''))}
        url=reverse('captura:nueva_bandeja')
        if bandeja:
            b=Bandeja.objects.create(numero=501)
            url=reverse('captura:resolver_bandeja')+'?numero=501'
        response=self.client.post(url,datos)
        self.assertEqual(response.status_code,302)
        return Servicio.objects.latest('fecha_creacion'),response

    def exportar(self,nombre,response):
        destino=os.environ.get('EVA_CONTEXT_VISUAL_DIR')
        if destino:
            ruta=Path(destino);ruta.mkdir(parents=True,exist_ok=True);(ruta/(nombre+'.html')).write_bytes(response.content)

    def test_get_contexto_no_escribe_y_parcial_conserva_campos(self):
        url=reverse('captura:nueva_bandeja')
        self.exportar('alta-contexto',self.client.get(url))
        for seleccion in [dict(sede='principal'),dict(modalidad='mesa'),dict(lote_preparacion='PREP-HTTP-01'),dict(sede='principal',modalidad='mesa')]:
            response=self.client.post(url,{**self.campos,**seleccion})
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.context['form'].errors)
            self.assertFalse(Servicio.objects.exists())
            for campo,valor in seleccion.items():self.assertEqual(response.context['form'][campo].value(),valor)
        self.exportar('contexto-incompleto',response)

    def test_sede_modalidad_lote_invalidos_no_asignan_bandeja(self):
        Bandeja.objects.create(numero=510)
        url=reverse('captura:resolver_bandeja')+'?numero=510'
        for cambios in [dict(sede='desconocida'),dict(modalidad='inventada'),dict(lote_preparacion='<script>'),dict(lote_preparacion='x'*65),dict(modalidad='')]:
            response=self.client.post(url,{**self.campos,**DATOS,**cambios})
            self.assertEqual(response.status_code,200);self.assertTrue(response.context['form'].errors)
            self.assertFalse(Servicio.objects.exists());self.assertFalse(AsignacionBandeja.objects.exists())
        self.assertContains(self.client.post(url,{**self.campos,**DATOS,'lote_preparacion':'<script>'}),'&lt;script&gt;')

    def test_guardado_ambas_rutas_usa_configuracion_y_no_franja_del_post(self):
        for numero,nombre in [(None,'captura:nueva_bandeja'),(520,'captura:resolver_bandeja')]:
            url=reverse(nombre)
            if numero:Bandeja.objects.create(numero=numero);url+='?numero='+str(numero)
            response=self.client.post(url,{**self.campos,**DATOS,'establecimiento':'intruso','franja':'00:00','fecha_servido':'2000-01-01','contexto_clave':'falsa'})
            self.assertEqual(response.status_code,302)
            s=Servicio.objects.latest('fecha_creacion');snapshot=s.contexto_snapshot
            self.assertEqual(snapshot['establecimiento']['nombre'],'La Mesa Costeña')
            self.assertEqual(snapshot['sede']['codigo'],'principal');self.assertEqual(snapshot['modalidad']['codigo'],'mesa')
            self.assertEqual(snapshot['lote_preparacion'],'prep-http-01')
            self.assertIsNone(snapshot['franja']);self.assertIsNone(snapshot['fecha_servido']);self.assertEqual(s.contexto_clave,'')
            self.assertEqual(s.asignaciones.count(),1 if numero else 0)
            self.exportar('guardado-pendiente-franja',self.client.get(reverse('captura:confirmacion',args=[s.pk])))

    def test_franja_automatica_ecuador_en_servido_rechaza_hora_del_cliente(self):
        s,_=self.alta(bandeja=True)
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,4,4,59,tzinfo=timezone.utc)):
            response=self.client.post(reverse('captura:foto_servido',args=[s.pk]),self.datos_foto(franja='12:00',fecha_servido='2000-01-01'))
        self.assertEqual(response.status_code,302);s.refresh_from_db()
        foto=s.fotografias.get(etapa='SERVIDO')
        self.assertEqual(s.contexto_snapshot['franja']['codigo'],'m1380_1440')
        self.assertEqual(datetime.fromisoformat(s.contexto_snapshot['fecha_servido']),foto.fecha)
        self.assertEqual(datetime.fromisoformat(s.contexto_snapshot['fecha_servido']).day,3)
        self.assertTrue(s.contexto_clave)

    def test_foto_invalida_no_fija_franja_y_reenvio_no_la_cambia(self):
        s,_=self.alta(bandeja=True);url=reverse('captura:foto_servido',args=[s.pk])
        response=self.client.post(url,dict(foto=SimpleUploadedFile('mal.png',b'no es imagen',content_type='image/png'),**dict.fromkeys(CRITERIOS,True)))
        self.assertEqual(response.status_code,200);s.refresh_from_db();self.assertEqual(s.contexto_clave,'');self.assertIsNone(s.contexto_snapshot['franja'])
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,3,12,59,tzinfo=ZONA)):
            self.assertEqual(self.client.post(url,self.datos_foto()).status_code,302)
        s.refresh_from_db();snapshot=deepcopy(s.contexto_snapshot)
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,3,14,1,tzinfo=ZONA)):
            self.client.post(url,self.datos_foto())
        s.refresh_from_db();self.assertEqual(s.contexto_snapshot,snapshot);self.assertEqual(s.fotografias.filter(etapa='SERVIDO').count(),1)

    def test_retorno_no_modifica_contexto_ni_lote_con_configuracion_nueva(self):
        s,_=self.alta(bandeja=True)
        with patch('django.utils.timezone.now',return_value=datetime(2026,11,3,12,30,tzinfo=ZONA)):
            self.assertEqual(self.client.post(reverse('captura:foto_servido',args=[s.pk]),self.datos_foto()).status_code,302)
        s.refresh_from_db();snapshot=deepcopy(s.contexto_snapshot);clave=s.contexto_clave
        config=deepcopy(settings.EVA_CONTEXTO_SERVICIO);config['version']='version-posterior-test';config['sedes'][0]['nombre']='Nombre posterior'
        with override_settings(EVA_CONTEXTO_SERVICIO=config):
            consulta=self.client.get(reverse('captura:buscar_retorno')+'?numero=501')
            self.assertContains(consulta,'prep-http-01')
            for campo in ('sede','modalidad','lote_preparacion'):
                self.assertNotContains(consulta,'name="'+campo+'"')
            self.assertNotContains(consulta,'Establecimiento: .')
            self.exportar('confirmar-retorno',consulta)
            self.assertEqual(self.client.post(reverse('captura:buscar_retorno')+'?numero=501',dict(confirmar=True,**dict(DATOS,modalidad='autoservicio',lote_preparacion='otra'))).status_code,302)
            self.exportar('foto-retorno',self.client.get(reverse('captura:foto_retorno',args=[s.pk])))
            with patch('django.utils.timezone.now',return_value=datetime(2026,11,3,15,30,tzinfo=ZONA)):
                response=self.client.post(reverse('captura:foto_retorno',args=[s.pk]),self.datos_foto(**dict(DATOS,modalidad='autoservicio',lote_preparacion='otra')))
        self.assertEqual(response.status_code,302);s.refresh_from_db()
        self.assertEqual(s.contexto_snapshot,snapshot);self.assertEqual(s.contexto_clave,clave)
        self.assertEqual(s.estado_captura,'PAR_COMPLETO');self.assertEqual(s.fotografias.count(),2)
        self.assertFalse(s.asignaciones.filter(fin__isnull=True).exists())
        self.exportar('par-completo-contexto',self.client.get(reverse('captura:foto_retorno',args=[s.pk])))

    def test_registro_sin_contexto_y_anterior_no_se_reconstruyen(self):
        s,response=self.alta(contexto=False)
        self.assertEqual(s.contexto_snapshot,{});self.assertEqual(s.contexto_clave,'')
        self.assertContains(self.client.get(response.url),'Sin contexto histórico')
        self.assertEqual(self.client.get(reverse('captura:foto_servido',args=[s.pk])).status_code,404)
        s,_=self.alta(contexto=False,bandeja=True)
        for etapa,nombre in [('SERVIDO','captura:foto_servido'),('RETORNO','captura:foto_retorno')]:
            self.assertEqual(self.client.post(reverse(nombre,args=[s.pk]),self.datos_foto()).status_code,302)
        s.refresh_from_db();self.assertEqual(s.contexto_snapshot,{});self.assertEqual(s.contexto_clave,'')
        antiguo,_,_=self.caso()
        detalle=self.client.get(reverse('captura:foto_retorno',args=[antiguo.pk]))
        self.assertContains(detalle,'Sin contexto histórico')
        antiguo.refresh_from_db();self.assertEqual(antiguo.contexto_snapshot,{})
        self.exportar('registro-anterior-sin-contexto',detalle)

    def test_permisos_y_csrf_del_registro_y_captura(self):
        s,_=self.alta();antes=Servicio.objects.count()
        self.client.force_login(self.cocina)
        for url in [reverse('captura:nueva_bandeja'),reverse('captura:foto_servido',args=[s.pk])]:
            self.assertEqual(self.client.post(url,{**self.campos,**DATOS}).status_code,403)
        cliente=Client(enforce_csrf_checks=True);cliente.force_login(self.registro)
        self.assertEqual(cliente.post(reverse('captura:nueva_bandeja'),{**self.campos,**DATOS}).status_code,403)
        self.assertEqual(cliente.post(reverse('captura:foto_servido',args=[s.pk]),self.datos_foto()).status_code,403)
        self.assertEqual(Servicio.objects.count(),antes);self.assertFalse(FotografiaServicio.objects.exists())

    def test_propuesta_experimental_no_se_activa(self):
        self.assertFalse(settings.EVA_ANALISIS_CRITERIOS['aprobada'])
        self.assertFalse(settings.EVA_ANALISIS_CRITERIOS['comparabilidad_aprobada'])
        self.assertFalse(settings.EVA_HISTORICO_CRITERIOS['aprobada'])
        self.assertFalse(settings.EVA_RECOMENDACIONES_CRITERIOS['aprobada'])
        self.assertFalse(settings.EVA_VISUAL_ENDPOINT)

    def test_limites_de_franja_local_usan_la_hora_exacta_del_servido(self):
        for i,(hora,minuto,codigo) in enumerate([(0,0,'m0000_0060'),(12,59,'m0720_0780'),(13,0,'m0780_0840')]):
            numero=700+i;Bandeja.objects.create(numero=numero)
            response=self.client.post(reverse('captura:resolver_bandeja')+'?numero='+str(numero),{**self.campos,**DATOS})
            self.assertEqual(response.status_code,302)
            servicio=Servicio.objects.latest('fecha_creacion')
            with patch('django.utils.timezone.now',return_value=datetime(2026,11,3,hora,minuto,tzinfo=ZONA)):
                self.assertEqual(self.client.post(response.url,self.datos_foto()).status_code,302)
            servicio.refresh_from_db()
            self.assertEqual(servicio.contexto_snapshot['franja']['codigo'],codigo)
