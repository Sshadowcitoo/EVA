"""Configuración Django para un lote de presentación local y desechable."""
import json
import os
import re
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
EVA_PRESENTACION_FILTROS_INICIALES = dict(desde='2026-10-05', hasta='2026-11-01',
    plato='seco_de_pollo', componente='pollo', porcion='estandar')
EVA_PRESENTACION_COMPARACION_INICIAL = dict(plato='arroz_menestra_carne', componente='menestra',
    porcion='estandar', referencia_desde='2026-10-05', referencia_hasta='2026-10-18',
    comparado_desde='2026-10-19', comparado_hasta='2026-11-01')

# Publicación explícita en un proceso y una base distintos de la operación.
if os.environ.get('EVA_PRESENTACION_PUBLICA') == '1':
    host = os.environ.get('EVA_PRESENTACION_HOST', '')
    clave = os.environ.get('EVA_PRESENTACION_SECRET_KEY', '')
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', host) or len(clave) < 50:
        raise ImproperlyConfigured('La presentación pública necesita host y clave propios.')
    DEBUG = False
    SECRET_KEY = clave
    ALLOWED_HOSTS = [host]
    FORCE_SCRIPT_NAME = '/presentacion'
    STATIC_URL = '/static/'
    SESSION_COOKIE_NAME = 'eva_presentacion_session'
    CSRF_COOKIE_NAME = 'eva_presentacion_csrf'
    SESSION_COOKIE_PATH = CSRF_COOKIE_PATH = '/presentacion/'
    SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_TRUSTED_ORIGINS = ['https://' + host]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    EVA_VISUAL_ENDPOINT = os.environ.get('EVA_PRESENTACION_MOTOR_ENDPOINT', '')
    EVA_VISUAL_TOKEN = os.environ.get('EVA_PRESENTACION_MOTOR_TOKEN', '')

# La aceptación de comparabilidad sigue pendiente incluso en los casos con fotos.
EVA_ANALISIS_CRITERIOS = dict(version='presentacion-inferencia-v1', aprobada=True,
    comparabilidad_aprobada=False,
    umbrales={c: .80 for c in ('arroz', 'pollo', 'yuca', 'pescado', 'menestra', 'carne', 'ensalada')})
