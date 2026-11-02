from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.analisis import services
from apps.analisis.models import (
    AnalisisServicio,
    ArtefactoAnalisis,
    IntentoAnalisis,
    ResultadoComponente,
)
from apps.captura.models import FotografiaServicio, Servicio
from apps.catalogo.models import Plato, TipoPorcion

Estado = IntentoAnalisis.Estado
Res = ResultadoComponente.Estado
Motivo = ResultadoComponente.Motivo
Etapa = FotografiaServicio.Etapa


class CalculoTests(SimpleTestCase):
    def evaluar(self, inicial=1000, residual=250, confianza=0.9, umbral=0.5,
                comparable=True, oculto=False):
        return services.evaluar_componente(
            area_inicial=inicial,
            area_residual=residual,
            confianza=confianza,
            umbral_confianza=umbral,
            comparable=comparable,
            oculto=oculto,
        )

    def test_porcentaje_visual_concluyente(self):
        r = self.evaluar()
        self.assertEqual(r["estado"], Res.CONCLUYENTE)
        self.assertEqual(r["porcentaje"], Decimal("25.0000"))

    def test_residuo_cero_evaluable_es_cero_concluyente(self):
        r = self.evaluar(residual=0)
        self.assertEqual((r["estado"], r["porcentaje"]), (Res.CONCLUYENTE, Decimal("0.0000")))

    def test_sin_deteccion_no_es_cero(self):
        r = self.evaluar(residual=None)
        self.assertEqual((r["estado"], r["porcentaje"], r["motivo"]),
                         (Res.NO_CONCLUYENTE, None, Motivo.SIN_DETECCION))

    def test_area_inicial_cero_o_ausente(self):
        for inicial in (0, None):
            r = self.evaluar(inicial=inicial)
            self.assertEqual((r["porcentaje"], r["motivo"]), (None, Motivo.AREA_INICIAL_CERO))

    def test_porcentaje_mayor_a_100_se_conserva_sin_recortar(self):
        r = self.evaluar(inicial=100, residual=150)
        self.assertEqual(r["estado"], Res.NO_CONCLUYENTE)
        self.assertEqual(r["motivo"], Motivo.MAYOR_100)
        self.assertEqual(r["porcentaje"], Decimal("150.0000"))

    def test_baja_confianza_y_sin_criterio_no_son_concluyentes(self):
        baja = self.evaluar(confianza=0.2)
        self.assertEqual((baja["estado"], baja["motivo"]), (Res.NO_CONCLUYENTE, Motivo.BAJA_CONFIANZA))
        sin = self.evaluar(umbral=None)
        self.assertEqual((sin["estado"], sin["motivo"]), (Res.NO_CONCLUYENTE, Motivo.SIN_CRITERIO))
        sin_conf = self.evaluar(confianza=None)
        self.assertEqual(sin_conf["motivo"], Motivo.BAJA_CONFIANZA)

    def test_ocultacion_y_no_comparable(self):
        self.assertEqual(self.evaluar(oculto=True)["motivo"], Motivo.OCULTACION)
        self.assertEqual(self.evaluar(comparable=False)["motivo"], Motivo.NO_COMPARABLE)
        self.assertIsNone(self.evaluar(oculto=True)["porcentaje"])

    def test_valores_no_finitos_o_negativos_se_rechazan(self):
        for malo in (float("nan"), float("inf"), -1, "x"):
            with self.assertRaises(ValidationError):
                self.evaluar(residual=malo)
        with self.assertRaises(ValidationError):
            self.evaluar(confianza=1.5)

    def test_total_ponderado_no_promedia_porcentajes(self):
        class Comp:
            def __init__(self, codigo):
                self.componente_codigo = codigo

        class R:
            def __init__(self, codigo, ini, res, estado=Res.CONCLUYENTE, motivo=""):
                self.servicio_componente = Comp(codigo)
                self.area_inicial, self.area_residual = ini, res
                self.estado, self.motivo = estado, motivo

        total = services.total_ponderado([
            R("arroz", 100, 50),
            R("pollo", 300, 0),
            R("maduro", None, None, Res.NO_CONCLUYENTE, Motivo.OCULTACION),
        ])
        self.assertEqual(total["porcentaje"], Decimal("12.5000"))  # no 25 (promedio)
        self.assertEqual(total["cobertura"], "2/3")
        self.assertFalse(total["completo"])
        self.assertEqual(total["excluidos"], [{"componente": "maduro", "motivo": Motivo.OCULTACION}])


class BaseAnalisis(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        self.usuario = get_user_model().objects.create_user("operador_analisis")
        self.servicio, self.servido, self.retorno = self.crear_par()
        self.comps = list(self.servicio.composicion.all())

    def crear_par(self):
        servicio = Servicio.registrar(
            plato=Plato.objects.get(codigo="seco_de_pollo"),
            porcion=TipoPorcion.objects.get(codigo="estandar"),
            usuario=self.usuario,
        )
        fotos = []
        for etapa in (Etapa.SERVIDO, Etapa.RETORNO):
            fotos.append(FotografiaServicio.objects.create(
                servicio=servicio, etapa=etapa, clave_archivo=f"k/{servicio.pk}/{etapa}",
                tipo_contenido="image/jpeg", tamano_bytes=10, ancho=4, alto=4,
                autor=self.usuario,
            ))
        Servicio.objects.filter(pk=servicio.pk).update(
            estado_captura=Servicio.EstadoCaptura.PAR_COMPLETO
        )
        servicio.refresh_from_db()
        return servicio, fotos[0], fotos[1]

    def solicitar(self, **cambios):
        datos = dict(servicio=self.servicio, solicitante=self.usuario,
                     version_modelo="m1", version_configuracion="c1", origen="REAL")
        datos.update(cambios)
        return services.solicitar_analisis(**datos)

    def en_proceso(self):
        _, intento, _ = self.solicitar()
        return services.reclamar_siguiente_intento()

    def respuesta(self, **cambios):
        item = lambda c, ini=1000, res=250: dict(
            servicio_componente=c, area_inicial=ini, area_residual=res,
            confianza=0.9, umbral_confianza=0.5, criterio="demo-v1",
            comparable=True, oculto=False)
        return [item(c) for c in self.comps]

    def completar(self, intento, resultados=None, artefactos=(), **cambios):
        datos = dict(
            intento=intento, request_id=str(intento.pk), version_modelo="m1",
            version_configuracion="c1", origen="REAL",
            resultados=self.respuesta() if resultados is None else resultados,
            artefactos=artefactos)
        datos.update(cambios)
        return services.completar_intento(**datos)


class SolicitudTests(BaseAnalisis):
    def test_solicitud_crea_analisis_con_fotos_exactas_y_primer_intento(self):
        analisis, intento, creado = self.solicitar()
        self.assertTrue(creado)
        self.assertEqual((analisis.foto_servido, analisis.foto_retorno), (self.servido, self.retorno))
        self.assertEqual((intento.numero, intento.estado), (1, Estado.PENDIENTE))

    def test_solicitud_repetida_no_duplica_trabajo(self):
        a1, i1, _ = self.solicitar()
        a2, i2, creado = self.solicitar()
        self.assertFalse(creado)
        self.assertEqual((a1.pk, i1.pk), (a2.pk, i2.pk))
        self.assertEqual(AnalisisServicio.objects.count(), 1)
        self.assertEqual(IntentoAnalisis.objects.count(), 1)

    def test_otra_version_u_origen_es_otro_analisis(self):
        self.solicitar()
        self.solicitar(version_modelo="m2")
        self.solicitar(origen="SIMULADO")
        self.assertEqual(AnalisisServicio.objects.count(), 3)

    def test_solo_pares_completos(self):
        for estado in ("", "PENDIENTE_SERVIDO", "EN_ESPERA_RETORNO", "ANULADO"):
            Servicio.objects.filter(pk=self.servicio.pk).update(estado_captura=estado)
            with self.assertRaises(ValidationError):
                self.solicitar()
        self.assertEqual(AnalisisServicio.objects.count(), 0)

    def test_falta_una_foto_vigente(self):
        FotografiaServicio.objects.filter(pk=self.retorno.pk).update(vigente=False)
        with self.assertRaises(ValidationError):
            self.solicitar()

    def test_origen_y_versiones_validos(self):
        with self.assertRaises(ValidationError):
            self.solicitar(origen="OTRO")
        with self.assertRaises(ValidationError):
            self.solicitar(version_modelo="")

    def test_un_solo_intento_activo_por_analisis_en_la_base(self):
        analisis, _, _ = self.solicitar()
        with self.assertRaises(IntegrityError), transaction.atomic():
            IntentoAnalisis.objects.create(analisis=analisis, numero=2)


class WorkerTests(BaseAnalisis):
    def test_reclamo_condicional_con_limite_de_30_segundos(self):
        self.solicitar()
        intento = services.reclamar_siguiente_intento()
        self.assertEqual(intento.estado, Estado.EN_PROCESO)
        self.assertEqual(intento.limite_en - intento.comenzado_en,
                         timedelta(seconds=services.SEGUNDOS_LIMITE_INTENTO))
        self.assertEqual(services.SEGUNDOS_LIMITE_INTENTO, 30)
        self.assertIsNone(services.reclamar_siguiente_intento())  # segundo worker

    def test_completar_persiste_resultados_y_publica_el_vigente(self):
        intento = self.en_proceso()
        art = dict(servicio_componente=self.comps[0], etapa="SERVIDO", clave_archivo="m/1",
                   hash_sha256="a" * 64, ancho=4, alto=4)
        hecho = self.completar(intento, artefactos=[art])
        self.assertEqual(hecho.estado, Estado.COMPLETADO)
        self.assertIsNotNone(hecho.duracion_ms)
        self.assertEqual(hecho.analisis.intento_vigente_id, hecho.pk)
        self.assertEqual(hecho.resultados.count(), len(self.comps))
        self.assertTrue(all(r.estado == Res.CONCLUYENTE for r in hecho.resultados.all()))
        mascara = ArtefactoAnalisis.objects.get()
        self.assertEqual(mascara.foto_padre, self.servido)

    def test_componente_ausente_es_no_concluyente_sin_deteccion(self):
        intento = self.en_proceso()
        parcial = self.respuesta()[:-1]
        faltante = self.comps[-1]
        hecho = self.completar(intento, resultados=parcial)
        r = hecho.resultados.get(servicio_componente=faltante)
        self.assertEqual((r.estado, r.motivo, r.porcentaje), (Res.NO_CONCLUYENTE, Motivo.SIN_DETECCION, None))

    def test_componente_desconocido_invalida_y_no_deja_nada(self):
        intento = self.en_proceso()
        otro, _, _ = self.crear_par()
        ajeno = otro.composicion.first()
        mala = self.respuesta()
        mala[0]["servicio_componente"] = ajeno
        with self.assertRaises(ValidationError):
            self.completar(intento, resultados=mala)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, Estado.EN_PROCESO)
        self.assertEqual(ResultadoComponente.objects.count(), 0)

    def test_valor_invalido_no_persiste_nada(self):
        intento = self.en_proceso()
        mala = self.respuesta()
        mala[0]["area_residual"] = float("nan")
        with self.assertRaises(ValidationError):
            self.completar(intento, resultados=mala)
        self.assertEqual(ResultadoComponente.objects.count(), 0)
        intento.refresh_from_db()
        self.assertIsNone(intento.analisis.intento_vigente)

    def test_respuesta_tardia_cierra_por_tiempo_y_no_publica_resultados(self):
        intento = self.en_proceso()
        IntentoAnalisis.objects.filter(pk=intento.pk).update(
            limite_en=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValidationError):
            self.completar(intento)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, Estado.TIEMPO_AGOTADO)
        self.assertEqual(ResultadoComponente.objects.count(), 0)
        self.assertIsNone(intento.analisis.intento_vigente)

    def test_intento_cerrado_descarta_respuestas_y_no_duplica(self):
        intento = self.en_proceso()
        self.completar(intento)
        total = ResultadoComponente.objects.count()
        with self.assertRaises(ValidationError):
            self.completar(intento)
        self.assertEqual(ResultadoComponente.objects.count(), total)

    def test_fallo_y_reintento_conservan_el_historial(self):
        intento = self.en_proceso()
        services.fallar_intento(intento=intento, tipo_error="ERROR_MOTOR", mensaje="motor caído")
        intento.refresh_from_db()
        self.assertEqual((intento.estado, intento.error_tipo), (Estado.FALLIDO, "ERROR_MOTOR"))
        with self.assertRaises(ValidationError):
            services.fallar_intento(intento=intento, tipo_error="OTRO")  # ya cerrado
        nuevo = services.reintentar_analisis(analisis=intento.analisis)
        self.assertEqual((nuevo.numero, nuevo.estado), (2, Estado.PENDIENTE))
        self.assertEqual(intento.analisis.intentos.count(), 2)
        with self.assertRaises(ValidationError):  # ya hay uno activo
            services.reintentar_analisis(analisis=intento.analisis)

    def test_no_se_reintenta_un_intento_completado(self):
        intento = self.en_proceso()
        self.completar(intento)
        with self.assertRaises(ValidationError):
            services.reintentar_analisis(analisis=intento.analisis)

    def test_cerrar_intentos_vencidos(self):
        intento = self.en_proceso()
        IntentoAnalisis.objects.filter(pk=intento.pk).update(
            limite_en=timezone.now() - timedelta(seconds=1))
        self.assertEqual(services.cerrar_intentos_vencidos(), 1)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, Estado.TIEMPO_AGOTADO)
        self.assertEqual(services.cerrar_intentos_vencidos(), 0)

    def test_base_impide_concluyente_sin_porcentaje_o_no_concluyente_sin_motivo(self):
        intento = self.en_proceso()
        comp = self.comps[0]
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResultadoComponente.objects.create(
                intento=intento, servicio_componente=comp, estado=Res.CONCLUYENTE)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ResultadoComponente.objects.create(
                intento=intento, servicio_componente=comp, estado=Res.NO_CONCLUYENTE)


class ContratoTests(BaseAnalisis):
    def test_comparable_y_oculto_son_obligatorios_en_la_respuesta(self):
        intento = self.en_proceso()
        for campo in ("comparable", "oculto"):
            mala = self.respuesta()
            del mala[0][campo]
            with self.assertRaises(ValidationError):
                self.completar(intento, resultados=mala)
        self.assertEqual(ResultadoComponente.objects.count(), 0)
        with self.assertRaises(TypeError):
            services.evaluar_componente(area_inicial=1, area_residual=1)

    def test_comparable_falso_deja_el_resultado_no_concluyente(self):
        intento = self.en_proceso()
        respuesta = self.respuesta()
        for item in respuesta:
            item["comparable"] = False
        hecho = self.completar(intento, resultados=respuesta)
        self.assertTrue(all(r.motivo == Motivo.NO_COMPARABLE for r in hecho.resultados.all()))
        self.assertTrue(all(r.porcentaje is None for r in hecho.resultados.all()))

    def test_respuesta_de_otro_intento_modelo_configuracion_u_origen(self):
        intento = self.en_proceso()
        for cambio in (dict(request_id="otro"), dict(version_modelo="m9"),
                       dict(version_configuracion="c9"), dict(origen="SIMULADO")):
            with self.assertRaises(ValidationError):
                self.completar(intento, **cambio)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, Estado.EN_PROCESO)
        self.assertEqual(ResultadoComponente.objects.count(), 0)

    def test_un_simulado_nunca_se_convierte_en_real(self):
        self.solicitar(origen="SIMULADO")
        intento = services.reclamar_siguiente_intento()
        with self.assertRaises(ValidationError):
            self.completar(intento, origen="REAL", version_modelo="m1", version_configuracion="c1")

    def test_fotos_vencidas_se_detectan_antes_de_reclamar(self):
        _, pendiente, _ = self.solicitar()
        FotografiaServicio.objects.filter(pk=self.retorno.pk).update(
            fecha=timezone.now() - timedelta(days=91))
        self.assertIsNone(services.reclamar_siguiente_intento())
        pendiente.refresh_from_db()
        self.assertEqual(pendiente.estado, Estado.FALLIDO)
        self.assertIn("conservación", pendiente.error_mensaje)

    def romper_y_completar(self, romper):
        intento = self.en_proceso()
        romper()
        with self.assertRaises(ValidationError):
            self.completar(intento)
        self.assertEqual(ResultadoComponente.objects.count(), 0)

    def test_no_se_completa_con_una_foto_que_dejo_de_ser_vigente(self):
        self.romper_y_completar(lambda: FotografiaServicio.objects.filter(
            pk=self.servido.pk).update(vigente=False))

    def test_no_se_completa_con_una_foto_vencida(self):
        self.romper_y_completar(lambda: FotografiaServicio.objects.filter(
            pk=self.retorno.pk).update(fecha=timezone.now() - timedelta(days=91)))

    def test_no_se_completa_si_el_servicio_fue_anulado(self):
        self.romper_y_completar(lambda: Servicio.objects.filter(
            pk=self.servicio.pk).update(estado_captura="ANULADO"))

    def test_solicitar_rechaza_fotos_vencidas(self):
        FotografiaServicio.objects.filter(pk=self.servido.pk).update(
            fecha=timezone.now() - timedelta(days=91))
        with self.assertRaises(ValidationError):
            self.solicitar()
        self.assertEqual(AnalisisServicio.objects.count(), 0)

    def test_solicitar_rechaza_servicio_sin_composicion(self):
        self.servicio.composicion.all().delete()
        with self.assertRaises(ValidationError):
            self.solicitar()

    def test_limite_se_comprueba_en_la_misma_actualizacion_que_cierra(self):
        intento = self.en_proceso()
        IntentoAnalisis.objects.filter(pk=intento.pk).update(
            limite_en=timezone.now() - timedelta(milliseconds=1))
        with self.assertRaises(ValidationError) as error:
            self.completar(intento)
        self.assertIn("límite de tiempo", str(error.exception))
        intento.refresh_from_db()
        self.assertEqual(intento.estado, Estado.TIEMPO_AGOTADO)
        self.assertEqual(ResultadoComponente.objects.count(), 0)


class RetencionTests(BaseAnalisis):
    def hacer_mascara(self):
        intento = self.en_proceso()
        art = dict(servicio_componente=self.comps[0], etapa="RETORNO", clave_archivo="m/2",
                   hash_sha256="b" * 64, ancho=4, alto=4)
        self.completar(intento, artefactos=[art])
        return ArtefactoAnalisis.objects.get()

    def test_la_mascara_hereda_el_plazo_de_la_foto_de_origen(self):
        mascara = self.hacer_mascara()
        self.assertEqual(mascara.vence_en, self.retorno.fecha + timedelta(days=90))
        self.assertEqual(services.artefactos_vencidos().count(), 0)
        FotografiaServicio.objects.filter(pk=self.retorno.pk).update(
            fecha=timezone.now() - timedelta(days=91))
        self.assertEqual(list(services.artefactos_vencidos()), [mascara])

    def test_una_mascara_ya_eliminada_no_se_lista(self):
        mascara = self.hacer_mascara()
        FotografiaServicio.objects.filter(pk=self.retorno.pk).update(
            fecha=timezone.now() - timedelta(days=100))
        ArtefactoAnalisis.objects.filter(pk=mascara.pk).update(eliminado_en=timezone.now())
        self.assertEqual(services.artefactos_vencidos().count(), 0)