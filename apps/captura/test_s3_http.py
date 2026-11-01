from io import BytesIO, StringIO
from unittest.mock import patch

import boto3
from botocore.response import StreamingBody
from botocore.stub import ANY, Stubber
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse

from . import test_dominio_bandejas as dominio
from .test_integracion_bloques import foto
from .forms import procesar_imagen


@override_settings(EVA_STORAGE_BACKEND='s3', EVA_S3_BUCKET='eva-pruebas', EVA_S3_REGION='us-east-2', EVA_S3_PREFIX='eva/capturas/')
class CapturaS3HTTPTests(dominio.BaseDominio):
    def setUp(self):
        super().setUp()
        call_command('configurar_roles', stdout=StringIO())
        self.usuario.groups.add(Group.objects.get(name='Registro'))
        self.client.force_login(self.usuario)
        self.servicio = self.nuevo_servicio()
        self.url = reverse('captura:foto_servido', args=[self.servicio.pk])
        client = boto3.client('s3', region_name='us-east-2', aws_access_key_id='testing', aws_secret_access_key='testing')
        self.stub = Stubber(client)
        self.stub.activate()
        self.addCleanup(self.stub.deactivate)
        patcher = patch('apps.captura.storage._cliente_s3', return_value=client)
        patcher.start()
        self.addCleanup(patcher.stop)

    def put_response(self):
        self.stub.add_response('put_object', {'VersionId': 'v1'}, {
            'Bucket': 'eva-pruebas', 'Key': ANY, 'Body': ANY, 'ContentType': 'image/png',
            'ServerSideEncryption': 'AES256', 'IfNoneMatch': '*', 'Metadata': ANY, 'ChecksumSHA256': ANY,
        })

    def test_post_persiste_backend_clave_hash_version_y_lectura_autorizada(self):
        self.put_response()
        self.assertEqual(self.client.post(self.url, {'foto': foto(), 'plato_visible': True, 'vista_superior': True, 'luz_adecuada': True}).status_code, 302)
        accepted = self.servicio.fotografias.get()
        self.assertEqual((accepted.backend, accepted.version_id), ('s3', 'v1'))
        self.assertTrue(accepted.clave_archivo.startswith('eva/capturas/servicios/'))
        self.assertEqual(len(accepted.hash_sha256), 64)
        payload = procesar_imagen(foto()).contenido
        self.stub.add_response('get_object', {'Body': StreamingBody(BytesIO(payload), len(payload))}, {
            'Bucket': 'eva-pruebas', 'Key': accepted.clave_archivo, 'VersionId': 'v1',
        })
        image_url = reverse('captura:imagen', args=[accepted.pk])
        response = self.client.get(image_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), payload)
        response.close()
        self.client.logout()
        self.assertEqual(self.client.get(image_url).status_code, 302)
        self.stub.assert_no_pending_responses()

    def test_rechazo_bd_limpia_objeto_s3_y_no_avanza(self):
        self.put_response()
        self.stub.add_response('delete_object', {}, {'Bucket': 'eva-pruebas', 'Key': ANY, 'VersionId': 'v1'})
        with patch('apps.captura.services.registrar_captura', side_effect=ValidationError('No aceptar')):
            self.assertEqual(self.client.post(self.url, {'foto': foto(), 'plato_visible': True, 'vista_superior': True, 'luz_adecuada': True}).status_code, 200)
        self.assertFalse(self.servicio.fotografias.exists())
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, 'PENDIENTE_SERVIDO')
        self.stub.assert_no_pending_responses()
