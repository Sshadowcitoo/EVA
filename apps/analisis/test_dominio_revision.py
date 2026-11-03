from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.analisis import services
from apps.analisis.models import (
    AnalisisServicio,
    IntentoAnalisis,
    ResultadoComponente,
    RevisionAnalisis,
)
from apps.analisis.test_dominio_analisis import BaseAnalisis

Decision = RevisionAnalisis.Decision


class BaseRevision(BaseAnalisis):
    def setUp(self):
        super().setUp()
        self.cocina = self.crear_revisor("cocina_uno")
        self.cocina_dos = self.crear_revisor("cocina_dos")

    def crear_revisor(self, nombre):
        usuario = get_user_model().objects.create_user(nombre)
        usuario.user_permissions.add(Permission.objects.get(codename="add_revisionanalisis"))
        return get_user_model().objects.get(pk=usuario.pk)  # sin caché de permisos

    def intento_completado(self, **cambios):
        self.solicitar(**{k: v for k, v in cambios.items() if k in ("version_modelo", "origen")})
        intento = services.reclamar_siguiente_intento()
        datos = {k: v for k, v in cambios.items() if k not in ("version_modelo", "origen")}
        self.completar(intento, **cambios_completar(cambios), **datos)
        return IntentoAnalisis.objects.get(pk=intento.pk)

    def revisar(self, intento, decision, motivo="", usuario=None, version=0, evidencia=True):
        return services.revisar_resultado(
            intento, decision, motivo, usuario or self.cocina, version,
            evidencia_disponible=evidencia)


def cambios_completar(cambios):
    extra = {}
    if "version_modelo" in cambios:
        extra["version_modelo"] = cambios["version_modelo"]
    if "origen" in cambios:
        extra["origen"] = cambios["origen"]
    return extra


class CriteriosPersistidosTests(BaseRevision):
    def test_se_guarda_el_criterio_realmente_aplicado(self):
        intento = self.intento_completado()
        for r in intento.resultados.all():
            self.assertEqual((r.umbral_aplicado, r.configuracion_aprobada), (0.5, True))

    def test_sin_umbral_la_configuracion_queda_no_aprobada(self):
        self.solicitar()
        intento = services.reclamar_siguiente_intento()
        respuesta = self.respuesta()
        for item in respuesta:
            item["umbral_confianza"] = None
        hecho = self.completar(intento, resultados=respuesta)
        for r in hecho.resultados.all():
            self.assertEqual((r.umbral_aplicado, r.configuracion_aprobada), (None, False))


class DecisionTests(BaseRevision):
    def test_confirmar_real_valido_persiste_decision_autor_fecha_y_version(self):
        intento = self.intento_completado()
        self.assertEqual(list(services.intentos_pendientes_de_revision()), [intento])
        revision = self.revisar(intento, Decision.CONFIRMADO)
        self.assertEqual((revision.decision, revision.autor, revision.version), ("CONFIRMADO", self.cocina, 1))
        self.assertTrue(revision.vigente)
        self.assertIsNotNone(revision.fecha)
        self.assertEqual(services.revision_vigente(intento), revision)
        self.assertEqual(list(services.intentos_pendientes_de_revision()), [])

    def test_rechazar_y_no_concluyente_exigen_motivo_y_conservan_el_original(self):
        intento = self.intento_completado()
        antes = list(intento.resultados.values_list("pk", "porcentaje", "estado"))
        for decision in (Decision.RECHAZADO, Decision.NO_CONCLUYENTE):
            with self.assertRaises(ValidationError):
                self.revisar(intento, decision, motivo="   ")
        self.assertEqual(RevisionAnalisis.objects.count(), 0)
        self.revisar(intento, Decision.RECHAZADO, motivo="Foto movida")
        despues = list(intento.resultados.values_list("pk", "porcentaje", "estado"))
        self.assertEqual(antes, despues)  # el resultado técnico no cambia
        intento.refresh_from_db()
        self.assertEqual(intento.estado, IntentoAnalisis.Estado.COMPLETADO)

    def test_confirmar_no_convierte_en_evidencia_apta_lo_que_no_lo_es(self):
        # Simulado
        sim = self.intento_completado(origen="SIMULADO")
        with self.assertRaises(ValidationError):
            self.revisar(sim, Decision.CONFIRMADO)
        # Sin evidencia disponible ahora
        real = self.intento_completado(version_modelo="m2")
        with self.assertRaises(ValidationError):
            self.revisar(real, Decision.CONFIRMADO, evidencia=False)
        # Baja confianza / MAYOR_100 / sin criterio
        malo = self.intento_completado(version_modelo="m3")
        ResultadoComponente.objects.filter(intento=malo).update(
            estado="NO_CONCLUYENTE", motivo="MAYOR_100")
        with self.assertRaises(ValidationError):
            self.revisar(malo, Decision.CONFIRMADO)
        sin_criterio = self.intento_completado(version_modelo="m4")
        ResultadoComponente.objects.filter(intento=sin_criterio).update(configuracion_aprobada=False)
        with self.assertRaises(ValidationError):
            self.revisar(sin_criterio, Decision.CONFIRMADO)
        self.assertEqual(RevisionAnalisis.objects.count(), 0)

    def test_rechazar_un_simulado_si_esta_permitido(self):
        sim = self.intento_completado(origen="SIMULADO")
        self.assertEqual(self.revisar(sim, Decision.RECHAZADO, motivo="No es real").decision, "RECHAZADO")

    def test_solo_intentos_completados_y_vigentes(self):
        self.solicitar()
        pendiente = services.reclamar_siguiente_intento()  # EN_PROCESO
        with self.assertRaises(ValidationError):
            self.revisar(pendiente, Decision.RECHAZADO, motivo="x")
        hecho = self.completar(pendiente)
        AnalisisServicio.objects.filter(pk=hecho.analisis_id).update(intento_vigente=None)
        with self.assertRaises(ValidationError):
            self.revisar(hecho, Decision.RECHAZADO, motivo="x")

    def test_decision_invalida_o_version_invalida(self):
        intento = self.intento_completado()
        with self.assertRaises(ValidationError):
            self.revisar(intento, "APROBADO")
        for mala in (-1, "0", True):
            with self.assertRaises(ValidationError):
                self.revisar(intento, Decision.CONFIRMADO, version=mala)


class PermisosTests(BaseRevision):
    def test_sin_permiso_o_inactivo_se_deniega(self):
        intento = self.intento_completado()
        sin_permiso = get_user_model().objects.create_user("sin_permiso")
        with self.assertRaises(PermissionDenied):
            self.revisar(intento, Decision.CONFIRMADO, usuario=sin_permiso)
        self.cocina.is_active = False
        self.cocina.save()
        self.cocina = get_user_model().objects.get(pk=self.cocina.pk)
        with self.assertRaises(PermissionDenied):
            self.revisar(intento, Decision.CONFIRMADO)
        self.assertEqual(RevisionAnalisis.objects.count(), 0)


class ConcurrenciaTests(BaseRevision):
    def test_doble_envio_no_duplica_decisiones(self):
        intento = self.intento_completado()
        primera = self.revisar(intento, Decision.CONFIRMADO)
        repetida = self.revisar(intento, Decision.CONFIRMADO)  # mismo POST, versión vieja
        self.assertEqual(primera.pk, repetida.pk)
        self.assertEqual(RevisionAnalisis.objects.count(), 1)

    def test_dos_revisores_reciben_conflicto_sin_sobrescritura(self):
        intento = self.intento_completado()
        self.revisar(intento, Decision.CONFIRMADO, usuario=self.cocina)
        with self.assertRaises(services.ConflictoRevision):
            self.revisar(intento, Decision.RECHAZADO, motivo="Distinto",
                         usuario=self.cocina_dos, version=0)
        vigente = services.revision_vigente(intento)
        self.assertEqual((vigente.decision, vigente.autor), ("CONFIRMADO", self.cocina))
        self.assertEqual(RevisionAnalisis.objects.count(), 1)

    def test_la_base_impide_dos_revisiones_vigentes_del_mismo_intento(self):
        intento = self.intento_completado()
        self.revisar(intento, Decision.CONFIRMADO)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RevisionAnalisis.objects.create(
                intento=intento, decision="RECHAZADO", motivo="x",
                autor=self.cocina, version=2)


class RectificacionTests(BaseRevision):
    def test_rectificar_crea_otra_revision_y_conserva_la_historia(self):
        intento = self.intento_completado()
        primera = self.revisar(intento, Decision.CONFIRMADO)
        segunda = self.revisar(intento, Decision.RECHAZADO, motivo="Error de lectura",
                               usuario=self.cocina_dos, version=1)
        primera.refresh_from_db()
        self.assertFalse(primera.vigente)
        self.assertEqual((segunda.version, segunda.sustituye), (2, primera))
        self.assertTrue(segunda.vigente)
        self.assertEqual(intento.revisiones.count(), 2)
        self.assertEqual(primera.decision, "CONFIRMADO")  # no se editó

    def test_rectificar_exige_motivo_y_version_correcta(self):
        intento = self.intento_completado()
        self.revisar(intento, Decision.CONFIRMADO)
        with self.assertRaises(ValidationError):
            self.revisar(intento, Decision.RECHAZADO, motivo="", version=1)
        with self.assertRaises(services.ConflictoRevision):
            self.revisar(intento, Decision.RECHAZADO, motivo="x", version=5)
        self.assertEqual(RevisionAnalisis.objects.count(), 1)
        self.assertTrue(services.revision_vigente(intento).decision == "CONFIRMADO")

    def test_rectificar_a_confirmado_tambien_exige_motivo_y_evidencia(self):
        intento = self.intento_completado()
        self.revisar(intento, Decision.RECHAZADO, motivo="Duda")
        with self.assertRaises(ValidationError):
            self.revisar(intento, Decision.CONFIRMADO, motivo="", version=1)
        with self.assertRaises(ValidationError):
            self.revisar(intento, Decision.CONFIRMADO, motivo="Revisado", version=1, evidencia=False)
        confirmada = self.revisar(intento, Decision.CONFIRMADO, motivo="Revisado", version=1)
        self.assertEqual(confirmada.version, 2)

    def test_nuevo_analisis_no_hereda_la_aprobacion_anterior(self):
        primero = self.intento_completado()
        self.revisar(primero, Decision.CONFIRMADO)
        segundo = self.intento_completado(version_modelo="m2")
        self.assertIsNone(services.revision_vigente(segundo))
        self.assertEqual(list(services.intentos_pendientes_de_revision()), [segundo])
        self.revisar(segundo, Decision.RECHAZADO, motivo="Otro caso")
        self.assertEqual(services.revision_vigente(primero).decision, "CONFIRMADO")