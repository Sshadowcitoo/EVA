"""Contrato de storage local de Lino; no valida aún decodificación de imágenes.

Todas las escrituras se confinan a TemporaryDirectory, nunca a fotos del piloto.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.captura import storage


class AlmacenamientoPrivadoTests(SimpleTestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name) / "privado"
        ajuste = self.settings(EVA_CAPTURE_PRIVATE_ROOT=self.raiz)
        ajuste.enable()
        self.addCleanup(ajuste.disable)

    def test_guardar_abrir_eliminar_y_eliminacion_repetida(self):
        clave = "servicios/prueba/servido/foto.png"
        storage.guardar(b"contenido de prueba", clave)
        with storage.abrir(clave) as archivo:
            self.assertEqual(archivo.read(), b"contenido de prueba")
        storage.eliminar(clave)
        storage.eliminar(clave)
        with self.assertRaises(storage.ArchivoNoEncontrado):
            storage.abrir(clave)

    def test_duplicado_preserva_bytes_originales(self):
        storage.guardar(b"original", "foto.png")
        with self.assertRaises(storage.ErrorAlmacenamiento):
            storage.guardar(b"reemplazo", "foto.png")
        with storage.abrir("foto.png") as archivo:
            self.assertEqual(archivo.read(), b"original")

    def test_traversal_rechazado_en_todas_las_operaciones(self):
        exterior = Path(self.temporal.name) / "no_tocar.txt"
        exterior.write_bytes(b"intacto")
        for operacion in (lambda: storage.guardar(b"otro", "../no_tocar.txt"),
                          lambda: storage.abrir("../no_tocar.txt"),
                          lambda: storage.eliminar("../no_tocar.txt")):
            with self.assertRaises(storage.ErrorAlmacenamiento):
                operacion()
        self.assertEqual(exterior.read_bytes(), b"intacto")

    def test_ruta_absoluta_rechazada_aunque_este_dentro_de_raiz(self):
        # El contrato exige claves opacas relativas, no rutas físicas del cliente.
        with self.assertRaises(storage.ErrorAlmacenamiento):
            storage.guardar(b"prueba", str(self.raiz / "absoluta.png"))

    def test_error_de_escritura_parcial_no_deja_archivo(self):
        class EscrituraFallida:
            def __enter__(interior):
                ruta = self.raiz / "parcial.png"
                ruta.write_bytes(b"parcial")
                return interior

            def write(interior, contenido):
                raise OSError("disco simulado")

            def __exit__(interior, *args):
                return False

        with patch("apps.captura.storage.open", return_value=EscrituraFallida()):
            with self.assertRaises(storage.ErrorAlmacenamiento):
                storage.guardar(b"datos", "parcial.png")
        self.assertFalse((self.raiz / "parcial.png").exists())

    def test_error_lectura_y_borrado_tienen_excepcion_de_dominio(self):
        with patch("apps.captura.storage.open", side_effect=PermissionError("denegado")):
            with self.assertRaises(storage.ErrorAlmacenamiento):
                storage.abrir("foto.png")
        with patch.object(Path, "unlink", side_effect=PermissionError("denegado")):
            with self.assertRaises(storage.ErrorAlmacenamiento):
                storage.eliminar("foto.png")
