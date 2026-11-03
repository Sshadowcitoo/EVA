from io import BytesIO
import json
from pathlib import Path
import unittest
from uuid import uuid4
from PIL import Image, ImageDraw

from .inference import EntradaInvalida, PredictorYOLO, analizar
from .server import aplicacion


def foto(color):
    salida=BytesIO();Image.new('RGB',(20,20),color).save(salida,'PNG');return salida.getvalue()


def mascara(caja):
    imagen=Image.new('L',(20,20));ImageDraw.Draw(imagen).rectangle(caja,fill=255);return imagen


class InferenciaTests(unittest.TestCase):
    def setUp(self):
        self.metadata=dict(schema_version=1,request_id=str(uuid4()),servicio_id=str(uuid4()),
            version_modelo='modelo-test',version_configuracion='criterios-test',origen='REAL',
            componentes=[dict(id=str(uuid4()),codigo='arroz')])
        self.servido,self.retorno=foto('red'),foto('green')

    def predictor(self, imagen):
        caja=(1,1,10,10) if imagen.getpixel((0,0))[0] else (1,1,5,5)
        return [dict(codigo='arroz',confianza=.9,mascara=mascara(caja))]

    def analizar(self,predictor=None,**kwargs):
        return analizar(self.metadata,self.servido,self.retorno,predictor or self.predictor,version_modelo='modelo-test',**kwargs)

    def test_mascaras_areas_y_geometria_no_se_aprueban_por_tamano(self):
        dto=self.analizar()
        self.assertFalse(dto['componentes'][0]['comparable'])
        self.assertEqual(dto['componentes'][0]['area_inicial'],100)
        self.assertEqual(dto['componentes'][0]['area_residual'],25)
        self.assertEqual(len(dto['componentes'][0]['mascaras']),2)
        self.assertTrue(self.analizar(identidad_verificada=True)['componentes'][0]['comparable'])

    def test_sin_deteccion_de_retorno_no_inventa_cero(self):
        def predictor(imagen):
            return self.predictor(imagen) if imagen.getpixel((0,0))[0] else []
        dto=self.analizar(predictor)['componentes'][0]
        self.assertIsNone(dto['area_residual']);self.assertIsNone(dto['confianza'])
        self.assertFalse(dto['comparable'])

    def test_solapamientos_no_publican_mascaras_ambiguas(self):
        self.metadata['componentes'].append(dict(id=str(uuid4()),codigo='pollo'))
        def predictor(_):
            return [dict(codigo=c,confianza=.9,mascara=mascara((1,1,5,5))) for c in ('arroz','pollo')]
        dto=self.analizar(predictor,identidad_verificada=True)
        self.assertTrue(all(c['mascaras']==[] and not c['comparable'] for c in dto['componentes']))

    def test_modelo_ajeno_version_invalida_y_numeros_no_finitos(self):
        with self.assertRaises(EntradaInvalida):
            PredictorYOLO(Path('no-existe.pt'))
        self.metadata['version_modelo']='otro'
        with self.assertRaises(EntradaInvalida):self.analizar()
        self.metadata['version_modelo']='modelo-test'
        with self.assertRaises(EntradaInvalida):
            self.analizar(lambda _: [dict(codigo='arroz',confianza=float('nan'),mascara=mascara((1,1,5,5)))])

    def test_origen_simulado_nunca_se_promueve_a_real(self):
        self.metadata['origen']='SIMULADO'
        self.assertEqual(self.analizar()['origen'],'SIMULADO')

    def test_endpoint_autenticado_multipart_sin_red(self):
        token='token-interno-de-prueba-123456'
        app=aplicacion(self.predictor,token,'modelo-test')
        boundary='limite-test'
        partes=[]
        for nombre,datos in [('metadata',json.dumps(self.metadata).encode()),('servido',self.servido),('retorno',self.retorno)]:
            partes.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{nombre}"\r\n\r\n'.encode()+datos+b'\r\n')
        cuerpo=b''.join(partes)+f'--{boundary}--\r\n'.encode()
        env=dict(PATH_INFO='/v1/analizar-par',REQUEST_METHOD='POST',HTTP_AUTHORIZATION='Bearer '+token,
                 CONTENT_TYPE='multipart/form-data; boundary='+boundary,CONTENT_LENGTH=str(len(cuerpo)))
        def ejecutar(cambios):
            estado=[];e=dict(env,**cambios);e['wsgi.input']=BytesIO(cuerpo)
            respuesta=b''.join(app(e,lambda status,headers:estado.append(status)))
            return estado[0],json.loads(respuesta)
        self.assertEqual(ejecutar({})[0],'200 OK')
        self.assertEqual(ejecutar(dict(HTTP_AUTHORIZATION='Bearer otro'))[0],'401 Unauthorized')
        self.assertEqual(ejecutar(dict(REQUEST_METHOD='GET'))[0],'405 Method Not Allowed')
        self.assertEqual(ejecutar(dict(CONTENT_LENGTH='999999999'))[0],'422 Unprocessable Entity')
        self.assertEqual(ejecutar(dict(CONTENT_TYPE='multipart/form-data; boundary=otro'))[0],'422 Unprocessable Entity')
