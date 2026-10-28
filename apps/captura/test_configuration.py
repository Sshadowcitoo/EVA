from django.test import SimpleTestCase, override_settings

from config.capture_checks import check_capture_configuration


@override_settings(EVA_STORAGE_BACKEND='local', EVA_CAPTURE_BASE_URL='')
class CaptureConfigurationTests(SimpleTestCase):
    def codes(self):
        return {error.id for error in check_capture_configuration(None)}

    def test_default_local_needs_no_aws_credentials_or_network(self):
        self.assertEqual(self.codes(), set())

    def test_unknown_backend_is_not_silently_local(self):
        with override_settings(EVA_STORAGE_BACKEND='otro'):
            self.assertIn('captura.E001', self.codes())

    def test_private_directory_cannot_be_relative_or_inside_checkout(self):
        from django.conf import settings
        for path in ('relative/photos', settings.BASE_DIR / 'static' / 'photos'):
            with self.subTest(path=path), override_settings(EVA_CAPTURE_PRIVATE_ROOT=path):
                self.assertIn('captura.E002', self.codes())

    def test_s3_requires_explicit_bucket_and_region(self):
        with override_settings(EVA_STORAGE_BACKEND='s3', EVA_S3_BUCKET='', EVA_S3_REGION=''):
            self.assertIn('captura.E003', self.codes())

    @override_settings(EVA_STORAGE_BACKEND='s3', EVA_S3_BUCKET='bucket-demo', EVA_S3_REGION='us-east-1')
    def test_s3_prefix_and_complete_configuration(self):
        for prefix in ('', '/public/', '../otro/', 'eva//capturas', 'eva\\capturas'):
            with self.subTest(prefix=prefix), override_settings(EVA_S3_PREFIX=prefix):
                self.assertIn('captura.E004', self.codes())
        with override_settings(EVA_S3_PREFIX='eva/capturas/'):
            self.assertEqual(self.codes(), set())

    def test_capture_origin_is_https_without_secret_or_loopback(self):
        for url in ('http://eva.example', 'https://localhost', 'https://127.0.0.1',
                    'https://user:secret@eva.example', 'https://eva.example/?token=x',
                    'https://eva.example/#token', 'https://eva.example/captura',
                    'https://eva.example:bad'):
            with self.subTest(url=url), override_settings(EVA_CAPTURE_BASE_URL=url):
                self.assertIn('captura.E005', self.codes())
        with override_settings(EVA_CAPTURE_BASE_URL='https://eva.example'):
            self.assertEqual(self.codes(), set())
