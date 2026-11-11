"""Configuración Django para un lote de presentación local y desechable."""
import json
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .settings import *
from ops.presentacion.planificar import construir

raiz = Path(os.environ.get('EVA_PRESENTACION_RAIZ', '')).resolve()
lote = os.environ.get('EVA_PRESENTACION_LOTE', '')
if not os.environ.get('EVA_PRESENTACION_RAIZ') or not lote:
    raise ImproperlyConfigured('Indica el directorio y el lote de presentación.')
try:
    marcador = raiz / '.eva-presentacion'
    if marcador.is_symlink() or marcador.read_text(encoding='utf-8').strip() != lote:
        raise ValueError('Marcador distinto al lote.')
    EVA_PRESENTACION_IDS = tuple(s['id'] for s in construir(lote)['servicios'])
except (ValueError, OSError) as exc:
    raise ImproperlyConfigured('El directorio debe tener un marcador local para este lote.') from exc
base_local = raiz / 'presentacion.sqlite3'
archivos_locales = raiz / 'capturas'
if base_local.is_symlink() or archivos_locales.is_symlink():
    raise ImproperlyConfigured('La base y las capturas deben permanecer en el directorio local.')
EVA_PRESENTACION_LOTE = lote
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': base_local}}
EVA_CAPTURE_PRIVATE_ROOT = archivos_locales
EVA_STORAGE_BACKEND = 'local'
EVA_VISUAL_ENDPOINT = ''
EVA_VISUAL_TOKEN = ''
EVA_VISUAL_ORIGEN = 'SIMULADO'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '[::1]']
MIDDLEWARE = ['ops.presentacion.aislamiento.solo_loopback', *MIDDLEWARE]
TEMPLATES[0]['OPTIONS']['context_processors'].append('ops.presentacion.aislamiento.rotulo')

perfil = json.loads((BASE_DIR / 'ops/analisis/criterios_piloto.propuesta.json').read_text(encoding='utf-8'))
EVA_HISTORICO_CRITERIOS = {**perfil['historico'], 'version': 'presentacion-presencia-v1', 'aprobada': True}
EVA_RECOMENDACIONES_CRITERIOS = {**perfil['recomendaciones'], 'version': 'presentacion-reglas-v1', 'aprobada': True}
