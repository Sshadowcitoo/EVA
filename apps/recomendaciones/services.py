"""Operaciones autorizadas y auditadas del bloque 7; sin fixtures productivas."""
from functools import wraps
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.catalogo.permissions import ADMINISTRACION, COCINA, tiene_rol
from apps.historico import services as historico
from apps.historico.contracts import FiltrosInvalidos
from ops.presentacion.aislamiento import lote_activo

from . import contracts as c, models as m, selectors
from .filtros import (normalizar_filtros, normalizar_periodo_evaluacion,
                      normalizar_decision, normalizar_prueba, _entero)
from .serialization import cargar, guardar, huella


def _permiso(usuario, escritura=False):
    if usuario is None or not tiene_rol(usuario, ADMINISTRACION):
        raise PermissionDenied('No tienes permiso para esta operación.')


def _operacion(funcion):
    @wraps(funcion)
    def ejecutar(*args, **kwargs):
        try:
            with transaction.atomic():
                return funcion(*args, **kwargs)
        except FiltrosInvalidos as exc:
            raise c.ParametrosInvalidos(exc.errores) from None
        except IntegrityError:
            raise c.ConflictoRecomendacion('Otro operador actualizó el caso. Actualiza antes de continuar.') from None
        except OperationalError as exc:
            if 'locked' in str(exc).lower():
                raise c.ConflictoRecomendacion('El caso se está actualizando. Actualiza antes de continuar.') from None
            raise
    return ejecutar


def _buscar(modelo, identificador, bloquear=False):
    try:
        pk = UUID(str(identificador))
    except (ValueError, TypeError, AttributeError):
        raise c.CasoNoDisponible('No se encontró el caso.') from None
    consulta = modelo.objects.select_for_update() if bloquear else modelo.objects
    try:
        return consulta.get(pk=pk)
    except modelo.DoesNotExist:
        raise c.CasoNoDisponible('No se encontró el caso.') from None


def _nombre(usuario):
    return usuario.get_full_name() or usuario.get_username()


def _responsables():
    return get_user_model().objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name__in=[COCINA, ADMINISTRACION])
    ).distinct().order_by('pk')


def _capturar(filtros):
    filtros = normalizar_periodo_evaluacion(filtros)
    datos, resumen, referencias, firma = selectors.seleccionar(filtros)
    criterios = selectors.criterios_actuales()
    chequeos, categoria = selectors.evaluar(datos, resumen, filtros, criterios)
    lote = lote_activo()
    dto = dict(id='', solo_pruebas=bool(lote), origen='SIMULADO' if lote else 'REAL',
        suficiencia='SUFICIENTE' if all(ch['cumple'] for ch in chequeos) else 'INSUFICIENTE',
        filtros=filtros, criterios=criterios, resumen=resumen['resumen'], indicadores=resumen['indicadores'],
        grupos=resumen['grupos'], chequeos=chequeos, motivos=[ch['motivo'] for ch in chequeos if not ch['cumple']],
        referencias=referencias, evaluada_en=timezone.now(), vigente=True, motivos_vigencia=[])
    return dto, categoria, firma


def _evaluacion(evaluacion):
    snapshot = cargar(evaluacion.snapshot)
    dto = snapshot['evaluacion']
    dto.update(id=str(evaluacion.pk), evaluada_en=evaluacion.fecha)
    try:
        _, _, _, firma = selectors.seleccionar(dto['filtros'])
        vigente = firma == snapshot['firma']
    except FiltrosInvalidos:
        vigente = False
    dto.update(vigente=vigente, motivos_vigencia=[] if vigente else ['La evidencia o los criterios cambiaron desde la evaluación.'])
    return dto


def _vigente(evaluacion):
    dto = _evaluacion(evaluacion)
    if not dto['vigente']:
        raise c.EvidenciaDesactualizada('La evidencia cambió. Genera una evaluación nueva.')
    return dto


def _decision(d):
    return dict(id=str(d.pk), decision=d.decision, justificacion=d.justificacion,
        autor_visible=_nombre(d.autor), fecha=d.fecha, version=d.version,
        sustituye_id=str(d.sustituye_id) if d.sustituye_id else None)


def _resumen_prueba(p):
    ultima = p.evaluaciones.order_by('-version').first()
    return dict(id=str(p.pk), estado=cargar(ultima.snapshot)['estado'] if ultima else 'REGISTRADA',
        cambio=p.cambio, responsable_nombre=_nombre(p.responsable), registrada_en=p.fecha, version=p.version)


def _caso(evaluacion, usuario):
    dto = _evaluacion(evaluacion)
    recomendacion = m.Recomendacion.objects.filter(evaluacion=evaluacion).first()
    decisiones = list(recomendacion.decisiones.select_related('autor').order_by('version')) if recomendacion else []
    actual = decisiones[-1] if decisiones else None
    admin = tiene_rol(usuario, ADMINISTRACION)
    puede_generar = admin and dto['vigente'] and dto['suficiencia'] == 'SUFICIENTE' and dto['criterios']['aprobada']
    propuesta = dict(id=str(recomendacion.pk), evaluacion_id=str(evaluacion.pk), categoria=recomendacion.categoria,
                    explicacion=recomendacion.explicacion, creada_en=recomendacion.fecha) if recomendacion else None
    return dict(evaluacion=dto, recomendacion=propuesta, decision_actual=_decision(actual) if actual else None,
        historial_decisiones=[_decision(d) for d in decisiones], version_esperada=recomendacion.version if recomendacion else 0,
        capacidades=dict(puede_evaluar=admin, puede_generar=bool(puede_generar and not recomendacion),
            puede_decidir=bool(admin and dto['vigente'] and recomendacion),
            puede_registrar_prueba=bool(admin and dto['vigente'] and actual and actual.decision == 'ACEPTADA'),
            puede_ver_analisis=tiene_rol(usuario, COCINA)),
        pruebas=[_resumen_prueba(p) for p in recomendacion.pruebas.select_related('responsable').order_by('fecha')] if recomendacion else [])


@_operacion
def opciones_recomendaciones(usuario):
    _permiso(usuario)
    config = selectors.criterios_actuales()
    versiones = [dict(version=config['version'], descripcion=config['descripcion'], aprobada=config['aprobada'])] if config['version'] else []
    return dict(historico=historico.opciones_historico(), versiones_criterios=versiones,
                responsables=[dict(id=u.pk, nombre=_nombre(u)) for u in _responsables()])


@_operacion
def evaluar_evidencia(filtros, version_criterios, usuario):
    _permiso(usuario, True)
    config = selectors.criterios_actuales()
    if version_criterios != config['version']:
        raise c.ParametrosInvalidos({'version_criterios': 'La versión seleccionada no está disponible.'})
    dto, categoria, firma = _capturar(filtros)
    opciones = historico.opciones_historico()
    nombres = {}
    for campo, plural in [('plato', 'platos'), ('componente', 'componentes'), ('porcion', 'porciones')]:
        codigo = dto['filtros'][campo]
        if codigo:
            nombres[campo] = next((o['nombre'] for o in opciones[plural] if o['codigo'] == codigo), codigo)
    evaluacion, _ = m.EvaluacionEvidencia.objects.get_or_create(huella=firma,
        defaults=dict(snapshot=guardar(dict(evaluacion=dto, categoria=categoria, firma=firma, nombres=nombres)), autor=usuario))
    return _caso(evaluacion, usuario)


@_operacion
def obtener_evaluacion(evaluacion_id, usuario):
    _permiso(usuario)
    return _caso(_buscar(m.EvaluacionEvidencia, evaluacion_id), usuario)


@_operacion
def generar_recomendacion(evaluacion_id, usuario):
    _permiso(usuario, True)
    evaluacion = _buscar(m.EvaluacionEvidencia, evaluacion_id, True)
    dto = _vigente(evaluacion)
    categoria = cargar(evaluacion.snapshot)['categoria']
    origen_admisible = (dto['origen'] == 'REAL' if not lote_activo()
                        else dto['solo_pruebas'] and dto['origen'] == 'SIMULADO')
    if dto['suficiencia'] != 'SUFICIENTE' or not dto['criterios']['aprobada'] or not origen_admisible or not categoria:
        raise c.ConflictoRecomendacion('La evidencia es insuficiente para generar una recomendación.')
    metricas, filtros = dto['indicadores'], dto['filtros']
    explicacion = (f"Regla {dto['criterios']['version']}; periodo {filtros['desde']} a {filtros['hasta']}; "
        f"n={metricas['n']}, intensidad visual={metricas['intensidad']} %, prevalencia={metricas['prevalencia']} %. "
        'Propuesta para revisión humana. Las imágenes no demuestran causas ni cambios de preferencia.')
    m.Recomendacion.objects.get_or_create(evaluacion=evaluacion, defaults=dict(categoria=categoria, explicacion=explicacion))
    return _caso(evaluacion, usuario)


@_operacion
def obtener_recomendacion(recomendacion_id, usuario):
    _permiso(usuario)
    return _caso(_buscar(m.Recomendacion, recomendacion_id).evaluacion, usuario)


@_operacion
def decidir_recomendacion(recomendacion_id, decision, justificacion, usuario, version_esperada):
    _permiso(usuario, True)
    datos = normalizar_decision(dict(decision=decision, justificacion=justificacion, version_esperada=version_esperada))
    r = _buscar(m.Recomendacion, recomendacion_id, True)
    _vigente(r.evaluacion)
    actual = r.decisiones.order_by('-version').first()
    if (actual and actual.autor_id == usuario.pk and actual.decision == datos['decision']
            and actual.justificacion == datos['justificacion'] and datos['version_esperada'] in (r.version, r.version - 1)):
        return _caso(r.evaluacion, usuario)
    if datos['version_esperada'] != r.version:
        raise c.ConflictoRecomendacion('La decisión cambió. Actualiza y revisa tu borrador.')
    if r.version >= 2**31 - 1:
        raise c.ConflictoRecomendacion('Se alcanzó el límite de versiones del caso.')
    if m.Recomendacion.objects.filter(pk=r.pk, version=r.version).update(version=r.version + 1) != 1:
        raise c.ConflictoRecomendacion('La decisión cambió durante el guardado.')
    m.DecisionRecomendacion.objects.create(recomendacion=r, decision=datos['decision'],
        justificacion=datos['justificacion'], autor=usuario, version=r.version + 1, sustituye=actual)
    return _caso(r.evaluacion, usuario)


@_operacion
def consultar_recomendaciones(filtros, usuario, pagina=1):
    _permiso(usuario)
    if type(pagina) is not int or pagina < 1:
        raise c.ParametrosInvalidos({'page': 'La página debe ser un entero positivo.'})
    # El DTO normalizado contiene el filtro histórico anidado; los formularios envían plano.
    entrada = dict(filtros.get('historico', filtros))
    entrada.update({k: filtros.get(k) for k in ('categoria', 'decision', 'suficiencia')})
    filtros = normalizar_filtros(entrada)
    filas = []
    for e in m.EvaluacionEvidencia.objects.order_by('-fecha', '-pk'):
        caso = _caso(e, usuario)
        dto, r, d = caso['evaluacion'], caso['recomendacion'], caso['decision_actual']
        guardado, solicitado = dto['filtros'], filtros['historico']
        if any(solicitado[k] is not None and solicitado[k] != guardado[k] for k in ('plato', 'componente', 'porcion', 'hora_desde', 'hora_hasta')):
            continue
        if solicitado['inicio'] and guardado['inicio'] < solicitado['inicio']:
            continue
        if solicitado['fin'] and guardado['fin'] > solicitado['fin']:
            continue
        valores = dict(categoria=r['categoria'] if r else None, decision=d['decision'] if d else None, suficiencia=dto['suficiencia'])
        if any(filtros[k] and filtros[k] != v for k, v in valores.items()):
            continue
        nombres = cargar(e.snapshot).get('nombres', {})
        filas.append(dict(evaluacion_id=str(e.pk), recomendacion_id=r['id'] if r else None,
            plato_nombre=nombres.get('plato', guardado['plato'] or 'Varios platos'),
            componente_nombre=nombres.get('componente', guardado['componente'] or 'Varios componentes'),
            porcion_nombre=nombres.get('porcion', guardado['porcion'] or 'Varias porciones'),
            **valores, vigente=dto['vigente'], n=dto['resumen']['aptos'], evaluada_en=e.fecha))
    resumen = dict(total=len(filas), insuficientes=sum(f['suficiencia'] == 'INSUFICIENTE' for f in filas),
        sin_decision=sum(f['recomendacion_id'] is not None and f['decision'] is None for f in filas),
        en_observacion=sum(f['decision'] == 'EN_OBSERVACION' for f in filas), obsoletas=sum(not f['vigente'] for f in filas))
    paginador = Paginator(filas, 30)
    page = paginador.get_page(pagina)
    return dict(version_contrato=c.CONTRACT_VERSION, solo_pruebas=bool(lote_activo()), filtros=filtros, filas=list(page.object_list),
        paginacion=dict(pagina=page.number, paginas=paginador.num_pages, total_filas=len(filas), por_pagina=30), resumen=resumen)


def _aceptacion(r):
    decision = r.decisiones.order_by('-version').first()
    if not decision or decision.decision != 'ACEPTADA':
        raise c.ConflictoRecomendacion('La recomendación debe estar aceptada.')
    return decision


@_operacion
def registrar_prueba(recomendacion_id, cambio, responsable_id, periodos, usuario):
    _permiso(usuario, True)
    datos = normalizar_prueba(dict(cambio=cambio, responsable_id=responsable_id, **periodos))
    r = _buscar(m.Recomendacion, recomendacion_id, True)
    _vigente(r.evaluacion)
    aceptacion = _aceptacion(r)
    responsable = _responsables().filter(pk=datos['responsable_id']).first()
    if not responsable:
        raise c.ParametrosInvalidos({'responsable_id': 'Selecciona un responsable activo de Cocina o Administración.'})
    firma = huella(dict(recomendacion=str(r.pk), aceptacion=str(aceptacion.pk), **datos))
    p, _ = m.PruebaControlada.objects.get_or_create(huella=firma, defaults=dict(recomendacion=r,
        aceptacion=aceptacion, cambio=datos['cambio'], responsable=responsable, autor=usuario, periodos=guardar(datos['periodos'])))
    return _detalle_prueba(p, usuario)


def _detalle_prueba(p, usuario):
    caso = _caso(p.recomendacion.evaluacion, usuario)
    ultima = p.evaluaciones.order_by('-version').first()
    valores = cargar(ultima.snapshot) if ultima else dict(comparacion=None, motivos=[])
    actual = caso['decision_actual']
    vigente = caso['evaluacion']['vigente'] and actual is not None and actual['id'] == str(p.aceptacion_id)
    dto = dict(**_resumen_prueba(p), recomendacion_id=str(p.recomendacion_id), aceptacion_id=str(p.aceptacion_id),
        responsable_id=p.responsable_id, periodos=cargar(p.periodos), registrada_por=_nombre(p.autor),
        evaluada_en=ultima.fecha if ultima else None, comparacion=valores['comparacion'], motivos=valores['motivos'],
        puede_evaluar=bool(tiene_rol(usuario, ADMINISTRACION) and vigente))
    return dict(caso=caso, prueba=dto)


@_operacion
def obtener_prueba(prueba_id, usuario):
    _permiso(usuario)
    return _detalle_prueba(_buscar(m.PruebaControlada, prueba_id), usuario)


@_operacion
def evaluar_prueba(prueba_id, usuario, version_esperada):
    _permiso(usuario, True)
    version = _entero(version_esperada, 'version_esperada')
    p = _buscar(m.PruebaControlada, prueba_id, True)
    r = _buscar(m.Recomendacion, p.recomendacion_id, True)
    _vigente(r.evaluacion)
    if _aceptacion(r).pk != p.aceptacion_id:
        raise c.EvidenciaDesactualizada('La aceptación original de la prueba fue sustituida.')
    if p.version != version:
        raise c.ConflictoRecomendacion('La prueba cambió. Actualiza antes de reevaluar.')
    if version >= 2**31 - 1:
        raise c.ConflictoRecomendacion('Se alcanzó el límite de versiones de la prueba.')
    filtros = cargar(r.evaluacion.snapshot)['evaluacion']['filtros']
    periodos = cargar(p.periodos)
    referencia = dict(filtros, desde=periodos['referencia_desde'], hasta=periodos['referencia_hasta'])
    intervencion = dict(filtros, desde=periodos['intervencion_desde'], hasta=periodos['intervencion_hasta'])
    comparacion = historico.comparar_periodos(referencia, intervencion)
    evaluable = comparacion['comparable'] and not comparacion['motivos'] and all(v is not None for v in comparacion['diferencias'].values())
    snapshot = dict(estado='EVALUADA' if evaluable else 'NO_EVALUABLE', comparacion=comparacion,
                    motivos=comparacion['motivos'] or ([] if evaluable else ['DATOS_NO_COMPARABLES']))
    if m.PruebaControlada.objects.filter(pk=p.pk, version=version).update(version=version + 1) != 1:
        raise c.ConflictoRecomendacion('La prueba cambió durante el guardado.')
    m.EvaluacionPrueba.objects.create(prueba=p, version=version + 1, snapshot=guardar(snapshot), autor=usuario)
    p.refresh_from_db()
    return _detalle_prueba(p, usuario)
