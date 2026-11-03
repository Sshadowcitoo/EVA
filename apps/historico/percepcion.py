"""Operaciones de percepción, independientes de los resultados visuales."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, OperationalError, transaction

from apps.captura.models import Servicio
from apps.catalogo.permissions import REGISTRO, tiene_rol
from .contracts import CATEGORIAS_PERCEPCION, MAX_MOTIVO, ConflictoPercepcion, ServicioNoDisponible
from .models import PercepcionServicio


def _autorizar(usuario):
    if not usuario or not tiene_rol(usuario, REGISTRO):
        raise PermissionDenied('Se requiere el rol Registro.')


def _servicio(servicio_id, bloquear=False):
    consulta = Servicio.objects.select_for_update() if bloquear else Servicio.objects
    try:
        return consulta.exclude(estado_captura='ANULADO').get(pk=servicio_id)
    except (Servicio.DoesNotExist, ValidationError, ValueError, TypeError):
        raise ServicioNoDisponible('Servicio no disponible.') from None


def _dto(servicio, registro=None):
    return dict(servicio_id=str(servicio.pk), categoria=registro.categoria if registro else 'NO_INFORMADO',
                motivo=registro.motivo if registro else '', version=registro.version if registro else 0,
                registrada_en=registro.fecha if registro else None,
                operador_visible=registro.autor.get_username() if registro else None)


def obtener_percepcion(servicio_id, usuario):
    _autorizar(usuario)
    servicio = _servicio(servicio_id)
    registro = servicio.percepciones.filter(vigente=True).select_related('autor').first()
    return _dto(servicio, registro)


def registrar_percepcion(servicio_id, categoria, motivo, usuario, version_esperada):
    _autorizar(usuario)
    errores = {}
    if categoria not in [c for c, _ in CATEGORIAS_PERCEPCION]:
        errores['categoria'] = 'Selecciona una categoría válida.'
    if not isinstance(motivo, str) or len(motivo) > MAX_MOTIVO:
        errores['motivo'] = 'El motivo debe tener como máximo 1000 caracteres.'
    else:
        motivo = motivo.strip()
        if categoria == 'NO_INFORMADO' and motivo:
            errores['motivo'] = 'Sin respuesta no se registra un motivo declarado.'
    if type(version_esperada) is not int or not 0 <= version_esperada < 2**31:
        errores['version_esperada'] = 'La versión debe ser un entero no negativo válido.'
    if errores:
        raise ValidationError(errores)
    try:
        with transaction.atomic():
            servicio = _servicio(servicio_id, bloquear=True)
            actual = servicio.percepciones.filter(vigente=True).select_related('autor').first()
            version = actual.version if actual else 0
            if actual and (actual.categoria, actual.motivo, actual.autor_id) == (categoria, motivo, usuario.pk):
                if version_esperada in (version - 1, version):
                    return _dto(servicio, actual)
            if version_esperada != version:
                raise ConflictoPercepcion('La percepción cambió; recarga el servicio antes de corregirla.')
            if actual is None and categoria == 'NO_INFORMADO':
                return _dto(servicio)
            if version >= 2**31 - 1:
                raise ValidationError({'version_esperada': 'No se pueden crear más versiones para este registro.'})
            if actual:
                cambiado = PercepcionServicio.objects.filter(pk=actual.pk, version=version, vigente=True).update(vigente=False)
                if cambiado != 1:
                    raise ConflictoPercepcion('Otra persona modificó la percepción.')
            nuevo = PercepcionServicio.objects.create(servicio=servicio, categoria=categoria, motivo=motivo,
                        autor=usuario, version=version + 1, sustituye=actual)
            return _dto(servicio, nuevo)
    except IntegrityError:
        raise ConflictoPercepcion('Otra persona registró una respuesta al mismo tiempo.') from None
    except OperationalError as exc:
        if any(p in str(exc).lower() for p in ('locked', 'busy')):
            raise ConflictoPercepcion('Otra operación está en curso; recarga antes de reintentar.') from None
        raise
