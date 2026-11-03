"""JSON interno reversible para fechas y Decimal de los contratos."""
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json


def _encode(value):
    if isinstance(value, (datetime, date, time, Decimal)):
        return {'__tipo_eva__': type(value).__name__, 'valor': str(value)}
    raise TypeError(f'Tipo no serializable: {type(value).__name__}')


def _decode(value):
    if set(value) == {'__tipo_eva__', 'valor'}:
        converters = dict(datetime=datetime.fromisoformat, date=date.fromisoformat,
                          time=time.fromisoformat, Decimal=Decimal)
        if value['__tipo_eva__'] in converters:
            return converters[value['__tipo_eva__']](value['valor'])
    return value


def guardar(value):
    return json.loads(json.dumps(value, default=_encode, sort_keys=True, allow_nan=False))


def cargar(value):
    return json.loads(json.dumps(value), object_hook=_decode)


def huella(value):
    return hashlib.sha256(json.dumps(value, default=_encode, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()
