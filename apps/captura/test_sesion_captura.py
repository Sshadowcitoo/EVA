from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.captura import services
from apps.captura.models import FotografiaServicio, Servicio, SesionCaptura
from apps.captura.test_dominio_bandejas import BaseDominio

Etapa = FotografiaServicio.Etapa
Estado = Servicio.EstadoCaptura
Sesion = SesionCaptura.Estado


class SesionCapturaTests(BaseDominio):
    def setUp(self):
        super().setUp()
        self.servicio = self.nuevo_servicio()

    def crear(self, etapa=Etapa.SERVIDO):
        return services.crear_sesion_captura(
            servicio=self.servicio, etapa=etapa, usuario=self.usuario
        )

    def consumir(self, token, **cambios):
        datos = dict(
            token=token, autor=self.usuario, clave_archivo="k/1",
            tipo_contenido="image/jpeg", tamano_bytes=10, ancho=4, alto=4,
        )
        datos.update(cambios)
        return services.consumir_sesion(**datos)

    def test_token_largo_aleatorio_y_solo_se_guarda_el_digest(self):
        sesion, token = self.crear()
        self.assertGreaterEqual(len(token), 43)  # >= 256 bits en base64
        self.assertNotIn(token, sesion.token_digest)
        self.assertEqual(len(sesion.token_digest), 64)
        otra, otro_token = self.crear()
        self.assertNotEqual(token, otro_token)

    def test_vigencia_de_cinco_minutos(self):
        sesion, _ = self.crear()
        espera = sesion.expira_en - sesion.creada_en
        self.assertEqual(espera, timedelta(minutes=services.MINUTOS_SESION_CAPTURA))
        self.assertEqual(services.MINUTOS_SESION_CAPTURA, 5)

    def test_nueva_solicitud_invalida_la_pendiente_anterior(self):
        anterior, token_viejo = self.crear()
        nueva, _ = self.crear()
        anterior.refresh_from_db()
        self.assertEqual(anterior.estado, Sesion.CANCELADA)
        self.assertEqual(nueva.estado, Sesion.PENDIENTE)
        with self.assertRaises(ValidationError):
            self.consumir(token_viejo)
        self.assertEqual(self.servicio.fotografias.count(), 0)

    def test_etapa_incompatible_con_el_estado_del_servicio(self):
        with self.assertRaises(ValidationError):
            self.crear(Etapa.RETORNO)
        self.assertEqual(SesionCaptura.objects.count(), 0)

    def test_consumir_guarda_foto_avanza_estado_y_completa(self):
        sesion, token = self.crear()
        foto = self.consumir(token, backend="s3", version_id="v1", hash_sha256="a" * 64)
        sesion.refresh_from_db()
        self.servicio.refresh_from_db()
        self.assertEqual(sesion.estado, Sesion.COMPLETADA)
        self.assertEqual(sesion.fotografia, foto)
        self.assertIsNotNone(sesion.completada_en)
        self.assertEqual(self.servicio.estado_captura, Estado.EN_ESPERA_RETORNO)
        self.assertEqual((foto.backend, foto.version_id), ("s3", "v1"))

    def test_consumo_unico_y_segunda_carga_no_reemplaza(self):
        _, token = self.crear()
        primera = self.consumir(token)
        with self.assertRaises(ValidationError):
            self.consumir(token, clave_archivo="k/2")
        self.assertEqual(self.servicio.fotografias.count(), 1)
        self.assertEqual(self.servicio.fotografias.get().clave_archivo, primera.clave_archivo)

    def test_sesion_expirada_se_marca_en_servidor_y_no_consume(self):
        sesion, token = self.crear()
        SesionCaptura.objects.filter(pk=sesion.pk).update(
            expira_en=timezone.now() - timedelta(seconds=1)
        )
        with self.assertRaises(ValidationError):
            self.consumir(token)
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, Sesion.EXPIRADA)
        self.assertEqual(self.servicio.fotografias.count(), 0)

    def test_sesion_cancelada_no_consume(self):
        sesion, token = self.crear()
        services.cancelar_sesion(sesion=sesion)
        with self.assertRaises(ValidationError):
            self.consumir(token)
        with self.assertRaises(ValidationError):
            services.cancelar_sesion(sesion=sesion)

    def test_token_desconocido(self):
        with self.assertRaises(ValidationError):
            services.obtener_sesion(token="no-existe")

    def test_fallo_al_registrar_no_consume_el_token(self):
        sesion, token = self.crear()
        with self.assertRaises(ValidationError):
            self.consumir(token, tamano_bytes=0)
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, Sesion.PENDIENTE)
        self.assertEqual(self.servicio.fotografias.count(), 0)
        self.consumir(token)  # el reintento válido sí funciona
        sesion.refresh_from_db()
        self.assertEqual(sesion.estado, Sesion.COMPLETADA)

    def test_flujo_de_retorno_completa_el_par(self):
        _, t1 = self.crear()
        self.consumir(t1)
        _, t2 = self.crear(Etapa.RETORNO)
        self.consumir(t2, clave_archivo="k/r")
        self.servicio.refresh_from_db()
        self.assertEqual(self.servicio.estado_captura, Estado.PAR_COMPLETO)
        self.assertEqual(self.servicio.asignaciones.filter(fin__isnull=True).count(), 0)

    def test_registrar_captura_sigue_funcionando_sin_hash_ni_version(self):
        foto = self.capturar(self.servicio, Etapa.SERVIDO)
        self.assertEqual((foto.hash_sha256, foto.version_id), ("", ""))