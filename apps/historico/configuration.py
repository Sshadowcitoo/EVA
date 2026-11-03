"""Presencia de sobrante: distinta de la confianza del modelo y sin aprobación implícita."""
from decimal import Decimal, InvalidOperation
from django.conf import settings


def criterio_presencia():
    config = getattr(settings, 'EVA_HISTORICO_CRITERIOS', {})
    if not isinstance(config, dict):
        config = {}
    version = config.get('version')
    valor = config.get('presencia_t')
    try:
        t = Decimal(str(valor)) if type(valor) in (int, float, str, Decimal) else None
    except InvalidOperation:
        t = None
    valido = (t is not None and t.is_finite() and 0 <= t <= 100
              and config.get('aprobada') is True and isinstance(version, str) and bool(version.strip()))
    return dict(t=t if valido else None, version_criterio=version.strip() if valido else None)
