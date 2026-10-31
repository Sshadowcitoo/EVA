"""Garantías complementarias de configuración; sin SDK ni credenciales AWS."""

from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from config.capture_checks import check_capture_configuration


@override_settings(
    EVA_STORAGE_BACKEND="s3", EVA_S3_BUCKET="bucket-de-prueba",
    EVA_S3_REGION="us-east-1", EVA_S3_PREFIX="pruebas/capturas/",
    EVA_CAPTURE_BASE_URL="https://eva.example",
)
class ConfiguracionBloque3ComplementariaTests(SimpleTestCase):
    def test_comprobacion_s3_no_abre_red_ni_crea_directorios(self):
        with patch("socket.create_connection", side_effect=AssertionError("Red no permitida")), \
             patch.object(Path, "mkdir", side_effect=AssertionError("Escritura no permitida")):
            self.assertEqual(check_capture_configuration(None), [])

    def test_error_s3_no_se_oculta_como_backend_local(self):
        with override_settings(EVA_S3_BUCKET="", EVA_S3_REGION="", EVA_S3_PREFIX="../otro"):
            codigos = {error.id for error in check_capture_configuration(None)}
        self.assertTrue({"captura.E003", "captura.E004"}.issubset(codigos))

    def test_raiz_privada_fuera_del_repo_pero_dentro_de_static_tambien_se_rechaza(self):
        # Rutas solo para resolver/confinar: no se crean directorios.
        raiz = Path(__file__).resolve().parents[2].parent / "estaticos-prueba"
        with override_settings(
            EVA_STORAGE_BACKEND="local", STATICFILES_DIRS=[raiz],
            EVA_CAPTURE_PRIVATE_ROOT=raiz / "capturas",
        ):
            codigos = {error.id for error in check_capture_configuration(None)}
        self.assertIn("captura.E002", codigos)
