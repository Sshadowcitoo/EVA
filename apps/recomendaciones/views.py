"""Adaptación HTTP del contrato v1, sin reglas de suficiencia ni persistencia."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from apps.catalogo.permissions import roles_required, tiene_rol, ADMINISTRACION
from . import services
from .presenters import parametros_texto, textos_caso, filas_visibles
from .contracts import BackendRecomendacionesNoDisponible, CasoNoDisponible, ConflictoRecomendacion, ParametrosInvalidos
from .forms import FiltrosForm, EvaluacionForm, DecisionForm, PruebaForm, VersionForm, errores_formulario


def _error(exc, form=None):
    if isinstance(exc, CasoNoDisponible):
        raise Http404 from None
    if isinstance(exc, BackendRecomendacionesNoDisponible):
        return 503, 'El módulo está pendiente de conexión. No hay confirmación de guardado ni resultados disponibles para esta operación.'
    if isinstance(exc, ConflictoRecomendacion):
        motivo = str(exc).strip() or 'La evidencia o la versión cambió.'
        return 409, motivo+' Tu borrador se conserva sin guardar. Recarga los datos y vuelve a decidir; no se reintentará la operación automáticamente.'
    errores = exc.errores if isinstance(exc, ParametrosInvalidos) else (exc.message_dict if hasattr(exc, 'message_dict') else {'__all__':exc.messages})
    if form is not None:
        errores_formulario(form, errores)
        return 400, 'Revisa los campos indicados; no se ha confirmado la operación.'
    mensajes = [str(mensaje) for valores in errores.values() for mensaje in (valores if isinstance(valores, (list, tuple)) else [valores])]
    return 400, 'No se confirmó la operación. '+' '.join(mensajes)


ERRORES = (BackendRecomendacionesNoDisponible, CasoNoDisponible, ConflictoRecomendacion, ParametrosInvalidos, ValidationError)


def _contexto(request, caso=None, **extra):
    return dict(caso=caso, parametros=parametros_texto(caso), administracion=tiene_rol(request.user, ADMINISTRACION), filas_presentadas=filas_visibles(extra.get('datos')), **textos_caso(caso), **extra)


def _render_detalle(request, caso=None, status=200, error=None, decision_form=None, prueba_form=None, bloqueado=False):
    opciones = None
    if caso and caso['capacidades']['puede_registrar_prueba'] and tiene_rol(request.user, ADMINISTRACION):
        try:
            opciones = services.opciones_recomendaciones(request.user)
        except ERRORES as exc:
            if status == 200:
                status, error = _error(exc)
            bloqueado = True
    decision_form = decision_form if decision_form is not None else DecisionForm(initial={'version_esperada':caso['version_esperada'] if caso else 0})
    prueba_form = prueba_form if prueba_form is not None else PruebaForm(opciones=opciones)
    return render(request, 'recomendaciones/detalle.html', _contexto(request, caso, error=error, bloqueado=bloqueado, decision_form=decision_form, prueba_form=prueba_form), status=status)


@never_cache
@roles_required(ADMINISTRACION)
@require_GET
def lista(request):
    opciones, datos, error, status = None, None, None, 200
    try:
        opciones = services.opciones_recomendaciones(request.user)
    except ERRORES as exc:
        status, error = _error(exc)
    form = FiltrosForm(request.GET, opciones=opciones)
    if status == 200:
        if form.is_valid():
            try:
                datos = services.consultar_recomendaciones(form.normalizado, request.user, pagina=form.cleaned_data.get('page') or 1)
            except ERRORES as exc:
                status, error = _error(exc, form)
        else:
            status = 400
    enlaces = {}
    if datos:
        for nombre, numero in [('anterior', datos['paginacion']['pagina']-1), ('siguiente', datos['paginacion']['pagina']+1)]:
            if 1 <= numero <= datos['paginacion']['paginas']:
                query = request.GET.copy(); query['page'] = numero
                enlaces[nombre] = '?'+query.urlencode()
    return render(request, 'recomendaciones/lista.html', _contexto(request, datos=datos, form=form, evaluacion_form=EvaluacionForm(opciones=opciones), error=error, enlaces=enlaces, bloqueado=status==503), status=status)


@never_cache
@roles_required(ADMINISTRACION)
@require_POST
def evaluar(request):
    opciones, status, error, caso = None, 200, None, None
    try:
        opciones = services.opciones_recomendaciones(request.user)
    except ERRORES as exc:
        status, error = _error(exc)
    form = EvaluacionForm(request.POST, opciones=opciones)
    if status == 200:
        if form.is_valid():
            try:
                caso = services.evaluar_evidencia(form.normalizado, form.cleaned_data['version_criterios'] or None, request.user)
                return redirect('recomendaciones:evaluacion', evaluacion_id=caso['evaluacion']['id'])
            except ERRORES as exc:
                status, error = _error(exc, form)
        else:
            status = 400
    return render(request, 'recomendaciones/lista.html', _contexto(request, datos=None, form=FiltrosForm(opciones=opciones), evaluacion_form=form, error=error, bloqueado=status in (409,503)), status=status)


@never_cache
@roles_required(ADMINISTRACION)
@require_GET
def evaluacion(request, evaluacion_id):
    try:
        caso = services.obtener_evaluacion(evaluacion_id, request.user)
    except ERRORES as exc:
        status, error = _error(exc)
        return _render_detalle(request, status=status, error=error, bloqueado=True)
    return _render_detalle(request, caso)


@never_cache
@roles_required(ADMINISTRACION)
@require_GET
def detalle(request, recomendacion_id):
    try:
        caso = services.obtener_recomendacion(recomendacion_id, request.user)
    except ERRORES as exc:
        status, error = _error(exc)
        return _render_detalle(request, status=status, error=error, bloqueado=True)
    return _render_detalle(request, caso)


@never_cache
@roles_required(ADMINISTRACION)
@require_POST
def generar(request, evaluacion_id):
    caso = None
    try:
        caso = services.generar_recomendacion(evaluacion_id, request.user)
        if caso['recomendacion']:
            return redirect('recomendaciones:detalle', recomendacion_id=caso['recomendacion']['id'])
        return redirect('recomendaciones:evaluacion', evaluacion_id=caso['evaluacion']['id'])
    except ERRORES as exc:
        status, error = _error(exc)
    try:
        caso = services.obtener_evaluacion(evaluacion_id, request.user)
    except ERRORES as exc:
        if isinstance(exc, CasoNoDisponible):
            raise Http404 from None
    return _render_detalle(request, caso, status=status, error=error, bloqueado=True)


@never_cache
@roles_required(ADMINISTRACION)
@require_POST
def decidir(request, recomendacion_id):
    form = DecisionForm(request.POST)
    caso, status, error = None, 400, None
    if form.is_valid():
        datos = form.normalizado
        try:
            caso = services.decidir_recomendacion(recomendacion_id, datos['decision'], datos['justificacion'], request.user, datos['version_esperada'])
            messages.success(request, 'Decisión guardada. El catálogo y las porciones no se modifican automáticamente.')
            return redirect('recomendaciones:detalle', recomendacion_id=caso['recomendacion']['id'])
        except ERRORES as exc:
            status, error = _error(exc, form)
    try:
        caso = services.obtener_recomendacion(recomendacion_id, request.user)
    except ERRORES as exc:
        if status != 409 or isinstance(exc, CasoNoDisponible):
            status, error = _error(exc)
    return _render_detalle(request, caso, status=status, error=error, decision_form=form, bloqueado=status in (409,503))


@never_cache
@roles_required(ADMINISTRACION)
@require_POST
def registrar_prueba(request, recomendacion_id):
    opciones, caso, error, status = None, None, None, 200
    try:
        opciones = services.opciones_recomendaciones(request.user)
    except ERRORES as exc:
        status, error = _error(exc)
    form = PruebaForm(request.POST, opciones=opciones)
    if status == 200:
        if form.is_valid():
            datos = form.normalizado
            try:
                resultado = services.registrar_prueba(recomendacion_id, datos['cambio'], datos['responsable_id'], datos['periodos'], request.user)
                messages.success(request, 'Prueba controlada registrada.')
                return redirect('recomendaciones:prueba', prueba_id=resultado['prueba']['id'])
            except ERRORES as exc:
                status, error = _error(exc, form)
        else:
            status = 400
    try:
        caso = services.obtener_recomendacion(recomendacion_id, request.user)
    except ERRORES as exc:
        if status != 409 or isinstance(exc, CasoNoDisponible):
            status, error = _error(exc)
    return _render_detalle(request, caso, status=status, error=error, prueba_form=form, bloqueado=status in (409,503))


@never_cache
@roles_required(ADMINISTRACION)
@require_GET
def prueba(request, prueba_id):
    try:
        datos = services.obtener_prueba(prueba_id, request.user)
    except ERRORES as exc:
        status, error = _error(exc)
        return render(request, 'recomendaciones/prueba.html', _contexto(request, error=error, bloqueado=True), status=status)
    return render(request, 'recomendaciones/prueba.html', _contexto(request, datos['caso'], prueba=datos['prueba'], version_form=VersionForm(initial={'version_esperada':datos['prueba']['version']})), status=200)


@never_cache
@roles_required(ADMINISTRACION)
@require_POST
def evaluar_prueba(request, prueba_id):
    form = VersionForm(request.POST)
    datos, status, error = None, 400, None
    if form.is_valid():
        try:
            datos = services.evaluar_prueba(prueba_id, request.user, form.cleaned_data['version_esperada'])
            messages.success(request, 'Evaluación de la prueba registrada. Revisa sus límites de comparabilidad.')
            return redirect('recomendaciones:prueba', prueba_id=datos['prueba']['id'])
        except ERRORES as exc:
            status, error = _error(exc, form)
    try:
        datos = services.obtener_prueba(prueba_id, request.user)
    except ERRORES as exc:
        if status != 409 or isinstance(exc, CasoNoDisponible):
            status, error = _error(exc)
    return render(request, 'recomendaciones/prueba.html', _contexto(request, datos['caso'] if datos else None, prueba=datos['prueba'] if datos else None, version_form=form, error=error, bloqueado=status in (409,503)), status=status)
