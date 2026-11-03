from io import BytesIO
import json
from uuid import uuid4

from django.test import override_settings
from PIL import Image, ImageDraw
from apps.historico.test_dominio_historico import BaseHistorico
from visual_service.server import aplicacion
from . import motor


class AdaptadorVisualTests(BaseHistorico):
    def test_cliente_endpoint_y_validador_comparten_protocolo(self):
        servicio, analisis, intento = self.caso()
        componentes = list(servicio.composicion.all())
        metadata = dict(schema_version=1,request_id=str(intento.pk),servicio_id=str(servicio.pk),
            version_modelo=analisis.version_modelo,version_configuracion=analisis.version_configuracion,
            origen='REAL',componentes=[dict(id=str(c.pk),codigo=c.componente_codigo) for c in componentes])
        salida=BytesIO();Image.new('RGB',(4,4),'red').save(salida,'PNG');contenido=salida.getvalue()
        cuerpo,boundary=motor._multipart(metadata,dict(SERVIDO=(analisis.foto_servido,contenido),RETORNO=(analisis.foto_retorno,contenido)))
        def predictor(_):
            respuesta=[]
            for codigo,caja in [('arroz',(0,0,1,3)),('pollo',(2,0,2,3)),('maduro',(3,0,3,3))]:
                imagen=Image.new('L',(4,4));ImageDraw.Draw(imagen).rectangle(caja,fill=255)
                respuesta.append(dict(codigo=codigo,confianza=.9,mascara=imagen))
            return respuesta
        token='token-interno-fixture-123456'
        app=aplicacion(predictor,token,analisis.version_modelo,identidad_verificada=True)
        env=dict(PATH_INFO='/v1/analizar-par',REQUEST_METHOD='POST',HTTP_AUTHORIZATION='Bearer '+token,
                 CONTENT_TYPE='multipart/form-data; boundary='+boundary,CONTENT_LENGTH=str(len(cuerpo)))
        env['wsgi.input']=BytesIO(cuerpo);estados=[]
        respuesta=json.loads(b''.join(app(env,lambda status,headers:estados.append(status))))
        self.assertEqual(estados,['200 OK'],respuesta)
        criterios=dict(version=analisis.version_configuracion,aprobada=True,comparabilidad_aprobada=True,
                        umbrales=dict(arroz=.8,pollo=.8,maduro=.8))
        with override_settings(EVA_ANALISIS_CRITERIOS=criterios):
            resultados,archivos=motor.validar(respuesta,intento,componentes)
        self.assertEqual(len(resultados),3);self.assertEqual(len(archivos),6)
        self.assertTrue(all(r['comparable'] for r in resultados))
        self.assertEqual(sum(r['area_inicial'] for r in resultados),16)
