"""Acciones operativas de Administración; no borra servicios ni fotografías."""
from io import BytesIO

import qrcode
import qrcode.image.svg
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from apps.catalogo.permissions import ADMINISTRACION, roles_required
from . import services
from .forms import BuscarGestionForm, MotivoOperacionForm, ReemplazarEtiquetaForm
from .models import AsignacionBandeja, Bandeja, EtiquetaBandeja, Servicio


def _contexto(request, **extra):
    return {
        'permite_anular': request.user.has_perm('captura.anular_servicio'),
        'permite_reemplazar': request.user.has_perm('captura.reemplazar_etiquetabandeja'),
        **extra,
    }


@never_cache
@roles_required(ADMINISTRACION)
@require_GET
def gestion(request):
    busqueda = request.GET.copy()
    pagina = busqueda.pop('pagina', [None])[-1]
    form = BuscarGestionForm(busqueda or None)
    bandeja = servicio = asignacion = bandejas = None
    if not form.is_bound:
        abiertas = AsignacionBandeja.objects.filter(bandeja_id=OuterRef('pk'), fin__isnull=True)
        listado = Bandeja.objects.annotate(ocupada=Exists(abiertas))
        bandejas = Paginator(listado, 25).get_page(pagina)
    elif form.is_valid():
        if form.cleaned_data['numero']:
            bandeja = get_object_or_404(Bandeja, numero=form.cleaned_data['numero'])
            asignacion = AsignacionBandeja.objects.select_related('servicio').filter(bandeja=bandeja, fin__isnull=True).first()
            servicio = asignacion.servicio if asignacion else None
        else:
            servicio = get_object_or_404(Servicio, pk=form.cleaned_data['servicio'])
            asignacion = servicio.asignaciones.select_related('bandeja').first()
            bandeja = asignacion.bandeja if asignacion else None
    etiqueta = bandeja.etiquetas.filter(revocada_en__isnull=True).first() if bandeja else None
    historial = bandeja.etiquetas.filter(revocada_en__isnull=False).select_related('revocada_por')[:5] if bandeja else []
    return render(request, 'captura/gestion.html', _contexto(request, form=form, bandeja=bandeja,
                  servicio=servicio, etiqueta=etiqueta, historial=historial,
                  asignacion=asignacion, bandejas=bandejas))


@never_cache
@roles_required(ADMINISTRACION)
@permission_required('captura.anular_servicio', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def anular(request, pk):
    servicio = get_object_or_404(Servicio, pk=pk)
    permitida = servicio.estado_captura in (Servicio.EstadoCaptura.PENDIENTE_SERVIDO, Servicio.EstadoCaptura.EN_ESPERA_RETORNO)
    form = MotivoOperacionForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and permitida and form.is_valid():
        try:
            services.anular_servicio(servicio=servicio, motivo=form.cleaned_data['motivo'], usuario=request.user)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Servicio anulado. La bandeja quedó libre y el historial se conserva.')
            return redirect(reverse('captura:gestion') + '?' + urlencode({'servicio': str(servicio.pk)}))
    return render(request, 'captura/anular_servicio.html', _contexto(request, form=form, servicio=servicio, permitida=permitida))


@never_cache
@roles_required(ADMINISTRACION)
@permission_required('captura.reemplazar_etiquetabandeja', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def reemplazar(request, pk):
    bandeja = get_object_or_404(Bandeja, pk=pk)
    etiqueta = bandeja.etiquetas.filter(revocada_en__isnull=True).first()
    if etiqueta is None:
        raise Http404('La bandeja no tiene una etiqueta vigente para reemplazar.')
    form = ReemplazarEtiquetaForm(request.POST if request.method == 'POST' else None,
                                 initial={'etiqueta_actual': etiqueta.codigo})
    if request.method == 'POST' and form.is_valid():
        try:
            services.reemplazar_etiqueta(bandeja=bandeja, motivo=form.cleaned_data['motivo'],
                                        usuario=request.user, codigo_esperado=form.cleaned_data['etiqueta_actual'])
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, 'Etiqueta reemplazada. Imprime el nuevo QR y retira la etiqueta anterior.')
            return redirect(reverse('captura:gestion') + '?' + urlencode({'numero': bandeja.numero}))
    return render(request, 'captura/reemplazar_etiqueta.html', _contexto(request, form=form, bandeja=bandeja, etiqueta=etiqueta))


@never_cache
@roles_required(ADMINISTRACION)
@permission_required('captura.reemplazar_etiquetabandeja', raise_exception=True)
@require_GET
def qr_etiqueta(request, pk):
    etiqueta = get_object_or_404(EtiquetaBandeja, pk=pk, revocada_en__isnull=True)
    image = qrcode.make(etiqueta.codigo, image_factory=qrcode.image.svg.SvgPathFillImage, border=4)
    output = BytesIO()
    image.save(output)
    response = HttpResponse(output.getvalue(), content_type='image/svg+xml')
    response['Content-Disposition'] = f'inline; filename="bandeja-{etiqueta.bandeja.numero}.svg"'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response
