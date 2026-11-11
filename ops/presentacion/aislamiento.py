from django.conf import settings
from django.http import HttpResponseForbidden


def lote_activo():
    if getattr(settings, 'SETTINGS_MODULE', '') == 'config.settings_presentacion':
        return settings.EVA_PRESENTACION_LOTE
    return None


def solo_loopback(siguiente):
    def atender(request):
        if request.META.get('REMOTE_ADDR') not in ('127.0.0.1', '::1'):
            return HttpResponseForbidden('El entorno de presentación requiere acceso local.')
        return siguiente(request)
    return atender


def rotulo(request):
    return {'entorno_presentacion': lote_activo()}
