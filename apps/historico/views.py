"""Adaptación HTTP del histórico. Los servicios conservan las reglas de negocio."""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from apps.catalogo.permissions import ADMINISTRACION, COCINA, REGISTRO, roles_required
from . import services
from .contracts import BackendHistoricoNoDisponible, ConflictoPercepcion, FiltrosInvalidos, ServicioNoDisponible
from .forms import ComparacionForm, FiltrosForm, PercepcionForm, agregar_errores


def _validacion(form, exc):
    agregar_errores(form, exc.errores if isinstance(exc, FiltrosInvalidos) else (exc.message_dict if hasattr(exc, 'message_dict') else {'__all__': exc.messages}))


def _enlaces_pagina(request, datos):
    paginacion = datos['paginacion']
    enlaces = {}
    for nombre, pagina in [('anterior', paginacion['pagina']-1), ('siguiente', paginacion['pagina']+1)]:
        if 1 <= pagina <= paginacion['paginas']:
            query = request.GET.copy()
            query['page'] = pagina
            enlaces[nombre] = '?' + query.urlencode()
    return enlaces


@roles_required(COCINA, ADMINISTRACION)
@require_GET
def lista(request):
    opciones = None
    error = None
    try:
        opciones = services.opciones_historico()
    except BackendHistoricoNoDisponible:
        error = 'El histórico está pendiente de conexión. No hay resultados disponibles para esta consulta.'
    form = FiltrosForm(request.GET, opciones=opciones)
    datos, panel, enlaces, status = None, None, {}, 503 if error else 200
    if not error:
        if form.is_valid():
            try:
                datos, panel = services.consultar_panel(form.filtros, pagina=form.cleaned_data.get('page') or 1,
                                                       grupo=request.GET.get('grupo', ''))
                enlaces = _enlaces_pagina(request, datos)
            except BackendHistoricoNoDisponible:
                error, status = 'El histórico está pendiente de conexión. Intenta nuevamente más tarde.', 503
            except (FiltrosInvalidos, ValidationError) as exc:
                _validacion(form, exc)
                status = 400
        else:
            status = 400
    return render(request, 'historico/lista.html', dict(form=form, datos=datos, panel=panel, enlaces=enlaces, error=error,
        filtros_panel=[(k, v) for k, v in request.GET.items() if k in form.fields and k != 'page']), status=status)


@roles_required(COCINA, ADMINISTRACION)
@require_GET
def comparar(request):
    error, opciones, datos = None, None, None
    try:
        opciones = services.opciones_historico()
    except BackendHistoricoNoDisponible:
        error = 'La comparación está pendiente de conexión. No se han calculado diferencias.'
    form = ComparacionForm(request.GET if request.GET else None, opciones=opciones)
    status = 503 if error else 200
    if not error and form.is_bound:
        if form.is_valid():
            try:
                datos = services.comparar_periodos(form.referencia, form.comparado)
            except BackendHistoricoNoDisponible:
                error, status = 'La comparación está pendiente de conexión. No se han calculado diferencias.', 503
            except (FiltrosInvalidos, ValidationError) as exc:
                _validacion(form, exc)
                status = 400
        else:
            status = 400
    return render(request, 'historico/comparar.html', dict(form=form, comparacion=datos, error=error), status=status)


@roles_required(REGISTRO)
@require_http_methods(['GET', 'POST'])
def percepcion(request, servicio_id):
    actual, error, conflicto = None, None, False
    try:
        actual = services.obtener_percepcion(servicio_id, request.user)
    except ServicioNoDisponible:
        raise Http404
    except BackendHistoricoNoDisponible:
        error = 'La percepción está pendiente de conexión. No se ha guardado ninguna respuesta; puedes continuar con la captura.'
    form = PercepcionForm(request.POST if request.method == 'POST' else None, initial={
        'categoria': actual['categoria'] if actual else 'NO_INFORMADO',
        'motivo': actual['motivo'] if actual else '',
        'version_esperada': actual['version'] if actual else 0,
    })
    status = 503 if error else 200
    if request.method == 'POST' and not error:
        if form.is_valid():
            try:
                services.registrar_percepcion(servicio_id, form.cleaned_data['categoria'], form.cleaned_data['motivo'], request.user, form.cleaned_data['version_esperada'])
                messages.success(request, 'Respuesta guardada correctamente.')
                return redirect(reverse('historico:percepcion', args=[servicio_id]))
            except ConflictoPercepcion:
                conflicto, status = True, 409
                error = 'La respuesta cambió mientras la editabas. Revisa la respuesta vigente y recarga antes de decidir de nuevo. Tu propuesta se conserva abajo y no se ha guardado.'
                try:
                    actual = services.obtener_percepcion(servicio_id, request.user)
                except ServicioNoDisponible:
                    raise Http404
                except BackendHistoricoNoDisponible:
                    actual = None
            except ServicioNoDisponible:
                raise Http404
            except BackendHistoricoNoDisponible:
                error, status = 'El guardado no está disponible. No se ha confirmado la respuesta; no se reintentará automáticamente.', 503
            except (FiltrosInvalidos, ValidationError) as exc:
                _validacion(form, exc)
                status = 400
        else:
            status = 400
    return render(request, 'historico/percepcion.html', dict(form=form, actual=actual, servicio_id=servicio_id, error=error, conflicto=conflicto, bloqueado=bool(error)), status=status)


@roles_required(COCINA, ADMINISTRACION)
@require_GET
def demostracion(request):
    """Vista de solo lectura; no consulta ni modifica los servicios operativos."""
    from .demo import ESCENARIOS, construir
    escenario = request.GET.get("escenario", "con_datos")
    try:
        if escenario not in ESCENARIOS:
            raise ValidationError("Escenario de demostración desconocido.")
        pagina = forms.IntegerField(min_value=1).clean(request.GET.get("page", "1"))
    except ValidationError as exc:
        return render(request, "historico/demostracion.html", dict(error=" ".join(exc.messages),
            es_demostracion=True, escenario=escenario), status=400)
    datos, panel = construir(escenario, request.GET.get("grupo", ""), pagina)
    return render(request, "historico/demostracion.html", dict(datos=datos, panel=panel,
        es_demostracion=True, escenario=escenario, filtros_panel=[("escenario", escenario)],
        enlaces=_enlaces_pagina(request, datos), recomendaciones_url=reverse("recomendaciones:demo")))
