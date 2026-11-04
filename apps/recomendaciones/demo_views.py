"""Sección separada: cifras preparadas, nunca resultados del modelo o del histórico."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from apps.catalogo.permissions import roles_required, COCINA, ADMINISTRACION
from apps.captura.models import FotografiaServicio
from apps.captura import storage
from apps.analisis.evidencia import foto_bytes
from .demo import preparar


@never_cache
@roles_required(COCINA, ADMINISTRACION)
@require_GET
def demostracion(request):
    try:
        datos = preparar(request.GET.get('escenario', 'porcion'))
    except ValueError:
        raise Http404 from None
    datos['foto_disponible'] = bool(getattr(settings, 'EVA_DEMO_SERVICIO_ID', ''))
    return render(request, 'recomendaciones/demo.html', datos)


@never_cache
@roles_required(COCINA, ADMINISTRACION)
@require_GET
def foto(request):
    servicio = getattr(settings, 'EVA_DEMO_SERVICIO_ID', '')
    if not servicio:
        raise Http404
    registro = get_object_or_404(FotografiaServicio, servicio_id=servicio, etapa='SERVIDO', vigente=True)
    try:
        contenido = foto_bytes(registro)
    except (ValidationError, storage.ErrorAlmacenamiento):
        raise Http404 from None
    respuesta = HttpResponse(contenido, content_type=registro.tipo_contenido)
    respuesta['Content-Disposition'] = 'inline; filename="referencia-demo.png"'
    return respuesta
