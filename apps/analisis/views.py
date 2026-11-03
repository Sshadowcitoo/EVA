from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.captura import storage
from apps.captura.models import Servicio
from apps.catalogo.permissions import COCINA, roles_required
from . import evidencia, motor, services
from .configuration import criterios_componente
from .models import AnalisisServicio, ArtefactoAnalisis
from .presentacion import contexto


def _permiso(request, nombre):
    if not request.user.has_perm('analisis.' + nombre):
        raise PermissionDenied


def _analisis(pk):
    return get_object_or_404(AnalisisServicio.objects.select_related(
        'servicio', 'foto_servido', 'foto_retorno'), pk=pk)


def actual(analisis):
    ultimo = AnalisisServicio.objects.filter(servicio=analisis.servicio).order_by('-creado_en', '-pk').first()
    return (ultimo.pk == analisis.pk and analisis.servicio.estado_captura == 'PAR_COMPLETO'
            and analisis.foto_servido.vigente and analisis.foto_retorno.vigente)


def ultimo_intento(analisis):
    return analisis.intentos.order_by('-numero').first()


@never_cache
@roles_required(COCINA)
@require_GET
def lista(request):
    _permiso(request, 'view_analisisservicio')
    servicios = Servicio.objects.filter(estado_captura='PAR_COMPLETO').order_by('-fecha_creacion', '-pk')
    page = Paginator(servicios, 30).get_page(request.GET.get('page'))
    casos = []
    for servicio in page:
        analisis = servicio.analisis.order_by('-creado_en', '-pk').first()
        if analisis:
            datos = contexto(analisis, ultimo_intento(analisis))['caso']
            datos['detalle_url'] = reverse('analisis:detalle', args=[analisis.pk])
        else:
            datos = dict(plato_nombre=servicio.get_plato_display(), porcion_nombre=servicio.get_tipo_porcion_display(),
                         servicio_id=str(servicio.pk), estado='', detalle_url=reverse('analisis:par', args=[servicio.pk]))
        casos.append(datos)
    ultimos = AnalisisServicio.objects.filter(servicio_id=OuterRef('servicio_id')).order_by('-creado_en', '-pk').values('pk')[:1]
    alcance = AnalisisServicio.objects.filter(pk=Subquery(ultimos), origen='REAL', servicio__estado_captura='PAR_COMPLETO')
    nulos = alcance.filter(intento_vigente__resultados__estado='NO_CONCLUYENTE').values('servicio_id').distinct().count()
    resumen = dict(no_concluyentes=nulos, por_revisar=None)
    return render(request, 'analisis/lista_operativa.html', dict(casos=casos, resumen=resumen, pagina=page))


@never_cache
@roles_required(COCINA)
@require_GET
def par(request, servicio_id):
    _permiso(request, 'view_analisisservicio')
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    error = None
    try:
        motor.configuracion()
    except ValidationError as exc:
        error = ' '.join(exc.messages)
    return render(request, 'analisis/par.html', dict(servicio=servicio, error=error))


@never_cache
@roles_required(COCINA)
@require_POST
def solicitar(request, servicio_id):
    _permiso(request, 'add_analisisservicio')
    servicio = get_object_or_404(Servicio, pk=servicio_id)
    try:
        motor.configuracion()
        fotos = list(servicio.fotografias.filter(vigente=True))
        if len(fotos) != 2 or any(not evidencia.protocolo_completo(f) for f in fotos):
            raise ValidationError('Ambas fotografías requieren el checklist del protocolo de captura.')
        # Comprobar existencia, huella y dimensiones antes de encolar; el worker repite la lectura.
        for foto in fotos:
            evidencia.foto_bytes(foto)
        version = criterios_componente('')['version_configuracion']
        analisis, _, _ = services.solicitar_analisis(servicio=servicio, solicitante=request.user,
                version_modelo=settings.EVA_VISUAL_VERSION_MODELO, version_configuracion=version,
                origen=settings.EVA_VISUAL_ORIGEN)
    except (ValidationError, storage.ErrorAlmacenamiento):
        return render(request, 'analisis/par.html', dict(servicio=servicio,
                      error='No se puede solicitar: revisa motor, par, protocolo y disponibilidad de las fotos.'), status=400)
    return redirect('analisis:detalle', analisis.pk)


@never_cache
@roles_required(COCINA)
@require_GET
def detalle(request, analisis_id):
    _permiso(request, 'view_analisisservicio')
    analisis = _analisis(analisis_id)
    datos = contexto(analisis, ultimo_intento(analisis))
    if not actual(analisis):
        datos.pop('reintentar_url', None)
    return render(request, 'analisis/detalle.html', datos)


@never_cache
@roles_required(COCINA)
@require_GET
def estado(request, analisis_id):
    _permiso(request, 'view_analisisservicio')
    intento = ultimo_intento(_analisis(analisis_id))
    if intento is None:
        raise Http404
    return JsonResponse(dict(estado=intento.estado))


@never_cache
@roles_required(COCINA)
@require_POST
def reintentar(request, analisis_id):
    _permiso(request, 'add_intentoanalisis')
    analisis = _analisis(analisis_id)
    try:
        motor.configuracion()
        if not actual(analisis):
            raise ValidationError('Este análisis ya no es el actual.')
        for f in (analisis.foto_servido, analisis.foto_retorno):
            if not evidencia.protocolo_completo(f):
                raise ValidationError('Falta protocolo.')
            evidencia.foto_bytes(f)
        services.reintentar_analisis(analisis=analisis)
    except (ValidationError, storage.ErrorAlmacenamiento):
        return HttpResponse('No se puede reintentar este análisis. Revisa el par y el estado.', status=409)
    return redirect('analisis:detalle', analisis.pk)


@never_cache
@roles_required(COCINA)
@require_GET
def foto(request, analisis_id, foto_id):
    _permiso(request, 'view_analisisservicio')
    analisis = _analisis(analisis_id)
    fotografia = next((f for f in (analisis.foto_servido, analisis.foto_retorno) if f.pk == foto_id), None)
    if fotografia is None:
        raise Http404
    try:
        datos = evidencia.foto_bytes(fotografia)
    except ValidationError:
        return HttpResponse('Evidencia no disponible.', status=410)
    except storage.ArchivoNoEncontrado:
        return HttpResponse('Evidencia no disponible.', status=410)
    except storage.ErrorAlmacenamiento:
        return HttpResponse('Almacenamiento temporalmente no disponible.', status=503)
    respuesta = HttpResponse(datos, content_type=fotografia.tipo_contenido)
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta


@never_cache
@roles_required(COCINA)
@require_GET
def mascara(request, analisis_id, mascara_id):
    _permiso(request, 'view_artefactoanalisis')
    art = get_object_or_404(ArtefactoAnalisis.objects.select_related('foto_padre', 'resultado__servicio_componente'),
                            pk=mascara_id, resultado__intento__analisis_id=analisis_id)
    if art.eliminado_en is not None or not art.foto_padre.disponible:
        return HttpResponse('Evidencia vencida.', status=410)
    try:
        datos = evidencia.leer(art, evidencia.MAX_MASCARA)
        datos = evidencia.superposicion(datos, art.foto_padre, art.resultado.servicio_componente.componente_codigo)
    except (ValidationError, storage.ArchivoNoEncontrado):
        return HttpResponse('Máscara no disponible.', status=410)
    except storage.ErrorAlmacenamiento:
        return HttpResponse('Almacenamiento temporalmente no disponible.', status=503)
    respuesta = HttpResponse(datos, content_type='image/png')
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta
