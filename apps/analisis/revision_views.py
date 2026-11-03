from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from apps.catalogo.permissions import COCINA, roles_required
from . import services, views
from .forms import RevisionForm
from .models import IntentoAnalisis
from .presentacion import contexto
from .revision import evidencia_disponible


def _contexto(analisis, intento):
    datos = contexto(analisis, intento)
    vigente = services.revision_vigente(intento)
    disponible = views.actual(analisis) and evidencia_disponible(analisis, intento)
    datos.update(revision_actual=vigente, version_esperada=vigente.version if vigente else 0,
                 puede_confirmar=disponible and not services.motivos_no_confirmable(intento, disponible),
                 revisiones=intento.revisiones.select_related('autor').order_by('-version'))
    if intento.estado == 'COMPLETADO' and views.actual(analisis) and analisis.intento_vigente_id == intento.pk:
        # URL contiene el intento exacto visto. Nunca decidir sobre un intento nuevo por accidente.
        datos['decision_url'] = reverse('analisis:revisar', args=[analisis.pk, intento.pk])
    return datos


@never_cache
@roles_required(COCINA)
@require_GET
def pendientes_revision(request):
    views._permiso(request, 'view_revisionanalisis')
    return views.lista(request, solo_revision=True)


@never_cache
@roles_required(COCINA)
@require_GET
def revision_detalle(request, analisis_id):
    views._permiso(request, 'view_revisionanalisis')
    analisis = views._analisis(analisis_id)
    intento = views.ultimo_intento(analisis)
    if intento is None:
        return HttpResponse('El análisis aún no tiene intento.', status=409)
    return render(request, 'analisis/revision_operativa.html', _contexto(analisis, intento))


@never_cache
@roles_required(COCINA)
@require_POST
def revisar(request, analisis_id, intento_id):
    views._permiso(request, 'add_revisionanalisis')
    analisis = views._analisis(analisis_id)
    intento = get_object_or_404(IntentoAnalisis, pk=intento_id, analisis=analisis)
    if (not views.actual(analisis) or analisis.intento_vigente_id != intento.pk
            or views.ultimo_intento(analisis).pk != intento.pk):
        return HttpResponse('Este resultado ya no es el vigente. Vuelve a abrir el caso.', status=409)
    # El dominio exige motivo al rectificar y reconoce un POST idéntico repetido.
    # No rechazar antes de tiempo ese reenvío idempotente como si fuera rectificación.
    form = RevisionForm(request.POST)
    if not form.is_valid():
        datos = _contexto(analisis, intento)
        datos.update(error='Revisa la decisión, versión y motivo antes de guardar.', form_errores=form.errors,
                     motivo_borrador=request.POST.get('motivo', '')[:1000])
        return render(request, 'analisis/revision_operativa.html', datos, status=400)
    try:
        # Ni el navegador ni el HTML deshabilitado certifican disponibilidad.
        disponible = evidencia_disponible(analisis, intento)
        services.revisar_resultado(intento, form.cleaned_data['decision'], form.cleaned_data['motivo'],
            request.user, form.cleaned_data['version_esperada'], evidencia_disponible=disponible)
    except ValidationError as exc:
        datos = _contexto(analisis, intento)
        datos.update(error=' '.join(exc.messages), motivo_borrador=form.cleaned_data['motivo'])
        return render(request, 'analisis/revision_operativa.html', datos,
                      status=409 if isinstance(exc, services.ConflictoRevision) else 400)
    except OperationalError as exc:
        # SQLite puede rechazar la promoción de dos transacciones simultáneas.
        # No reintentar una escritura que quizá el usuario ya haya actualizado.
        if any(palabra in str(exc).lower() for palabra in ('locked', 'busy')):
            return HttpResponse('Otra revisión está en curso. Recarga el caso antes de volver a decidir.', status=409)
        return HttpResponse('No se pudo guardar la revisión. Comprueba el caso antes de reintentar.', status=503)
    return redirect('analisis:revision_detalle', analisis.pk)
