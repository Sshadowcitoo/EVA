import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from threading import Thread
from wsgiref.simple_server import make_server

from .production import configuracion, create_app, comprobar
from .inference import EntradaInvalida
from .server import aplicacion, SinLogAcceso


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.pesos = Path(self.temporal.name) / 'modelo.pt'
        self.pesos.write_bytes(b'fixture-sin-modelo-real')
        self.version = 'sha256-' + hashlib.sha256(self.pesos.read_bytes()).hexdigest()[:40]
        self.env = dict(EVA_VISUAL_TOKEN='t' * 32, EVA_VISUAL_PESOS=str(self.pesos),
                        EVA_VISUAL_VERSION_MODELO=self.version,
                        EVA_VISUAL_ENDPOINT='http://127.0.0.1:8765/v1/analizar-par')
        self.parche = patch.dict(os.environ, self.env)
        self.parche.start()
        self.addCleanup(self.parche.stop)

    def test_pesos_y_version_deben_coincidir_antes_de_cargar(self):
        self.assertEqual(configuracion()[2], self.version)
        self.pesos.write_bytes(b'pesos-distintos')
        with patch('visual_service.production.PredictorYOLO') as predictor:
            with self.assertRaises(EntradaInvalida):
                create_app()
            predictor.assert_not_called()

    def test_no_admite_endpoint_remoto_ni_token_corto(self):
        for cambios in ({'EVA_VISUAL_ENDPOINT': 'https://otro.test/v1/analizar-par'},
                        {'EVA_VISUAL_TOKEN': 'corto'}, {'EVA_VISUAL_PESOS': 'ausente.pt'}):
            with self.subTest(cambios=cambios), patch.dict(os.environ, cambios):
                with self.assertRaises(EntradaInvalida):
                    configuracion()

    def test_factory_no_aprueba_geometria(self):
        with patch('visual_service.production.PredictorYOLO'), patch('visual_service.production.aplicacion') as app:
            create_app()
            self.assertNotIn('identidad_verificada', app.call_args.kwargs)

    def test_salud_privada_no_ejecuta_inferencia(self):
        def predictor(_):
            self.fail('La comprobación de disponibilidad no debe inferir.')
        app = aplicacion(predictor, self.env['EVA_VISUAL_TOKEN'], self.version)
        for autorizado, esperado in ((False, '401'), (True, '200')):
            estados = []
            env = dict(PATH_INFO='/v1/salud', REQUEST_METHOD='GET', **{'wsgi.input': BytesIO()})
            if autorizado:
                env['HTTP_AUTHORIZATION'] = 'Bearer ' + self.env['EVA_VISUAL_TOKEN']
            cuerpo = b''.join(app(env, lambda estado, headers: estados.append(estado)))
            self.assertTrue(estados[0].startswith(esperado))
            if autorizado:
                self.assertEqual(json.loads(cuerpo)['version_modelo'], self.version)

    def test_comprobacion_rechaza_otro_modelo_y_cuerpo_excesivo(self):
        for datos in (b'{"estado":"LISTO","version_modelo":"otra"}', b'x' * 4097):
            with patch('visual_service.production.build_opener') as opener:
                opener.return_value.open.return_value.__enter__.return_value.read.return_value = datos
                with self.assertRaises(EntradaInvalida):
                    comprobar()

    def test_salud_http_real_y_autenticacion(self):
        from urllib.error import HTTPError
        from urllib.request import Request, build_opener, ProxyHandler
        app = aplicacion(lambda _: self.fail('No ejecutar inferencia.'), self.env['EVA_VISUAL_TOKEN'], self.version)
        with make_server('127.0.0.1', 0, app, handler_class=SinLogAcceso) as servidor:
            hilo = Thread(target=servidor.serve_forever, daemon=True)
            hilo.start()
            try:
                url = f'http://127.0.0.1:{servidor.server_port}/v1/salud'
                opener = build_opener(ProxyHandler({}))
                with self.assertRaises(HTTPError) as error:
                    opener.open(url, timeout=3)
                self.assertEqual(error.exception.code, 401)
                peticion = Request(url, headers={'Authorization': 'Bearer ' + self.env['EVA_VISUAL_TOKEN']})
                with opener.open(peticion, timeout=3) as respuesta:
                    self.assertEqual(json.load(respuesta), dict(estado='LISTO', version_modelo=self.version))
            finally:
                servidor.shutdown()
                hilo.join(timeout=3)


if __name__ == '__main__':
    unittest.main()
