import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from django.conf import settings
from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory, override_settings

from ops.presentacion.aislamiento import lote_activo, solo_loopback


class PresentacionPublicaTests(SimpleTestCase):
    def importar(self, raiz, clave):
        env = {k: v for k, v in os.environ.items() if not k.startswith('EVA_PRESENTACION_')}
        env.update(EVA_PRESENTACION_PUBLICA='1', EVA_PRESENTACION_HOST='example.invalid',
                   EVA_PRESENTACION_SECRET_KEY=clave, EVA_PRESENTACION_LOTE='prueba',
                   EVA_PRESENTACION_RAIZ=str(raiz))
        codigo = "from config import settings_presentacion as s; import json; print(json.dumps([s.DEBUG,s.FORCE_SCRIPT_NAME,s.SESSION_COOKIE_NAME,s.CSRF_COOKIE_NAME,s.SESSION_COOKIE_SECURE,s.CSRF_COOKIE_SECURE,s.DATABASES['default']['NAME'].__str__()]))"
        return subprocess.run([sys.executable, '-c', codigo], cwd=settings.BASE_DIR,
                              env=env, text=True, capture_output=True, timeout=20)

    def test_publicacion_exige_clave_y_separa_base_y_cookies(self):
        with TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            (raiz / '.eva-presentacion').write_text('prueba')
            self.assertNotEqual(self.importar(raiz, '').returncode, 0)
            resultado = self.importar(raiz, 'clave-exclusiva-de-prueba-' * 3)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            valores = json.loads(resultado.stdout)
            self.assertEqual(valores[:6], [False, '/presentacion', 'eva_presentacion_session', 'eva_presentacion_csrf', True, True])
            self.assertEqual(Path(valores[6]), raiz / 'presentacion.sqlite3')

    def test_solo_proxy_local_y_modulo_explicito(self):
        middleware = solo_loopback(lambda request: HttpResponse('ok'))
        fabrica = RequestFactory()
        self.assertEqual(middleware(fabrica.get('/', REMOTE_ADDR='127.0.0.1')).status_code, 200)
        self.assertEqual(middleware(fabrica.get('/', REMOTE_ADDR='203.0.113.10', HTTP_X_FORWARDED_FOR='127.0.0.1')).status_code, 403)
        with override_settings(SETTINGS_MODULE='config.production', EVA_PRESENTACION_LOTE='prueba'):
            self.assertIsNone(lote_activo())
