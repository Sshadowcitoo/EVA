from datetime import timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from . import limpieza, storage
from .models import CargaFotografia, FotografiaServicio, Servicio
from .test_dominio_bandejas import BaseDominio
from .test_integracion_bloques import foto


class LimpiezaTests(BaseDominio):
    def setUp(self):
        super().setUp()
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        ajuste = self.settings(EVA_STORAGE_BACKEND="local", EVA_CAPTURE_PRIVATE_ROOT=self.raiz)
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        call_command("configurar_roles", stdout=StringIO())
        self.usuario.groups.add(Group.objects.get(name="Registro"))
        self.client.force_login(self.usuario)
        self.servicio = self.nuevo_servicio()
        self.ahora = timezone.now()

    def fotografia(self, dias=90, **kwargs):
        key = "servicios/prueba/servido/propia.png"
        storage.guardar(b"foto tecnica", key)
        registro = self.capturar(self.servicio, "SERVIDO", clave_archivo=key, **kwargs)
        FotografiaServicio.objects.filter(pk=registro.pk).update(fecha=self.ahora - timedelta(days=dias))
        registro.refresh_from_db()
        return registro

    def carga(self, horas=24, clave="servicios/prueba/carga.png"):
        registro = limpieza.registrar_carga(clave)
        storage.guardar(b"carga tecnica", clave)
        CargaFotografia.objects.filter(pk=registro.pk).update(creada_en=self.ahora - timedelta(hours=horas))
        return registro

    def test_simulacion_no_borra_archivos_ni_modifica_base(self):
        imagen = self.fotografia()
        carga = self.carga()
        informe = limpieza.ejecutar(ahora=self.ahora)
        self.assertEqual(informe["modo"], "simulacion")
        self.assertEqual(informe["fotos_candidatas"], 1)
        self.assertEqual(informe["cargas_por_reconciliar"], 1)
        self.assertTrue((self.raiz / imagen.clave_archivo).exists())
        self.assertTrue((self.raiz / carga.clave_archivo).exists())
        imagen.refresh_from_db(); carga.refresh_from_db()
        self.assertIsNone(imagen.eliminada_en)
        self.assertIsNone(carga.resuelta_en)
        self.assertEqual(imagen.limpieza_intentos, 0)

    def test_borra_al_cumplir_90_dias_y_conserva_historial(self):
        imagen = self.fotografia(checklist={"plato_visible": True, "vista_superior": True, "luz_adecuada": True})
        anterior = (imagen.servicio_id, imagen.fecha, imagen.autor_id, imagen.checklist)
        resultado = limpieza.ejecutar(aplicar=True, ahora=self.ahora)
        self.assertEqual(resultado["fotos_eliminadas"], 1)
        self.assertFalse((self.raiz / imagen.clave_archivo).exists())
        imagen.refresh_from_db()
        self.assertEqual(imagen.eliminada_en, self.ahora)
        self.assertEqual((imagen.servicio_id, imagen.fecha, imagen.autor_id, imagen.checklist), anterior)
        self.assertTrue(Servicio.objects.filter(pk=self.servicio.pk).exists())
        self.assertEqual(limpieza.ejecutar(aplicar=True, ahora=self.ahora)["fotos_candidatas"], 0)

    def test_foto_reciente_y_carga_en_curso_no_se_tocan(self):
        imagen = self.fotografia(dias=89)
        carga = self.carga(horas=23)
        with patch("apps.captura.storage.eliminar") as eliminar:
            limpieza.ejecutar(aplicar=True, ahora=self.ahora)
            eliminar.assert_not_called()
        self.assertTrue((self.raiz / imagen.clave_archivo).exists())
        self.assertTrue((self.raiz / carga.clave_archivo).exists())

    def test_fallo_se_registra_y_reintento_idempotente_completa(self):
        imagen = self.fotografia()
        with patch("apps.captura.storage.eliminar", side_effect=storage.ErrorAlmacenamiento("No autorizado")):
            self.assertEqual(limpieza.ejecutar(aplicar=True, ahora=self.ahora)["errores"], 1)
        imagen.refresh_from_db()
        self.assertIsNone(imagen.eliminada_en)
        self.assertEqual(imagen.limpieza_intentos, 1)
        self.assertTrue(imagen.limpieza_error)
        limpieza.ejecutar(aplicar=True, ahora=self.ahora)
        imagen.refresh_from_db()
        self.assertEqual(imagen.limpieza_intentos, 2)
        self.assertEqual(imagen.limpieza_error, "")

    def test_archivo_ya_ausente_se_marca_eliminado(self):
        imagen = self.fotografia()
        storage.eliminar(imagen.clave_archivo, backend="local")
        self.assertEqual(limpieza.ejecutar(aplicar=True, ahora=self.ahora)["fotos_eliminadas"], 1)

    def test_carga_sin_referencia_se_limpia_y_referenciada_se_conserva(self):
        imagen = self.fotografia(dias=1)
        carga = self.carga(clave="servicios/prueba/otro.png")
        vinculada = CargaFotografia.objects.create(backend="local", clave_archivo=imagen.clave_archivo)
        CargaFotografia.objects.filter(pk=vinculada.pk).update(creada_en=self.ahora - timedelta(hours=24))
        informe = limpieza.ejecutar(aplicar=True, ahora=self.ahora)
        self.assertEqual(informe["cargas_eliminadas"], 1)
        self.assertEqual(informe["cargas_vinculadas"], 1)
        self.assertTrue((self.raiz / imagen.clave_archivo).exists())
        self.assertFalse((self.raiz / carga.clave_archivo).exists())

    def test_version_s3_exacta_y_limite_de_lote(self):
        imagen = self.fotografia(backend="s3", version_id="version-propia")
        with patch("apps.captura.storage.eliminar") as eliminar:
            limpieza.ejecutar(aplicar=True, limite=1, ahora=self.ahora)
            eliminar.assert_called_once_with(imagen.clave_archivo, backend="s3", version_id="version-propia")

    def test_imagen_vencida_no_se_sirve_aunque_borrado_falle(self):
        imagen = self.fotografia()
        with patch("apps.captura.storage.abrir") as abrir:
            response = self.client.get(reverse("captura:imagen", args=[imagen.pk]))
            self.assertEqual(response.status_code, 410)
            self.assertIn("no-store", response["Cache-Control"])
            abrir.assert_not_called()

    def test_comando_simula_por_defecto_y_valida_limite(self):
        self.fotografia()
        out = StringIO()
        call_command("limpiar_fotografias", stdout=out)
        self.assertIn('"modo": "simulacion"', out.getvalue())
        with self.assertRaises(CommandError):
            call_command("limpiar_fotografias", limite=0)

    def test_intencion_existe_antes_de_subir_y_sobrevive_fallo(self):
        def fallo(contenido, clave, **kwargs):
            self.assertTrue(CargaFotografia.objects.filter(clave_archivo=clave).exists())
            raise storage.ErrorAlmacenamiento("Timeout")
        with patch("apps.captura.storage.guardar", side_effect=fallo):
            self.client.post(reverse("captura:foto_servido", args=[self.servicio.pk]),
                {"foto": foto(), "plato_visible": True, "vista_superior": True, "luz_adecuada": True})
        self.assertEqual(CargaFotografia.objects.filter(resuelta_en__isnull=True).count(), 1)
        self.assertFalse(self.servicio.fotografias.exists())

    def test_colision_no_programa_borrado_del_objeto_preexistente(self):
        clave = "servicios/prueba/preexistente.png"
        storage.guardar(b"original", clave)
        with patch("apps.captura.storage.generar_clave", return_value=clave):
            self.client.post(reverse("captura:foto_servido", args=[self.servicio.pk]),
                {"foto": foto(), "plato_visible": True, "vista_superior": True, "luz_adecuada": True})
        carga = CargaFotografia.objects.get()
        self.assertEqual(carga.resultado, "colision")
        limpieza.ejecutar(aplicar=True, ahora=self.ahora + timedelta(days=2))
        self.assertEqual((self.raiz / clave).read_bytes(), b"original")

    def test_s3_elimina_solo_version_referenciada_sin_listar_bucket(self):
        import boto3
        from botocore.stub import Stubber
        imagen = self.fotografia(backend="s3", version_id="version-propia")
        key = "eva/capturas/servicios/prueba/foto.png"
        FotografiaServicio.objects.filter(pk=imagen.pk).update(clave_archivo=key)
        cliente = boto3.client("s3", region_name="us-east-2", aws_access_key_id="testing", aws_secret_access_key="testing")
        with self.settings(EVA_S3_BUCKET="eva-pruebas", EVA_S3_REGION="us-east-2", EVA_S3_PREFIX="eva/capturas/"):
            with Stubber(cliente) as stub, patch("apps.captura.storage._cliente_s3", return_value=cliente):
                stub.add_response("delete_object", {}, {"Bucket": "eva-pruebas", "Key": key, "VersionId": "version-propia"})
                self.assertEqual(limpieza.ejecutar(aplicar=True, ahora=self.ahora)["fotos_eliminadas"], 1)
                stub.assert_no_pending_responses()

    def test_carga_fallida_queda_pendiente_y_comando_indica_fallo(self):
        carga = self.carga(horas=25)
        with patch("apps.captura.storage.eliminar", side_effect=storage.ErrorAlmacenamiento("Fallo")):
            with self.assertRaises(CommandError):
                call_command("limpiar_fotografias", aplicar=True, stdout=StringIO())
        carga.refresh_from_db()
        self.assertIsNone(carga.resuelta_en)
        self.assertEqual(carga.intentos, 1)
        self.assertTrue(carga.error)

    def test_traversal_en_registro_no_borra_archivo_exterior(self):
        imagen = self.fotografia()
        exterior = self.raiz / "exterior.txt"
        exterior.write_bytes(b"conservar")
        FotografiaServicio.objects.filter(pk=imagen.pk).update(clave_archivo="../exterior.txt")
        self.assertEqual(limpieza.ejecutar(aplicar=True, ahora=self.ahora)["errores"], 1)
        self.assertEqual(exterior.read_bytes(), b"conservar")

    def test_referencia_reciente_al_mismo_archivo_impide_borrarlo(self):
        imagen = self.fotografia()
        self.capturar(self.servicio, "RETORNO", clave_archivo=imagen.clave_archivo)
        with patch("apps.captura.storage.eliminar") as eliminar:
            informe = limpieza.ejecutar(aplicar=True, ahora=self.ahora)
            eliminar.assert_not_called()
        self.assertEqual(informe["fotos_protegidas_por_referencia_reciente"], 1)
