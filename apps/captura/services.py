"""Operaciones de dominio de bandejas y capturas.

Todas son atómicas y lanzan ValidationError con un mensaje legible cuando la
operación no es válida; en ese caso no queda ninguna fila parcial. Las
transiciones de estado usan actualizaciones condicionales y restricciones
únicas (no select_for_update), para que funcionen igual con SQLite.
"""

import hashlib
import secrets
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.captura.models import (
    AsignacionBandeja,
    Bandeja,
    EtiquetaBandeja,
    FotografiaServicio,
    Servicio,
    SesionCaptura,
)

Estado = Servicio.EstadoCaptura
Etapa = FotografiaServicio.Etapa


def _transicion(servicio, desde, hacia, **extra):
    """Cambia el estado solo si sigue siendo `desde`; si no, rechaza."""
    filas = Servicio.objects.filter(pk=servicio.pk, estado_captura=desde).update(
        estado_captura=hacia, **extra
    )
    if filas != 1:
        raise ValidationError(
            "El servicio no está en un estado que permita esta operación."
        )


def _cerrar_asignacion(servicio):
    AsignacionBandeja.objects.filter(servicio=servicio, fin__isnull=True).update(
        fin=timezone.now()
    )


def asignar_bandeja(*, servicio, bandeja):
    """Asigna una bandeja activa a un servicio pendiente de servido."""
    with transaction.atomic():
        if not Bandeja.objects.filter(pk=bandeja.pk, activo=True).exists():
            raise ValidationError("La bandeja no existe o no está activa.")
        if not Servicio.objects.filter(
            pk=servicio.pk, estado_captura=Estado.PENDIENTE_SERVIDO
        ).exists():
            raise ValidationError(
                "Solo se puede asignar una bandeja a un servicio pendiente de servido."
            )
        try:
            with transaction.atomic():
                return AsignacionBandeja.objects.create(
                    servicio=servicio, bandeja=bandeja
                )
        except IntegrityError:
            raise ValidationError(
                "La bandeja ya está asignada o el servicio ya tiene una bandeja."
            )


def registrar_captura(
    *,
    servicio,
    etapa,
    clave_archivo,
    tipo_contenido,
    tamano_bytes,
    ancho,
    alto,
    autor,
    backend="local",
    hash_sha256="",
    version_id="",
):
    """Guarda los metadatos de una fotografía ya almacenada y avanza el estado.

    SERVIDO: pendiente -> en espera de retorno.
    RETORNO: en espera -> par completo y libera la bandeja (todo en una
    transacción). El archivo se guarda antes, fuera de esta transacción.
    """
    if etapa not in Etapa.values:
        raise ValidationError("Etapa de captura no válida.")
    if min(tamano_bytes, ancho, alto) <= 0 or not clave_archivo:
        raise ValidationError("Los datos de la fotografía no son válidos.")

    datos = dict(
        servicio=servicio,
        etapa=etapa,
        backend=backend,
        hash_sha256=hash_sha256,
        version_id=version_id,
        clave_archivo=clave_archivo,
        tipo_contenido=tipo_contenido,
        tamano_bytes=tamano_bytes,
        ancho=ancho,
        alto=alto,
        autor=autor,
    )
    with transaction.atomic():
        if etapa == Etapa.SERVIDO:
            _transicion(servicio, Estado.PENDIENTE_SERVIDO, Estado.EN_ESPERA_RETORNO)
        elif not Servicio.objects.filter(
            pk=servicio.pk, estado_captura=Estado.EN_ESPERA_RETORNO
        ).exists():
            raise ValidationError(
                "No se puede registrar el retorno: el servicio no está en espera de retorno."
            )
        try:
            with transaction.atomic():
                foto = FotografiaServicio.objects.create(**datos)
        except IntegrityError:
            raise ValidationError("Ese servicio ya tiene una fotografía en esa etapa.")
        if etapa == Etapa.RETORNO:
            completar_par(servicio=servicio)
        return foto


def completar_par(*, servicio):
    """Cierra el par servido/retorno y libera la bandeja."""
    with transaction.atomic():
        vigentes = set(
            FotografiaServicio.objects.filter(servicio=servicio, vigente=True)
            .values_list("etapa", flat=True)
        )
        if vigentes != {Etapa.SERVIDO, Etapa.RETORNO}:
            raise ValidationError("Faltan fotografías para completar el par.")
        _transicion(servicio, Estado.EN_ESPERA_RETORNO, Estado.PAR_COMPLETO)
        _cerrar_asignacion(servicio)


def anular_servicio(*, servicio, motivo, usuario):
    """Anula un servicio no completado, con motivo y responsable; libera la bandeja."""
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("La anulación requiere un motivo.")
    with transaction.atomic():
        filas = Servicio.objects.filter(
            pk=servicio.pk,
            estado_captura__in=[Estado.PENDIENTE_SERVIDO, Estado.EN_ESPERA_RETORNO],
        ).update(
            estado_captura=Estado.ANULADO,
            anulado_motivo=motivo,
            anulado_por=usuario,
            anulado_en=timezone.now(),
        )
        if filas != 1:
            raise ValidationError("El servicio no se puede anular en su estado actual.")
        _cerrar_asignacion(servicio)


def emitir_etiqueta(*, bandeja):
    """Crea la etiqueta vigente de una bandeja que no tiene ninguna vigente."""
    with transaction.atomic():
        try:
            with transaction.atomic():
                return EtiquetaBandeja.objects.create(bandeja=bandeja)
        except IntegrityError:
            raise ValidationError("La bandeja ya tiene una etiqueta vigente.")


def reemplazar_etiqueta(*, bandeja, motivo, usuario):
    """Revoca la etiqueta vigente y emite una nueva para la misma bandeja.

    Exige motivo y responsable; la revocación guarda motivo, autor y fecha.
    No toca asignaciones: una comida nunca cambia de bandeja por esto.
    """
    motivo = (motivo or "").strip()
    if not motivo:
        raise ValidationError("El reemplazo de etiqueta requiere un motivo.")
    with transaction.atomic():
        EtiquetaBandeja.objects.filter(
            bandeja=bandeja, revocada_en__isnull=True
        ).update(
            revocada_en=timezone.now(),
            revocada_por=usuario,
            motivo_revocacion=motivo,
        )
        return emitir_etiqueta(bandeja=bandeja)


# --- Sesión de captura temporal (bloque 3) ---------------------------------

MINUTOS_SESION_CAPTURA = 5  # cambiarlo exige modificar el contrato y las pruebas
Sesion = SesionCaptura.Estado
_ESTADO_REQUERIDO = {
    Etapa.SERVIDO: Estado.PENDIENTE_SERVIDO,
    Etapa.RETORNO: Estado.EN_ESPERA_RETORNO,
}


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def crear_sesion_captura(*, servicio, etapa, usuario):
    """Crea una solicitud temporal; devuelve (sesion, token). El token no se guarda.

    Invalida (cancela) la pendiente anterior del mismo servicio y etapa.
    """
    if etapa not in Etapa.values:
        raise ValidationError("Etapa de captura no válida.")
    with transaction.atomic():
        if not Servicio.objects.filter(
            pk=servicio.pk, estado_captura=_ESTADO_REQUERIDO[etapa]
        ).exists():
            raise ValidationError("El servicio no admite captura en esa etapa.")
        SesionCaptura.objects.filter(
            servicio=servicio, etapa=etapa, estado=Sesion.PENDIENTE
        ).update(estado=Sesion.CANCELADA)
        token = secrets.token_urlsafe(32)  # 256 bits
        ahora = timezone.now()
        try:
            with transaction.atomic():
                sesion = SesionCaptura.objects.create(
                    servicio=servicio,
                    etapa=etapa,
                    creado_por=usuario,
                    token_digest=_digest(token),
                    creada_en=ahora,
                    expira_en=ahora + timedelta(minutes=MINUTOS_SESION_CAPTURA),
                )
        except IntegrityError:
            raise ValidationError("Ya se está creando otra solicitud; inténtalo de nuevo.")
        return sesion, token


def obtener_sesion(*, token):
    """Busca la sesión por token y marca EXPIRADA si venció (comprobado en servidor)."""
    try:
        sesion = SesionCaptura.objects.select_related("servicio").get(
            token_digest=_digest(token or "")
        )
    except SesionCaptura.DoesNotExist:
        raise ValidationError("El vínculo de captura no es válido.")
    SesionCaptura.objects.filter(
        pk=sesion.pk, estado=Sesion.PENDIENTE, expira_en__lte=timezone.now()
    ).update(estado=Sesion.EXPIRADA)
    sesion.refresh_from_db()
    return sesion


def cancelar_sesion(*, sesion):
    filas = SesionCaptura.objects.filter(pk=sesion.pk, estado=Sesion.PENDIENTE).update(
        estado=Sesion.CANCELADA
    )
    if filas != 1:
        raise ValidationError("La solicitud ya no está pendiente.")


def consumir_sesion(
    *,
    token,
    autor,
    clave_archivo,
    tipo_contenido,
    tamano_bytes,
    ancho,
    alto,
    backend="local",
    hash_sha256="",
    version_id="",
):
    """Registra la foto y marca la sesión COMPLETADA en una sola transacción.

    El archivo ya debe estar guardado en storage. Si algo falla no se consume
    el token ni avanza el estado.
    """
    sesion = obtener_sesion(token=token)  # fuera de la transacción: persiste EXPIRADA
    if sesion.estado != Sesion.PENDIENTE:
        raise ValidationError(f"La solicitud está {sesion.get_estado_display().lower()}.")
    with transaction.atomic():
        foto = registrar_captura(
            servicio=sesion.servicio,
            etapa=sesion.etapa,
            clave_archivo=clave_archivo,
            tipo_contenido=tipo_contenido,
            tamano_bytes=tamano_bytes,
            ancho=ancho,
            alto=alto,
            autor=autor,
            backend=backend,
            hash_sha256=hash_sha256,
            version_id=version_id,
        )
        filas = SesionCaptura.objects.filter(pk=sesion.pk, estado=Sesion.PENDIENTE).update(
            estado=Sesion.COMPLETADA, completada_en=timezone.now(), fotografia=foto
        )
        if filas != 1:
            raise ValidationError("La solicitud ya no está pendiente.")
        return foto