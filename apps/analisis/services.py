"""Operaciones de dominio del análisis visual.

Los porcentajes son una estimación visual de área, no gramos ni volumen. Las
operaciones lanzan ValidationError con mensaje legible y no dejan filas
parciales. Las transiciones usan actualizaciones condicionales y restricciones
únicas (no select_for_update), para que funcionen igual con SQLite.
"""

import math
from datetime import timedelta
from decimal import ROUND_HALF_EVEN, Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.analisis.elegibilidad import evaluar_elegibilidad
from apps.analisis.models import (
    RETENCION_DIAS,
    AnalisisServicio,
    ArtefactoAnalisis,
    IntentoAnalisis,
    ResultadoComponente,
    RevisionAnalisis,
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
    comparable,
    oculto,
):
    """Devuelve dict(estado, porcentaje, motivo) para un componente.

    `comparable` y `oculto` son obligatorios: no existe un valor por defecto que
    certifique comparabilidad. Debe ser False si falta evidencia o aprobación.

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
    """Total = 100 x suma de residuales / suma de iniciales, si todos son válidos.

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
        "porcentaje": (
            _porcentaje(suma_inicial, suma_residual)
            if suma_inicial and not excluidos else None
        ),
        "incluidos": [r.servicio_componente.componente_codigo for r in incluidos],
        "excluidos": excluidos,
        "cobertura": f"{len(incluidos)}/{len(resultados)}",
        "completo": not excluidos and bool(resultados),
    }


# --- Precondiciones del par ---------------------------------------------------


def _verificar_precondiciones(servicio, foto_servido, foto_retorno):
    """Antes de solicitar, reclamar o completar: el par debe seguir siendo válido."""
    actual = Servicio.objects.get(pk=servicio.pk)
    if actual.estado_captura != Servicio.EstadoCaptura.PAR_COMPLETO:
        raise ValidationError("Solo se analizan servicios con el par completo y no anulados.")
    limite = timezone.now() - timedelta(days=RETENCION_DIAS)
    for foto, etapa in ((foto_servido, Etapa.SERVIDO), (foto_retorno, Etapa.RETORNO)):
        vigente = FotografiaServicio.objects.filter(
            pk=foto.pk, servicio=actual, etapa=etapa, vigente=True
        ).first()
        if vigente is None:
            raise ValidationError(f"La fotografía de {etapa} ya no es la vigente del servicio.")
        if vigente.eliminada_en is not None:
            raise ValidationError(f"La fotografía de {etapa} ya fue eliminada.")
        if vigente.fecha <= limite:
            raise ValidationError(f"La fotografía de {etapa} superó su plazo de conservación.")
    if not actual.composicion.exists():
        raise ValidationError("El servicio no tiene composición histórica.")


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
            raise ValidationError("Solo se analizan servicios con el par completo y no anulados.")
        fotos = {
            f.etapa: f
            for f in FotografiaServicio.objects.filter(servicio=actual, vigente=True)
        }
        if set(fotos) != {Etapa.SERVIDO, Etapa.RETORNO}:
            raise ValidationError("El servicio no tiene las dos fotografías vigentes.")
        _verificar_precondiciones(actual, fotos[Etapa.SERVIDO], fotos[Etapa.RETORNO])
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
    """Toma el intento pendiente más antiguo de forma condicional (varios workers).

    Antes de reclamar comprueba el par; un intento cuyas fotos ya no son válidas
    se cierra FALLIDO con el motivo y no se entrega al worker.
    """
    candidatos = list(
        IntentoAnalisis.objects.filter(estado=Estado.PENDIENTE)
        .order_by("creado_en")
        .values_list("pk", flat=True)[:10]
    )
    for pk in candidatos:
        intento = IntentoAnalisis.objects.select_related(
            "analisis__servicio", "analisis__foto_servido", "analisis__foto_retorno"
        ).get(pk=pk)
        if intento.estado != Estado.PENDIENTE:
            continue
        analisis = intento.analisis
        try:
            _verificar_precondiciones(
                analisis.servicio, analisis.foto_servido, analisis.foto_retorno
            )
        except ValidationError as error:
            IntentoAnalisis.objects.filter(pk=pk, estado=Estado.PENDIENTE).update(
                estado=Estado.FALLIDO,
                finalizado_en=timezone.now(),
                error_tipo=IntentoAnalisis.TipoError.OTRO,
                error_mensaje="Precondición no cumplida: " + "; ".join(error.messages),
            )
            continue
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


class _NoCompletado(Exception):
    pass


def completar_intento(
    *,
    intento,
    request_id,
    version_modelo,
    version_configuracion,
    origen,
    resultados,
    artefactos=(),
):
    """Persiste resultados y máscaras y marca COMPLETADO, todo o nada.

    request_id, version_modelo, version_configuracion y origen deben coincidir con
    los del intento y su análisis (un adaptador SIMULADO nunca pasa a REAL).
    resultados: dicts con servicio_componente, area_inicial, area_residual,
    comparable y oculto (obligatorios) y, opcionalmente, confianza,
    umbral_confianza y criterio. El umbral lo toma Lino de la configuración
    aprobada, nunca del navegador ni del motor. Un componente de la composición
    que no venga se guarda NO_CONCLUYENTE (SIN_DETECCION); uno ajeno o repetido
    invalida toda la respuesta.
    artefactos: dicts con servicio_componente, etapa, clave_archivo,
    hash_sha256, ancho, alto, y opcionalmente backend y version_id.
    El estado y el límite de tiempo se comprueban dentro de la misma
    actualización condicional que cierra el intento, sin carrera con el vencimiento.
    """
    actual = IntentoAnalisis.objects.select_related(
        "analisis__servicio", "analisis__foto_servido", "analisis__foto_retorno"
    ).get(pk=intento.pk)
    analisis = actual.analisis
    if actual.estado != Estado.EN_PROCESO:
        raise ValidationError("El intento ya está cerrado; la respuesta se descarta.")
    if str(request_id) != str(actual.pk):
        raise ValidationError("La respuesta no corresponde a este intento.")
    if (version_modelo, version_configuracion, origen) != (
        analisis.version_modelo,
        analisis.version_configuracion,
        analisis.origen,
    ):
        raise ValidationError(
            "La respuesta no coincide con el modelo, la configuración o el origen solicitados."
        )
    _verificar_precondiciones(analisis.servicio, analisis.foto_servido, analisis.foto_retorno)

    componentes = {c.pk: c for c in analisis.servicio.composicion.all()}
    filas, vistos = [], set()
    for item in resultados:
        comp = item["servicio_componente"]
        if comp.pk not in componentes or comp.pk in vistos:
            raise ValidationError("La respuesta incluye un componente no válido o repetido.")
        if "comparable" not in item or "oculto" not in item:
            raise ValidationError("Cada componente debe declarar explícitamente comparable y oculto.")
        vistos.add(comp.pk)
        evaluacion = evaluar_componente(
            area_inicial=item.get("area_inicial"),
            area_residual=item.get("area_residual"),
            confianza=item.get("confianza"),
            umbral_confianza=item.get("umbral_confianza"),
            comparable=item["comparable"],
            oculto=item["oculto"],
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

    fotos = {Etapa.SERVIDO: analisis.foto_servido, Etapa.RETORNO: analisis.foto_retorno}
    for art in artefactos:
        if art["servicio_componente"].pk not in componentes or art.get("etapa") not in fotos:
            raise ValidationError("La respuesta incluye una máscara no válida.")
        if not art.get("clave_archivo") or min(art.get("ancho", 0), art.get("alto", 0)) <= 0:
            raise ValidationError("Los datos de una máscara no son válidos.")

    try:
        with transaction.atomic():
            ahora = timezone.now()
            duracion = int((ahora - actual.comenzado_en).total_seconds() * 1000)
            cerrado = IntentoAnalisis.objects.filter(
                pk=actual.pk, estado=Estado.EN_PROCESO, limite_en__gte=ahora
            ).update(
                estado=Estado.COMPLETADO,
                finalizado_en=ahora,
                duracion_ms=duracion,
                request_id=str(request_id),
            )
            if cerrado != 1:
                raise _NoCompletado()
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
                    umbral_aplicado=item.get("umbral_confianza"),
                    configuracion_aprobada=item.get("umbral_confianza") is not None,
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
            AnalisisServicio.objects.filter(pk=analisis.pk).update(intento_vigente=actual)
    except _NoCompletado:
        posterior = IntentoAnalisis.objects.get(pk=actual.pk)
        if posterior.estado == Estado.EN_PROCESO and posterior.limite_en < timezone.now():
            _cerrar(posterior, Estado.TIEMPO_AGOTADO)
            raise ValidationError("La respuesta llegó después del límite de tiempo.")
        raise ValidationError("El intento ya no está en proceso.")
    return IntentoAnalisis.objects.get(pk=actual.pk)


# --- Retención -----------------------------------------------------------------


def artefactos_vencidos(ahora=None):
    """Máscaras cuyo plazo (el de su foto de origen) ya venció y siguen sin eliminar."""
    ahora = ahora or timezone.now()
    limite = ahora - timedelta(days=RETENCION_DIAS)
    return ArtefactoAnalisis.objects.filter(
        eliminado_en__isnull=True, foto_padre__fecha__lte=limite
    )


# --- Revisión humana (bloque 5) ---------------------------------------------------

Decision = RevisionAnalisis.Decision


class ConflictoRevision(ValidationError):
    """La revisión vigente cambió mientras el revisor preparaba su decisión."""


def revision_vigente(intento):
    return RevisionAnalisis.objects.filter(intento=intento, vigente=True).first()


def intentos_pendientes_de_revision():
    """Resultados vigentes de cada análisis, completados y sin revisión vigente."""
    vigentes = AnalisisServicio.objects.exclude(intento_vigente=None).values(
        "intento_vigente"
    )
    return (
        IntentoAnalisis.objects.filter(estado=Estado.COMPLETADO, pk__in=vigentes)
        .exclude(revisiones__vigente=True)
        .order_by("finalizado_en")
    )


_TEXTO_MOTIVO = {
    "ORIGEN_NO_REAL": "El análisis es simulado: no es evidencia real.",
    "INTENTO_NO_COMPLETADO": "El intento no está completado.",
    "SIN_CONFIGURACION_APROBADA": "Se aplicó una configuración sin aprobación.",
    "COMPONENTES_NO_CONCLUYENTES": "Hay componentes no concluyentes o no hay resultados.",
    "EVIDENCIA_NO_DISPONIBLE": "La evidencia (fotos y máscaras) no está disponible ahora.",
}


def _datos_elegibilidad(intento):
    """Datos verificados del servidor (nunca del formulario) para la regla compartida."""
    resultados = list(intento.resultados.all())
    return {
        "origen": intento.analisis.origen,
        "estado_intento": intento.estado,
        "estados_componentes": [r.estado for r in resultados],
        "configuracion_aprobada": bool(resultados)
        and all(r.configuracion_aprobada for r in resultados),
    }


def motivos_no_confirmable(intento, evidencia_disponible):
    """Razones legibles por las que NO se puede confirmar; vacía si se puede.

    Usa `evaluar_elegibilidad` (regla compartida de César): una confirmación
    humana no convierte en evidencia apta un resultado simulado, fallido, no
    concluyente, sin criterio aprobado o sin imágenes disponibles ahora.
    """
    evaluacion = evaluar_elegibilidad(
        **_datos_elegibilidad(intento), evidencia_disponible=evidencia_disponible is True
    )
    if evaluacion["puede_confirmar"]:
        return []
    return [_TEXTO_MOTIVO.get(codigo, codigo) for codigo in evaluacion["motivos"]]


def apto_historico(intento):
    """True si el intento tiene revisión vigente CONFIRMADO y validez técnica.

    No exige que los bytes sigan disponibles: una decisión válida anterior no
    se borra al vencer la retención. Un intento nuevo no hereda la anterior.
    """
    revision = revision_vigente(intento)
    if revision is None:
        return False
    evaluacion = evaluar_elegibilidad(
        **_datos_elegibilidad(intento),
        evidencia_disponible=False,
        decision=revision.decision,
        intento_id=intento.pk,
        intento_revisado_id=revision.intento_id,
    )
    return evaluacion["apto_historico"]


def revisar_resultado(
    resultado, decision, motivo, usuario, version_esperada, *, evidencia_disponible=False
):
    """Registra la decisión de Cocina sobre el intento exacto `resultado`.

    version_esperada: versión de la revisión vigente que el revisor vio (0 si
    no había). Si cambió, lanza ConflictoRevision sin escribir nada. Un POST
    repetido idéntico devuelve la revisión existente. Rechazar, marcar no
    concluyente y rectificar exigen motivo; la rectificación crea otra revisión
    que sustituye a la anterior, que se conserva. Confirmar exige que
    `motivos_no_confirmable` salga vacío; `evidencia_disponible` lo comprueba
    Lino contra el almacenamiento (por defecto False: no se confirma a ciegas).
    """
    if decision not in Decision.values:
        raise ValidationError("Decisión no válida.")
    if not (usuario and usuario.is_active and usuario.has_perm("analisis.add_revisionanalisis")):
        raise PermissionDenied("No tienes permiso para revisar análisis.")
    if not isinstance(version_esperada, int) or isinstance(version_esperada, bool) or version_esperada < 0:
        raise ValidationError("Versión esperada no válida.")
    motivo = (motivo or "").strip()

    with transaction.atomic():
        intento = IntentoAnalisis.objects.select_related("analisis").get(pk=resultado.pk)
        if intento.estado != Estado.COMPLETADO:
            raise ValidationError("Solo se revisan intentos completados.")
        if intento.analisis.intento_vigente_id != intento.pk:
            raise ValidationError("Este intento ya no es el resultado vigente del análisis.")

        vigente = revision_vigente(intento)
        actual = vigente.version if vigente else 0
        if (
            vigente
            and (vigente.decision, vigente.motivo, vigente.autor_id)
            == (decision, motivo, usuario.pk)
            and version_esperada in (actual - 1, actual)
        ):
            return vigente  # doble envío: no duplica
        if version_esperada != actual:
            raise ConflictoRevision(
                "La revisión cambió mientras la preparabas; vuelve a cargar el caso."
            )
        if (vigente or decision != Decision.CONFIRMADO) and not motivo:
            raise ValidationError("Esta decisión requiere un motivo.")
        if decision == Decision.CONFIRMADO:
            razones = motivos_no_confirmable(intento, evidencia_disponible)
            if razones:
                raise ValidationError(razones)
        if vigente:
            filas = RevisionAnalisis.objects.filter(
                pk=vigente.pk, vigente=True, version=actual
            ).update(vigente=False)
            if filas != 1:
                raise ConflictoRevision("La revisión cambió mientras la preparabas.")
        try:
            with transaction.atomic():
                return RevisionAnalisis.objects.create(
                    intento=intento,
                    decision=decision,
                    motivo=motivo,
                    autor=usuario,
                    sustituye=vigente,
                    version=actual + 1,
                )
        except IntegrityError:
            raise ConflictoRevision("Otra persona registró una decisión al mismo tiempo.")
