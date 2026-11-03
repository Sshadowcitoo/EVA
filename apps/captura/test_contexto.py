"""Instantáneas de contexto y comparación real, sin reconstruir registros antiguos."""
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.catalogo.models import Plato, TipoPorcion
from apps.historico import services as historico
from apps.historico.test_dominio_historico import BaseHistorico
from apps.recomendaciones import services as recomendaciones
from apps.recomendaciones.test_dominio_recomendaciones import CONFIG
from . import contexto, services
from .forms import ServicioForm
from .models import Servicio, Bandeja
from .protocolo import CRITERIOS

ZONA = ZoneInfo('America/Guayaquil')
DATOS = dict(sede='principal', modalidad='mesa', lote_preparacion='PREP-01')


class ContextoTests(BaseHistorico):
    def agregar_contexto_fixture(self, servicio, analisis, lote='PREP-01', modalidad='mesa'):
        Servicio.objects.filter(pk=servicio.pk).update(contexto_snapshot=contexto.preparar(dict(DATOS,lote_preparacion=lote,modalidad=modalidad)))
        servicio.refresh_from_db()
        contexto.fijar_servido(servicio, analisis.foto_servido)
        servicio.refresh_from_db()

    def test_servicio_nuevo_captura_automatica_y_retorno_no_reclasifica(self):
        bandeja=Bandeja.objects.create(numero=123)
        servicio=Servicio.registrar(plato=Plato.objects.get(codigo='seco_de_pollo'),
            porcion=TipoPorcion.objects.get(codigo='estandar'),usuario=self.registro,bandeja=bandeja,datos_contexto=DATOS)
        self.assertEqual(servicio.contexto_clave,'')
        def capturar(etapa,fecha):
            with patch('django.utils.timezone.now',return_value=fecha):
                return services.registrar_captura(servicio=servicio,etapa=etapa,clave_archivo=f'fixture/{etapa}.png',
                    tipo_contenido='image/png',tamano_bytes=10,ancho=4,alto=4,autor=self.registro,checklist=dict.fromkeys(CRITERIOS,True))
        capturar('SERVIDO',datetime(2026,10,3,12,30,tzinfo=ZONA))
        servicio.refresh_from_db();original=deepcopy(servicio.contexto_snapshot)
        self.assertTrue(contexto.clave_historica(servicio))
        self.assertEqual(original['franja']['nombre'],'12:00–12:59')
        self.assertEqual(original['lote_preparacion'],'prep-01')
        capturar('RETORNO',datetime(2026,10,3,14,30,tzinfo=ZONA))
        servicio.refresh_from_db();self.assertEqual(servicio.contexto_snapshot,original)

    def test_registros_anteriores_y_datos_incompletos_no_se_inventan(self):
        s,a,_=self.caso()
        contexto.fijar_servido(s,a.foto_servido)
        s.refresh_from_db()
        self.assertEqual(s.contexto_snapshot,{})
        self.assertIsNone(contexto.clave_historica(s))
        with self.assertRaises(ValidationError):contexto.preparar(dict(sede='principal'))
        self.assertFalse(ServicioForm(dict(plato=Plato.objects.get(codigo='seco_de_pollo').pk,
            tipo_porcion=TipoPorcion.objects.get(codigo='estandar').pk,sede='principal')).is_valid())

    def test_configuracion_nueva_no_modifica_snapshot(self):
        s,a,_=self.caso();self.agregar_contexto_fixture(s,a)
        clave=s.contexto_clave
        config=deepcopy(settings.EVA_CONTEXTO_SERVICIO)
        config.update(version='otro-contexto',franja_minutos=120)
        with override_settings(EVA_CONTEXTO_SERVICIO=config):
            self.assertEqual(contexto.clave_historica(s),clave)
            self.assertEqual(contexto.preparar(DATOS)['franja_minutos'],120)

    @override_settings(EVA_HISTORICO_CRITERIOS=dict(version='fixture',aprobada=True,presencia_t=20))
    def test_periodos_con_lotes_distintos_y_contexto_igual_se_comparan(self):
        primero,a,_=self.caso(40,fecha=datetime(2026,10,3,12,tzinfo=ZONA))
        segundo,b,_=self.caso(20,fecha=datetime(2026,10,10,12,tzinfo=ZONA))
        self.agregar_contexto_fixture(primero,a,'prep-uno');self.agregar_contexto_fixture(segundo,b,'prep-dos')
        self.assertEqual(primero.contexto_clave,segundo.contexto_clave)
        f=dict(plato='seco_de_pollo',componente='arroz')
        comparacion=historico.comparar_periodos(dict(f,desde='2026-10-01',hasta='2026-10-07'),dict(f,desde='2026-10-08',hasta='2026-10-14'))
        self.assertTrue(comparacion['comparable'])
        self.assertEqual(comparacion['diferencias']['intensidad_pp'],-20)
        self.assertTrue(historico.opciones_historico()['contexto_disponible'])
        self.agregar_contexto_fixture(segundo,b,'prep-dos',modalidad='autoservicio')
        comparacion=historico.comparar_periodos(dict(f,desde='2026-10-01',hasta='2026-10-07'),dict(f,desde='2026-10-08',hasta='2026-10-14'))
        self.assertFalse(comparacion['comparable'])
        self.assertIsNone(comparacion['diferencias']['intensidad_pp'])

    def test_snapshot_alterado_no_certifica_contexto(self):
        s,a,_=self.caso();self.agregar_contexto_fixture(s,a)
        s.contexto_snapshot['sede']['codigo']='otra'
        self.assertIsNone(contexto.clave_historica(s))

    def test_post_con_contexto_guarda_datos_sin_aceptar_nombre_desde_cliente(self):
        self.client.force_login(self.registro)
        response=self.client.post(reverse('captura:nueva_bandeja'),dict(plato=Plato.objects.get(codigo='seco_de_pollo').pk,
            tipo_porcion=TipoPorcion.objects.get(codigo='estandar').pk,**DATOS,establecimiento='inventado'))
        self.assertEqual(response.status_code,302)
        s=Servicio.objects.get()
        self.assertEqual(s.contexto_snapshot['establecimiento']['nombre'],'La Mesa Costeña')
        self.assertIsNone(s.contexto_snapshot['franja'])

    @override_settings(EVA_HISTORICO_CRITERIOS=dict(version='fixture-t20',aprobada=True,presencia_t=20))
    def test_recomendacion_con_contexto_real_y_lotes_sin_dobles_de_servicio(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        admin=get_user_model().objects.create_user('admin_contexto')
        admin.groups.add(Group.objects.get(name='Administración'))
        for i in range(2):
            s,a,_=self.caso(25);self.agregar_contexto_fixture(s,a,f'prep-{i}')
        config=deepcopy(CONFIG);config['reglas']['lotes_minimos']=2
        with override_settings(EVA_RECOMENDACIONES_CRITERIOS=config):
            caso=recomendaciones.evaluar_evidencia(dict(plato='seco_de_pollo',componente='arroz',desde='2026-10-01',hasta='2026-10-07'),'fixture-v1',admin)
            self.assertEqual(caso['evaluacion']['suficiencia'],'SUFICIENTE')
            self.assertTrue(next(c for c in caso['evaluacion']['chequeos'] if c['codigo']=='PREPARACIONES')['cumple'])
            respuesta=recomendaciones.generar_recomendacion(caso['evaluacion']['id'],admin)
            self.assertIsNotNone(respuesta['recomendacion'])
            config['reglas']['lotes_minimos']=3
        with override_settings(EVA_RECOMENDACIONES_CRITERIOS=config):
            caso=recomendaciones.evaluar_evidencia(dict(plato='seco_de_pollo',componente='arroz',desde='2026-10-01',hasta='2026-10-07'),'fixture-v1',admin)
            self.assertEqual(caso['evaluacion']['suficiencia'],'INSUFICIENTE')
