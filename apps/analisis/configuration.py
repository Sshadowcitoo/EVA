"""Criterios de aceptación: ausentes o inválidos nunca habilitan conclusiones."""
import math
from django.conf import settings


def criterios_componente(codigo):
    config = settings.EVA_ANALISIS_CRITERIOS
    if not isinstance(config, dict):
        config = {}
    version = config.get("version", "")
    umbrales = config.get("umbrales", {})
    umbral = umbrales.get(codigo) if isinstance(umbrales, dict) else None
    valido = (type(umbral) in (int, float) and math.isfinite(umbral) and 0 <= umbral <= 1)
    aprobada = config.get("aprobada") is True and bool(version)
    return {
        "umbral_confianza": umbral if aprobada and valido else None,
        "comparabilidad_aprobada": aprobada and config.get("comparabilidad_aprobada") is True,
        "version_configuracion": version,
    }
