"""Operaciones de dominio de bandejas y capturas.

Todas son atómicas y lanzan ValidationError con un mensaje legible cuando la
operación no es válida; en ese caso no queda ninguna fila parcial. Las
transiciones de estado usan actualizaciones condicionales y restricciones
únicas (no select_for_update), para que funcionen igual con SQLite.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.captura.models import (
    AsignacionBandeja,
    Bandeja,
    EtiquetaBandeja,
    FotografiaServicio,
    Servicio,
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