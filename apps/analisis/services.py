"""Operaciones de dominio del análisis visual.

Los porcentajes son una estimación visual de área, no gramos ni volumen. Las
operaciones lanzan ValidationError con mensaje legible y no dejan filas
parciales. Las transiciones usan actualizaciones condicionales y restricciones
únicas (no select_for_update), para que funcionen igual con SQLite.
"""

import math
from datetime import timedelta
from decimal import ROUND_HALF_EVEN, Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.analisis.models import (
    RETENCION_DIAS,
    AnalisisServicio,
    ArtefactoAnalisis,
    IntentoAnalisis,
    ResultadoComponente,
)
from apps.captura.models import FotografiaServicio, Servicio

SEGUNDOS_LIMITE_INTENTO = 30  # tiempo máximo real acordado

Estado = IntentoAnalisis.Estado
Resultado = ResultadoComponente.Estado
Motivo = ResultadoComponente.Motivo
Etapa = FotografiaServicio.Etapa
_ACTIVOS = [Estado.PENDIENTE, Estado.EN_PROCESO]
_REINTENTABLES = [Estado.FALLIDO, Estado.TIEMPO_AGOTADO]
_CUATRO_DECIMALES = Decimal("0.0001")


# --- Cálculo ----------------------------------------------------------------


def _finito(valor):
    try:
        return math.isfinite(float(valor))
    except (TypeError, ValueError):
        return False


def _porcentaje(inicial, residual):
    valor = Decimal(str(residual)) * 100 / Decimal(str(inicial))
    return valor.quantize(_CUATRO_DECIMALES, rounding=ROUND_HALF_EVEN)


def evaluar_componente(
    *,
    area_inicial,
    area_residual,
    confianza=None,
    umbral_confianza=None,
    comparable=True,
    oculto=False,
):
    """Devuelve dict(estado, porcentaje, motivo) para un componente.

    porcentaje = 100 x residual / inicial. Solo es CONCLUYENTE si el par es
    comparable, hay área inicial, detección evaluable, porcentaje <= 100 y la
    confianza alcanza el umbral configurado. Sin umbral nunca es concluyente.
    Un porcentaje > 100 se conserva (no se recorta). Sin detección no es 0 %.
    """
    for nombre, valor in (("inicial", area_inicial), ("residual", area_residual)):
        if valor is not None and (not _finito(valor) or float(valor) < 0):
            raise ValidationError(f"El área {nombre} no es un valor válido.")
    for nombre, valor in (("confianza", confianza), ("umbral", umbral_confianza)):
        if valor is not None and (not _finito(valor) or not 0 <= float(valor) <= 1):
            raise ValidationError(f"El valor de {nombre} debe estar entre 0 y 1.")

    def salida(estado, porcentaje=None, motivo=""):
        return {"estado": estado, "porcentaje": porcentaje, "motivo": motivo}

    no = Resultado.NO_CONCLUYENTE
    if not area_inicial:
        return salida(no, motivo=Motivo.AREA_INICIAL_CERO)
    if not comparable:
        return salida(no, motivo=Motivo.NO_COMPARABLE)
    if oculto:
        return salida(no, motivo=Motivo.OCULTACION)
    if area_residual is None:
        return salida(no, motivo=Motivo.SIN_DETECCION)

    porcentaje = _porcentaje(area_inicial, area_residual)
    if porcentaje > 100:
        return salida(no, porcentaje, Motivo.MAYOR_100)
    if umbral_confianza is None:
        return salida(no, porcentaje, Motivo.SIN_CRITERIO)
    if confianza is None or float(confianza) < float(umbral_confianza):
        return salida(no, porcentaje, Motivo.BAJA_CONFIANZA)
    return salida(Resultado.CONCLUYENTE, porcentaje)


def total_ponderado(resultados):
    """Total = 100 x suma de residuales / suma de iniciales, solo de los válidos.

    No promedia porcentajes. Declara los componentes excluidos y la cobertura.
    """
    resultados = list(resultados)
    incluidos = [
        r
        for r in resultados
        if r.estado == Resultado.CONCLUYENTE
        and r.area_inicial
        and r.area_residual is not None
    ]
    excluidos = [
        {"componente": r.servicio_componente.componente_codigo, "motivo": r.motivo}
        for r in resultados
        if r not in incluidos
    ]
    suma_inicial = sum(r.area_inicial for r in incluidos)
    suma_residual = sum(r.area_residual for r in incluidos)
    return {
        "porcentaje": _porcentaje(suma_inicial, suma_residual) if suma_inicial else None,
        "incluidos": [r.servicio_componente.componente_codigo for r in incluidos],
        "excluidos": excluidos,
        "cobertura": f"{len(incluidos)}/{len(resultados)}",
        "completo": not excluidos and bool(resultados),
    }


# --- Solicitud y reintentos ---------------------------------------------------


def _ultimo_intento(analisis):
    return analisis.intentos.order_by("-numero").first()


def solicitar_analisis(
    *, servicio, solicitante, version_modelo, version_configuracion, origen="REAL"
):
    """Crea (o recupera) el análisis del par y su primer intento.

    Devuelve (analisis, intento, creado). Una solicitud repetida del mismo par,
    modelo y configuración no duplica trabajo: devuelve el intento existente.
    """
    if origen not in AnalisisServicio.Origen.values:
        raise ValidationError("Origen de análisis no válido.")
    if not version_modelo or not version_configuracion:
        raise ValidationError("Faltan la versión del modelo o de la configuración.")
    with transaction.atomic():
        actual = Servicio.objects.get(pk=servicio.pk)
        if actual.estado_captura != Servicio.EstadoCaptura.PAR_COMPLETO:
            raise ValidationError("Solo se analizan servicios con el par completo.")
        fotos = {
            f.etapa: f
            for f in FotografiaServicio.objects.filter(servicio=actual, vigente=True)
        }
        if set(fotos) != {Etapa.SERVIDO, Etapa.RETORNO}:
            raise ValidationError("El servicio no tiene las dos fotografías vigentes.")
        analisis, _ = AnalisisServicio.objects.get_or_create(
            foto_servido=fotos[Etapa.SERVIDO],
            foto_retorno=fotos[Etapa.RETORNO],
            version_modelo=version_modelo,
            version_configuracion=version_configuracion,
            origen=origen,
            defaults={"servicio": actual, "solicitante": solicitante},
        )
        existente = _ultimo_intento(analisis)
        if existente is not None:
            return analisis, existente, False
        try:
            with transaction.atomic():
                intento = IntentoAnalisis.objects.create(analisis=analisis, numero=1)
        except IntegrityError:
            return analisis, _ultimo_intento(analisis), False
        return analisis, intento, True


def reintentar_analisis(*, analisis):
    """Crea un intento nuevo si el último falló o agotó el tiempo."""
    with transaction.atomic():
        ultimo = _ultimo_intento(analisis)
        if ultimo is None or ultimo.estado not in _REINTENTABLES:
            raise ValidationError("Solo se reintenta un intento fallido o con tiempo agotado.")
        try:
            with transaction.atomic():
                return IntentoAnalisis.objects.create(
                    analisis=analisis, numero=ultimo.numero + 1
                )
        except IntegrityError:
            raise ValidationError("Ya existe un reintento en curso.")


# --- Worker --------------------------------------------------------------------


def reclamar_siguiente_intento():
    """Toma el intento pendiente más antiguo de forma condicional (varios workers)."""
    candidatos = list(
        IntentoAnalisis.objects.filter(estado=Estado.PENDIENTE)
        .order_by("creado_en")
        .values_list("pk", flat=True)[:10]
    )
    for pk in candidatos:
        ahora = timezone.now()
        filas = IntentoAnalisis.objects.filter(pk=pk, estado=Estado.PENDIENTE).update(
            estado=Estado.EN_PROCESO,
            comenzado_en=ahora,
            limite_en=ahora + timedelta(seconds=SEGUNDOS_LIMITE_INTENTO),
        )
        if filas == 1:
            return IntentoAnalisis.objects.select_related("analisis").get(pk=pk)
    return None


def _cerrar(intento, estado, **extra):
    """Cierra un intento EN_PROCESO; devuelve False si ya no lo estaba."""
    consulta = IntentoAnalisis.objects.filter(pk=intento.pk, estado=Estado.EN_PROCESO)
    comenzado = consulta.values_list("comenzado_en", flat=True).first()
    ahora = timezone.now()
    duracion = int((ahora - comenzado).total_seconds() * 1000) if comenzado else None
    return (
        consulta.update(
            estado=estado, finalizado_en=ahora, duracion_ms=duracion, **extra
        )
        == 1
    )


def fallar_intento(*, intento, tipo_error, mensaje=""):
    if tipo_error not in IntentoAnalisis.TipoError.values:
        raise ValidationError("Tipo de error no válido.")
    if not _cerrar(intento, Estado.FALLIDO, error_tipo=tipo_error, error_mensaje=mensaje):
        raise ValidationError("El intento ya no está en proceso.")


def agotar_tiempo(*, intento):
    if not _cerrar(intento, Estado.TIEMPO_AGOTADO):
        raise ValidationError("El intento ya no está en proceso.")


def cerrar_intentos_vencidos():
    """Cierra como TIEMPO_AGOTADO los intentos en proceso que pasaron su límite."""
    vencidos = IntentoAnalisis.objects.filter(
        estado=Estado.EN_PROCESO, limite_en__lt=timezone.now()
    )
    return sum(_cerrar(i, Estado.TIEMPO_AGOTADO) for i in vencidos)


def completar_intento(*, intento, resultados, artefactos=(), request_id=""):
    """Persiste resultados y máscaras y marca COMPLETADO, todo o nada.

    resultados: dicts con servicio_componente, area_inicial, area_residual y,
    opcionalmente, confianza, umbral_confianza, comparable, oculto, criterio.
    Un componente de la composición que no venga se guarda NO_CONCLUYENTE
    (SIN_DETECCION); uno que no pertenezca al servicio invalida la respuesta.
    artefactos: dicts con servicio_componente, etapa, clave_archivo,
    hash_sha256, ancho, alto, y opcionalmente backend y version_id.
    Una respuesta tardía o para un intento cerrado se descarta.
    """
    actual = IntentoAnalisis.objects.select_related(
        "analisis__servicio", "analisis__foto_servido", "analisis__foto_retorno"
    ).get(pk=intento.pk)
    if actual.estado != Estado.EN_PROCESO:
        raise ValidationError("El intento ya está cerrado; la respuesta se descarta.")
    if timezone.now() > actual.limite_en:
        _cerrar(actual, Estado.TIEMPO_AGOTADO)
        raise ValidationError("La respuesta llegó después del límite de tiempo.")

    componentes = {c.pk: c for c in actual.analisis.servicio.composicion.all()}
    filas, vistos = [], set()
    for item in resultados:
        comp = item["servicio_componente"]
        if comp.pk not in componentes or comp.pk in vistos:
            raise ValidationError("La respuesta incluye un componente no válido o repetido.")
        vistos.add(comp.pk)
        evaluacion = evaluar_componente(
            area_inicial=item.get("area_inicial"),
            area_residual=item.get("area_residual"),
            confianza=item.get("confianza"),
            umbral_confianza=item.get("umbral_confianza"),
            comparable=item.get("comparable", True),
            oculto=item.get("oculto", False),
        )
        filas.append((comp, item, evaluacion))
    for pk, comp in componentes.items():
        if pk not in vistos:
            filas.append(
                (
                    comp,
                    {},
                    {
                        "estado": Resultado.NO_CONCLUYENTE,
                        "porcentaje": None,
                        "motivo": Motivo.SIN_DETECCION,
                    },
                )
            )

    fotos = {Etapa.SERVIDO: actual.analisis.foto_servido, Etapa.RETORNO: actual.analisis.foto_retorno}
    for art in artefactos:
        if art["servicio_componente"].pk not in componentes or art.get("etapa") not in fotos:
            raise ValidationError("La respuesta incluye una máscara no válida.")
        if not art.get("clave_archivo") or min(art.get("ancho", 0), art.get("alto", 0)) <= 0:
            raise ValidationError("Los datos de una máscara no son válidos.")

    with transaction.atomic():
        if not _cerrar(
            actual, Estado.COMPLETADO, request_id=request_id
        ):
            raise ValidationError("El intento ya no está en proceso.")
        creados = {}
        for comp, item, ev in filas:
            creados[comp.pk] = ResultadoComponente.objects.create(
                intento=actual,
                servicio_componente=comp,
                area_inicial=item.get("area_inicial"),
                area_residual=item.get("area_residual"),
                porcentaje=ev["porcentaje"],
                confianza=item.get("confianza"),
                criterio=item.get("criterio", ""),
                estado=ev["estado"],
                motivo=ev["motivo"],
            )
        for art in artefactos:
            ArtefactoAnalisis.objects.create(
                resultado=creados[art["servicio_componente"].pk],
                etapa=art["etapa"],
                foto_padre=fotos[art["etapa"]],
                backend=art.get("backend", "local"),
                clave_archivo=art["clave_archivo"],
                hash_sha256=art.get("hash_sha256", ""),
                ancho=art["ancho"],
                alto=art["alto"],
                version_id=art.get("version_id", ""),
            )
        AnalisisServicio.objects.filter(pk=actual.analisis_id).update(
            intento_vigente=actual
        )
    return IntentoAnalisis.objects.get(pk=actual.pk)


# --- Retención -----------------------------------------------------------------


def artefactos_vencidos(ahora=None):
    """Máscaras cuyo plazo (el de su foto de origen) ya venció y siguen sin eliminar."""
    ahora = ahora or timezone.now()
    limite = ahora - timedelta(days=RETENCION_DIAS)
    return ArtefactoAnalisis.objects.filter(
        eliminado_en__isnull=True, foto_padre__fecha__lte=limite
    )