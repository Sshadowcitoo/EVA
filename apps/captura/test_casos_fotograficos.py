import hashlib
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase

from .management.commands.cargar_casos_fotograficos import leer_casos


class CasosFotograficosTests(SimpleTestCase):
    def test_operacion_rechaza_carga_fuera_de_presentacion(self):
        with self.assertRaisesMessage(CommandError, 'presentación aislada'):
            call_command('cargar_casos_fotograficos', manifiesto=Path('no-existe.json'), stdout=StringIO())

    def test_manifiesto_verifica_huellas_y_no_lee_fuera_del_paquete(self):
        with TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            foto = raiz / 'foto.png'
            foto.write_bytes(b'contenido privado de prueba')
            huella = hashlib.sha256(foto.read_bytes()).hexdigest()
            caso = dict(clave='prueba', plato='seco_de_pollo', nota='Fotografías de control.',
                        servido='foto.png', retorno='foto.png', servido_sha256=huella, retorno_sha256=huella)
            manifiesto = raiz / 'casos.json'
            manifiesto.write_text(json.dumps(dict(schema_version=1, casos=[caso])))
            self.assertEqual(leer_casos(manifiesto)[0]['servido'], foto)
            caso['servido_sha256'] = '0' * 64
            manifiesto.write_text(json.dumps(dict(schema_version=1, casos=[caso])))
            with self.assertRaisesMessage(CommandError, 'no coincide'):
                leer_casos(manifiesto)
            caso['servido'] = '../foto.png'
            manifiesto.write_text(json.dumps(dict(schema_version=1, casos=[caso])))
            with self.assertRaisesMessage(CommandError, 'dentro del paquete'):
                leer_casos(manifiesto)
