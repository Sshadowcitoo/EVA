"""Cliente multipart, HTTP local y validador reales; predictor determinista SOLO de test."""
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import time
from urllib.error import HTTPError
from wsgiref.simple_server import make_server

from django.test import override_settings
from PIL import Image, ImageDraw

from apps.captura import storage
from apps.historico.test_dominio_historico import BaseHistorico
from visual_service.server import aplicacion, SinLogAcceso
from . import motor

TOKEN='token-exclusivo-del-test-local-123456'


class CompatibilidadEndpointTests(BaseHistorico):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup)
        config=override_settings(EVA_CAPTURE_PRIVATE_ROOT=Path(temp.name),EVA_STORAGE_BACKEND='local')
        config.enable();self.addCleanup(config.disable)
        self.servicio,self.analisis,self.intento=self.caso()
        for foto,color in [(self.analisis.foto_servido,'red'),(self.analisis.foto_retorno,'green')]:
            salida=BytesIO();Image.new('RGB',(4,4),color).save(salida,'PNG')
            storage.guardar(salida.getvalue(),foto.clave_archivo,tipo_contenido='image/png')

    def predictor(self,imagen):
        objetos=[]
        for codigo,caja in [('arroz',(0,0,1,3)),('pollo',(2,0,2,3)),('maduro',(3,0,3,3))]:
            mascara=Image.new('L',(4,4));ImageDraw.Draw(mascara).rectangle(caja,fill=255)
            objetos.append(dict(codigo=codigo,confianza=.9,mascara=mascara))
        return objetos

    @contextmanager
    def endpoint(self,predictor=None,**opciones):
        app=aplicacion(predictor or self.predictor,TOKEN,self.analisis.version_modelo,**opciones)
        with make_server('127.0.0.1',0,app,handler_class=SinLogAcceso) as server:
            hilo=Thread(target=server.serve_forever,daemon=True);hilo.start()
            try:
                with override_settings(EVA_VISUAL_ENDPOINT=f'http://127.0.0.1:{server.server_port}/v1/analizar-par',EVA_VISUAL_TOKEN=TOKEN,EVA_VISUAL_VERSION_MODELO=self.analisis.version_modelo):
                    yield app
            finally:
                server.shutdown();hilo.join(timeout=5)

    def test_http_cliente_y_validador_con_ids_numericos_y_criterios_sin_aprobar(self):
        with self.endpoint():
            resultados,archivos=motor.llamar(self.intento,time.monotonic()+10)
        self.assertEqual(len(resultados),3);self.assertEqual(len(archivos),6)
        self.assertEqual({r['servicio_componente'].pk for r in resultados},set(self.servicio.composicion.values_list('pk',flat=True)))
        self.assertTrue(all(r['comparable'] is False and r['umbral_confianza'] is None for r in resultados))
        self.assertEqual(sum(r['area_inicial'] for r in resultados),16)

    def test_identidad_del_servidor_no_aprueba_criterios_de_eva(self):
        with self.endpoint(identidad_verificada=True):
            resultados,_=motor.llamar(self.intento,time.monotonic()+10)
        self.assertTrue(all(r['comparable'] is False for r in resultados))

    def test_sin_deteccion_retorno_mantiene_ausencia_y_origen_simulado(self):
        self.analisis.origen='SIMULADO';self.analisis.save(update_fields=['origen'])
        self.intento.analisis=self.analisis
        def predictor(imagen):
            return self.predictor(imagen) if imagen.getpixel((0,0))[0] else []
        with self.endpoint(predictor):
            resultados,archivos=motor.llamar(self.intento,time.monotonic()+10)
        self.assertTrue(all(r['area_residual'] is None and r['confianza'] is None and not r['comparable'] for r in resultados))
        self.assertEqual(len(archivos),3)
        self.analisis.refresh_from_db();self.assertEqual(self.analisis.origen,'SIMULADO')

    def test_autenticacion_y_version_incorrectas_son_rechazos_sin_resultados(self):
        with self.endpoint():
            with override_settings(EVA_VISUAL_TOKEN='otro-token-de-prueba-interno'):
                with self.assertRaises(HTTPError) as error:motor.llamar(self.intento,time.monotonic()+10)
                self.assertEqual(error.exception.code,401)
            self.analisis.version_modelo='version-no-servida';self.intento.analisis=self.analisis
            with self.assertRaises(HTTPError) as error:motor.llamar(self.intento,time.monotonic()+10)
            self.assertEqual(error.exception.code,422)

    def test_fallo_predictor_no_devuelve_exito_ni_expone_detalles(self):
        def predictor(_):raise RuntimeError('Detalle interno que no debe aparecer')
        with self.endpoint(predictor):
            with self.assertLogs('visual_service.server',level='ERROR'):
                with self.assertRaises(HTTPError) as error:motor.llamar(self.intento,time.monotonic()+10)
            self.assertEqual(error.exception.code,503)
            cuerpo=error.exception.read().decode()
            self.assertNotIn('Detalle interno',cuerpo);self.assertNotIn(TOKEN,cuerpo)
