import base64
import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
from unittest.mock import patch

import boto3
from botocore.response import StreamingBody
from botocore.stub import Stubber
from django.test import SimpleTestCase, override_settings

from . import storage


@override_settings(EVA_STORAGE_BACKEND='s3', EVA_S3_BUCKET='eva-pruebas', EVA_S3_REGION='us-east-2', EVA_S3_PREFIX='eva/capturas/')
class S3StorageTests(SimpleTestCase):
    def setUp(self):
        # Credenciales ficticias solo para construir el cliente de Stubber; nunca hay red.
        client = boto3.client('s3', region_name='us-east-2', aws_access_key_id='testing', aws_secret_access_key='testing')
        self.stub = Stubber(client)
        self.stub.activate()
        self.addCleanup(self.stub.deactivate)
        patcher = patch('apps.captura.storage._cliente_s3', return_value=client)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.key = 'eva/capturas/servicios/prueba/foto.png'
        self.content = b'bytes-de-prueba'
        self.digest = hashlib.sha256(self.content).hexdigest()

    def parametros_put(self):
        return dict(Bucket='eva-pruebas', Key=self.key, Body=self.content, ContentType='image/png',
                    ServerSideEncryption='AES256', IfNoneMatch='*', Metadata={'sha256': self.digest},
                    ChecksumSHA256=base64.b64encode(bytes.fromhex(self.digest)).decode())

    def test_guardar_leer_y_eliminar_version_exacta_sin_acl_publica(self):
        self.stub.add_response('put_object', {'VersionId': 'v1'}, self.parametros_put())
        guardado = storage.guardar(self.content, 'servicios/prueba/foto.png', tipo_contenido='image/png')
        self.assertEqual((guardado.backend, guardado.clave, guardado.hash_sha256, guardado.version_id),
                         ('s3', self.key, self.digest, 'v1'))
        arguments = {'Bucket': 'eva-pruebas', 'Key': self.key, 'VersionId': 'v1'}
        self.stub.add_response('get_object', {'Body': StreamingBody(BytesIO(self.content), len(self.content))}, arguments)
        with storage.abrir(guardado.clave, backend=guardado.backend, version_id=guardado.version_id) as body:
            self.assertEqual(body.read(), self.content)
        self.stub.add_response('delete_object', {}, arguments)
        storage.eliminar(guardado.clave, backend='s3', version_id='v1')
        self.stub.assert_no_pending_responses()

    def test_error_s3_y_no_sobrescritura_no_caen_a_disco(self):
        self.stub.add_client_error('put_object', service_error_code='PreconditionFailed', http_status_code=412,
                                   expected_params=self.parametros_put())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'privado'
            with override_settings(EVA_CAPTURE_PRIVATE_ROOT=root):
                with self.assertRaises(storage.ErrorAlmacenamiento):
                    storage.guardar(self.content, 'servicios/prueba/foto.png', tipo_contenido='image/png')
                self.assertFalse(root.exists())
        self.stub.add_client_error('get_object', service_error_code='AccessDenied', http_status_code=403,
                                   expected_params={'Bucket': 'eva-pruebas', 'Key': self.key})
        with self.assertRaises(storage.ErrorAlmacenamiento):
            storage.abrir(self.key, backend='s3')
        self.stub.assert_no_pending_responses()

    def test_lectura_fuera_de_prefijo_o_traversal_no_llaman_aws(self):
        for key in ('otro/foto.png', 'eva/capturas/../foto.png', '/etc/foto.png', 'C:\\foto.png'):
            with self.subTest(key=key):
                with self.assertRaises(storage.ErrorAlmacenamiento):
                    storage.abrir(key, backend='s3')

    def test_foto_local_sigue_accesible_cuando_nuevas_fotos_usan_s3(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(EVA_CAPTURE_PRIVATE_ROOT=Path(directory)):
            local = storage.guardar(b'foto-local', 'antigua.png', backend='local')
            self.assertEqual(local.backend, 'local')
            with storage.abrir(local.clave, backend='local') as body:
                self.assertEqual(body.read(), b'foto-local')

    def test_no_such_key_se_traduce_a_excepcion_de_dominio(self):
        self.stub.add_client_error('get_object', service_error_code='NoSuchKey', http_status_code=404,
                                   expected_params={'Bucket': 'eva-pruebas', 'Key': self.key})
        with self.assertRaises(storage.ArchivoNoEncontrado):
            storage.abrir(self.key, backend='s3')
