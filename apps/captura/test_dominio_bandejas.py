from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.captura import services
from apps.captura.models import (
    AsignacionBandeja,
    Bandeja,
    EtiquetaBandeja,
    FotografiaServicio,
    Servicio,
)
from apps.catalogo.models import Plato, TipoPorcion

Estado = Servicio.EstadoCaptura
Etapa = FotografiaServicio.Etapa


class BaseDominio(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        call_command("cargar_bandejas_demo", verbosity=0)
        self.usuario = get_user_model().objects.create_user("operador_prueba")
        self.plato = Plato.objects.get(codigo="seco_de_pollo")
        self.porcion = TipoPorcion.objects.get(codigo="estandar")
        self.bandeja = Bandeja.objects.get(numero=1)

    def nuevo_servicio(self, bandeja=None):
        return Servicio.registrar(
            plato=self.plato,
            porcion=self.porcion,
            usuario=self.usuario,
            bandeja=bandeja or self.bandeja,
        )

    def capturar(self, servicio, etapa, **cambios):
        datos = dict(
            servicio=servicio,
            etapa=etapa,
            clave_archivo=f"{servicio.pk}/{etapa}/prueba",
            tipo_contenido="image/jpeg",
            tamano_bytes=1000,
            ancho=640,
            alto=480,
            autor=self.usuario,
        )
        datos.update(cambios)
        return services.registrar_captura(**datos)


class DatosTests(BaseDominio):
    def test_carga_demo_crea_diez_bandejas_con_etiqueta(self):
        self.assertEqual(Bandeja.objects.count(), 10)
        self.assertEqual(EtiquetaBandeja.objects.filter(revocada_en__isnull=True).count(), 10)

    def test_carga_demo_repetida_no_modifica_datos(self):
        codigos = set(EtiquetaBandeja.objects.values_list("codigo", flat=True))
        self.bandeja.activo = False
        self.bandeja.save()
        call_command("cargar_bandejas_demo", verbosity=0)
        self.assertEqual(Bandeja.objects.count(), 10)
        self.assertEqual(EtiquetaBandeja.objects.count(), 10)
        self.assertEqual(
            set(EtiquetaBandeja.objects.values_list("codigo", flat=True)), codigos
        )
        self.bandeja.refresh_from_db()
        self.assertFalse(self.bandeja.activo)

    def test_una_sola_etiqueta_vigente_por_bandeja(self):
        with self.assertRaises(ValidationError):
            services.emitir_etiqueta(bandeja=self.bandeja)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EtiquetaBandeja.objects.create(bandeja=self.bandeja)

    def test_codigos_de_etiqueta_distintos_y_largos(self):
        codigos = list(EtiquetaBandeja.objects.values_list("codigo", flat=True))
        self.assertEqual(len(set(codigos)), 10)
        self.assertTrue(all(len(c) >= 20 for c in codigos))

    def test_reemplazar_etiqueta_conserva_historial_y_asignacion(self):
        servicio = self.nuevo_servicio()
        anterior = self.bandeja.etiquetas.get(revocada_en__isnull=True)
        nueva = services.reemplazar_etiqueta(
            bandeja=self.bandeja, motivo="Etiqueta dañada", usuario=self.usuario
        )
        anterior.refresh_from_db()
        self.assertFalse(anterior.vigente)
        self.assertEqual(anterior.motivo_revocacion, "Etiqueta dañada")
        self.assertEqual(anterior.revocada_por, self.usuario)
        self.assertIsNotNone(anterior.revocada_en)
        self.assertTrue(nueva.vigente)
        self.assertNotEqual(anterior.codigo, nueva.codigo)
        self.assertEqual(self.bandeja.etiquetas.count(), 2)
        asignacion = AsignacionBandeja.objects.get(servicio=servicio)
        self.assertEqual(asignacion.bandeja, self.bandeja)
        self.assertIsNone(asignacion.fin)

    def test_reemplazar_etiqueta_requiere_motivo(self):
        antes = self.bandeja.etiquetas.get(revocada_en__isnull=True)
        with self.assertRaises(ValidationError):
            services.reemplazar_etiqueta(
                bandeja=self.bandeja, motivo="  ", usuario=self.usuario
            )
        antes.refresh_from_db()
        self.assertTrue(antes.vigente)
        self.assertEqual(self.bandeja.etiquetas.count(), 1)

    def test_permisos_personalizados_declarados_por_los_modelos(self):
        codenames = set(
            Permission.objects.filter(content_type__app_label="captura").values_list(
                "codename", flat=True
            )
        )
        self.assertIn("anular_servicio", codenames)
        self.assertIn("reemplazar_etiquetabandeja", codenames)
        self.assertIn("add_fotografiaservicio", codenames)
        self.assertIn("delete_fotografiaservicio", codenames)
        self.assertTrue(
            Permission.objects.filter(
                content_type__app_label="captura",
                content_type__model="etiquetabandeja",
                codename="reemplazar_etiquetabandeja",
            ).exists()
        )
        self.assertTrue(
            Permission.objects.filter(
                content_type__app_label="captura",
                content_type__model="servicio",
                codename="anular_servicio",
            ).exists()
        )

    def test_una_fotografia_vigente_por_servicio_y_etapa(self):
        servicio = self.nuevo_servicio()
        self.capturar(servicio, Etapa.SERVIDO)
        with self.assertRaises(IntegrityError), transaction.atomic():
            FotografiaServicio.objects.create(
                servicio=servicio, etapa=Etapa.SERVIDO, clave_archivo="otra",
                tipo_contenido="image/png", tamano_bytes=1, ancho=1, alto=1,
                autor=self.usuario,
            )


class AsignacionTests(BaseDominio):
    def test_registrar_con_bandeja_asigna_y_deja_pendiente(self):
        servicio = self.nuevo_servicio()
        self.assertEqual(servicio.estado_captura, Estado.PENDIENTE_SERVIDO)
        self.assertEqual(servicio.asignaciones.filter(fin__isnull=True).count(), 1)

    def test_bandeja_ocupada_se_rechaza_sin_filas_parciales(self):
        self.nuevo_servicio()
        with self.assertRaises(ValidationError):
            self.nuevo_servicio()
        self.assertEqual(Servicio.objects.count(), 1)
        self.assertEqual(AsignacionBandeja.objects.count(), 1)

    def test_bandeja_inactiva_se_rechaza(self):
        self.bandeja.activo = False
        self.bandeja.save()
        with self.assertRaises(ValidationError):
            self.nuevo_servicio()
        self.assertEqual(Servicio.objects.count(), 0)

    def test_un_servicio_no_tiene_dos_asignaciones_abiertas(self):
        servicio = self.nuevo_servicio()
        otra = Bandeja.objects.get(numero=2)
        with self.assertRaises(ValidationError):
            services.asignar_bandeja(servicio=servicio, bandeja=otra)
        self.assertEqual(AsignacionBandeja.objects.count(), 1)

    def test_registrar_sin_bandeja_conserva_el_comportamiento_anterior(self):
        servicio = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.assertEqual(servicio.estado_captura, "")
        self.assertEqual(servicio.asignaciones.count(), 0)


class EstadosTests(BaseDominio):
    def test_flujo_completo_libera_la_bandeja(self):
        servicio = self.nuevo_servicio()
        self.capturar(servicio, Etapa.SERVIDO)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, Estado.EN_ESPERA_RETORNO)
        self.assertEqual(servicio.asignaciones.filter(fin__isnull=True).count(), 1)

        self.capturar(servicio, Etapa.RETORNO)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, Estado.PAR_COMPLETO)
        self.assertEqual(servicio.asignaciones.filter(fin__isnull=True).count(), 0)
        self.assertEqual(servicio.fotografias.count(), 2)

    def test_retorno_por_otro_operador_conserva_creador_y_guarda_su_autor(self):
        otro = get_user_model().objects.create_user("otro_operador")
        servicio = self.nuevo_servicio()
        self.capturar(servicio, Etapa.SERVIDO)
        self.capturar(servicio, Etapa.RETORNO, autor=otro)
        servicio.refresh_from_db()
        self.assertEqual(servicio.creado_por, self.usuario)
        self.assertEqual(servicio.fotografias.get(etapa=Etapa.RETORNO).autor, otro)
        self.assertEqual(servicio.fotografias.get(etapa=Etapa.SERVIDO).autor, self.usuario)

    def test_bandeja_reutilizable_y_servicio_anterior_conserva_todo(self):
        primero = self.nuevo_servicio()
        self.capturar(primero, Etapa.SERVIDO)
        self.capturar(primero, Etapa.RETORNO)
        segundo = self.nuevo_servicio()
        self.assertEqual(segundo.asignaciones.get().bandeja, self.bandeja)
        primero.refresh_from_db()
        self.assertEqual(primero.fotografias.count(), 2)
        self.assertEqual(primero.composicion.count(), 3)
        self.assertEqual(primero.asignaciones.get().bandeja, self.bandeja)

    def test_retorno_sin_servido_denegado(self):
        servicio = self.nuevo_servicio()
        with self.assertRaises(ValidationError):
            self.capturar(servicio, Etapa.RETORNO)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, Estado.PENDIENTE_SERVIDO)
        self.assertEqual(servicio.fotografias.count(), 0)
        self.assertEqual(servicio.asignaciones.filter(fin__isnull=True).count(), 1)

    def test_servido_duplicado_no_sobrescribe(self):
        servicio = self.nuevo_servicio()
        primera = self.capturar(servicio, Etapa.SERVIDO)
        with self.assertRaises(ValidationError):
            self.capturar(servicio, Etapa.SERVIDO, clave_archivo="otra/clave")
        self.assertEqual(servicio.fotografias.count(), 1)
        self.assertEqual(servicio.fotografias.get().clave_archivo, primera.clave_archivo)

    def test_retorno_duplicado_no_sobrescribe(self):
        servicio = self.nuevo_servicio()
        self.capturar(servicio, Etapa.SERVIDO)
        self.capturar(servicio, Etapa.RETORNO)
        with self.assertRaises(ValidationError):
            self.capturar(servicio, Etapa.RETORNO, clave_archivo="otra/clave")
        self.assertEqual(servicio.fotografias.count(), 2)

    def test_datos_invalidos_no_avanzan_el_estado(self):
        servicio = self.nuevo_servicio()
        with self.assertRaises(ValidationError):
            self.capturar(servicio, Etapa.SERVIDO, tamano_bytes=0)
        with self.assertRaises(ValidationError):
            self.capturar(servicio, "OTRA")
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, Estado.PENDIENTE_SERVIDO)
        self.assertEqual(servicio.fotografias.count(), 0)

    def test_completar_par_sin_ambas_fotos_se_rechaza(self):
        servicio = self.nuevo_servicio()
        self.capturar(servicio, Etapa.SERVIDO)
        with self.assertRaises(ValidationError):
            services.completar_par(servicio=servicio)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, Estado.EN_ESPERA_RETORNO)

    def test_anulacion_conserva_motivo_responsable_y_libera(self):
        servicio = self.nuevo_servicio()
        self.capturar(servicio, Etapa.SERVIDO)
        services.anular_servicio(
            servicio=servicio, motivo="  Error de registro  ", usuario=self.usuario
        )
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, Estado.ANULADO)
        self.assertEqual(servicio.anulado_motivo, "Error de registro")
        self.assertEqual(servicio.anulado_por, self.usuario)
        self.assertIsNotNone(servicio.anulado_en)
        self.assertEqual(servicio.asignaciones.filter(fin__isnull=True).count(), 0)
        self.assertEqual(servicio.fotografias.count(), 1)
        self.assertTrue(Servicio.objects.get(pk=servicio.pk).composicion.exists())

    def test_anulacion_requiere_motivo(self):
        servicio = self.nuevo_servicio()
        with self.assertRaises(ValidationError):
            services.anular_servicio(servicio=servicio, motivo="   ", usuario=self.usuario)
        servicio.refresh_from_db()
        self.assertEqual(servicio.estado_captura, Estado.PENDIENTE_SERVIDO)

    def test_no_se_anula_un_par_completo_ni_dos_veces(self):
        servicio = self.nuevo_servicio()
        self.capturar(servicio, Etapa.SERVIDO)
        self.capturar(servicio, Etapa.RETORNO)
        with self.assertRaises(ValidationError):
            services.anular_servicio(servicio=servicio, motivo="x", usuario=self.usuario)

        otro = self.nuevo_servicio()
        services.anular_servicio(servicio=otro, motivo="x", usuario=self.usuario)
        with self.assertRaises(ValidationError):
            services.anular_servicio(servicio=otro, motivo="y", usuario=self.usuario)

    def test_despues_de_anular_se_puede_usar_la_bandeja(self):
        servicio = self.nuevo_servicio()
        services.anular_servicio(servicio=servicio, motivo="x", usuario=self.usuario)
        self.assertEqual(self.nuevo_servicio().asignaciones.get().bandeja, self.bandeja)


class HistoricosTests(BaseDominio):
    def test_servicio_historico_queda_sin_captura(self):
        historico = Servicio.objects.create(
            plato="lentejas", plato_nombre="Lentejas",
            tipo_porcion="grande", porcion_nombre="Grande",
        )
        self.assertEqual(historico.estado_captura, "")
        self.assertEqual(historico.get_plato_display(), "Lentejas")
        with self.assertRaises(ValidationError):
            services.asignar_bandeja(servicio=historico, bandeja=self.bandeja)
        with self.assertRaises(ValidationError):
            self.capturar(historico, Etapa.SERVIDO)
        with self.assertRaises(ValidationError):
            services.anular_servicio(servicio=historico, motivo="x", usuario=self.usuario)
        historico.refresh_from_db()
        self.assertEqual(historico.estado_captura, "")
        self.assertEqual(historico.fotografias.count(), 0)
        self.assertEqual(historico.asignaciones.count(), 0)