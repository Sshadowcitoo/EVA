"""Contexto histórico de captura: instantánea, nunca reconstrucción de registros viejos."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError

CODIGO = re.compile(r'[-a-zA-Z0-9_]{1,64}')
ZONA = ZoneInfo('America/Guayaquil')


def configuracion():
    config = deepcopy(settings.EVA_CONTEXTO_SERVICIO)
    if (not isinstance(config, dict) or not isinstance(config.get('version'), str) or not config['version']
            or not isinstance(config.get('establecimiento'), dict)):
        raise ValidationError('El contexto del establecimiento no está configurado.')
    for grupo in ([config['establecimiento']], config.get('sedes', []), config.get('modalidades', [])):
        if not isinstance(grupo, list) or not grupo:
            raise ValidationError('Faltan opciones de contexto.')
        codigos = []
        for opcion in grupo:
            if (not isinstance(opcion, dict) or not isinstance(opcion.get('codigo'), str)
                    or not CODIGO.fullmatch(opcion['codigo']) or not isinstance(opcion.get('nombre'), str)
                    or not opcion['nombre'].strip()):
                raise ValidationError('Opción de contexto no válida.')
            codigos.append(opcion['codigo'])
        if len(codigos) != len(set(codigos)):
            raise ValidationError('Opciones de contexto duplicadas.')
    minutos = config.get('franja_minutos', 60)
    if type(minutos) is not int or not 1 <= minutos <= 1440 or 1440 % minutos:
        raise ValidationError('La duración de franja debe dividir exactamente los 1440 minutos del día.')
    config['franja_minutos'] = minutos
    return config


def preparar(datos):
    if not isinstance(datos, dict):
        raise ValidationError('Indica sede, modalidad y lote de preparación.')
    config = configuracion()
    salida = dict(schema_version=1, version=config['version'], establecimiento=config['establecimiento'],
                  franja_minutos=config['franja_minutos'],
                  franja=None, fecha_servido=None)
    for campo, plural in [('sede', 'sedes'), ('modalidad', 'modalidades')]:
        seleccion = next((o for o in config[plural] if o['codigo'] == datos.get(campo)), None)
        if seleccion is None:
            raise ValidationError(f'El valor de {campo} no está habilitado.')
        salida[campo] = seleccion
    lote = datos.get('lote_preparacion')
    if not isinstance(lote, str) or not CODIGO.fullmatch(lote.strip()):
        raise ValidationError('El lote debe usar entre 1 y 64 letras sin tildes, números, guiones o guiones bajos.')
    salida['lote_preparacion'] = lote.strip().lower()
    return salida


def _huella(snapshot):
    # Lotes distintos pueden compararse; la identidad del lote mide diversidad,
    # no define un contexto que obligue a usar la misma preparación dos veces.
    identidad = dict(schema_version=snapshot['schema_version'], version=snapshot['version'],
        establecimiento=snapshot['establecimiento']['codigo'], sede=snapshot['sede']['codigo'],
        modalidad=snapshot['modalidad']['codigo'], franja=snapshot['franja'])
    return hashlib.sha256(json.dumps(identidad, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fijar_servido(servicio, foto):
    """Invocar dentro de la transacción que acepta la primera foto de servido."""
    from .models import Servicio
    if foto.servicio_id != servicio.pk or foto.etapa != 'SERVIDO':
        raise ValidationError('El contexto solo se fija con el servido de este servicio.')
    actual = Servicio.objects.get(pk=servicio.pk)
    if not actual.contexto_snapshot or actual.contexto_clave:
        return  # Los anteriores al contexto no se rellenan ni reclasifican.
    snapshot = deepcopy(actual.contexto_snapshot)
    fecha = foto.fecha.astimezone(ZONA)
    minutos = snapshot['franja_minutos']
    inicio = (fecha.hour * 60 + fecha.minute) // minutos * minutos
    fin = inicio + minutos
    snapshot.update(fecha_servido=fecha.isoformat(), franja=dict(codigo=f'm{inicio:04}_{fin:04}',
        desde_minuto=inicio, hasta_minuto=fin,
        nombre=f'{inicio//60:02}:{inicio%60:02}–{(fin-1)//60:02}:{(fin-1)%60:02}'))
    clave = _huella(snapshot)
    Servicio.objects.filter(pk=actual.pk, contexto_clave='').update(contexto_snapshot=snapshot, contexto_clave=clave)


def clave_historica(servicio):
    snapshot = servicio.contexto_snapshot
    try:
        if (not isinstance(snapshot, dict) or type(snapshot.get('schema_version')) is not int or snapshot['schema_version'] != 1
                or not servicio.contexto_clave or not snapshot.get('version')
                or not snapshot.get('lote_preparacion') or snapshot.get('franja') is None):
            return None
        lote = snapshot['lote_preparacion']
        if not isinstance(lote, str) or not CODIGO.fullmatch(lote):
            return None
        for campo in ('establecimiento', 'sede', 'modalidad'):
            if not isinstance(snapshot.get(campo), dict) or not isinstance(snapshot[campo].get('codigo'), str) or not CODIGO.fullmatch(snapshot[campo]['codigo']):
                return None
        fecha = datetime.fromisoformat(snapshot['fecha_servido'])
        if fecha.tzinfo is None:
            return None
        minutos = snapshot['franja_minutos']
        if type(minutos) is not int or not 1 <= minutos <= 1440 or 1440 % minutos:
            return None
        local = fecha.astimezone(ZONA)
        esperado = (local.hour * 60 + local.minute) // minutos * minutos
        if (snapshot['franja']['desde_minuto'] != esperado
                or snapshot['franja']['hasta_minuto'] != esperado + minutos):
            return None
        return servicio.contexto_clave if _huella(snapshot) == servicio.contexto_clave else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
