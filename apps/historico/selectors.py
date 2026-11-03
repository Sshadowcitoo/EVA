"""Selección de instantáneas y evidencia vigente, sin lecturas de archivos."""
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.db.models import F, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce, TruncTime

from apps.analisis.elegibilidad import evaluar_elegibilidad
from apps.analisis.models import AnalisisServicio, IntentoAnalisis, ResultadoComponente, RevisionAnalisis
from apps.captura.models import FotografiaServicio, Servicio
from apps.captura.protocolo import CRITERIOS
from .contracts import FiltrosInvalidos, ZONA_HORARIA


def opciones_historico():
    def opciones(filas):
        unicos = {}
        for codigo, nombre in filas:
            if codigo and codigo not in unicos:
                unicos[codigo] = nombre or codigo
        return [dict(codigo=c, nombre=n) for c, n in sorted(unicos.items(), key=lambda item: (item[1], item[0]))]
    servicios = Servicio.objects.order_by('-fecha_creacion', '-pk')
    from apps.captura.models import ServicioComponente
    componentes = ServicioComponente.objects.order_by('-servicio__fecha_creacion', '-servicio_id', '-pk')
    return dict(platos=opciones(servicios.values_list('plato', 'plato_nombre')),
                porciones=opciones(servicios.values_list('tipo_porcion', 'porcion_nombre')),
                componentes=opciones(componentes.values_list('componente_codigo', 'componente_nombre')),
                contexto_disponible=False)


def validar_codigos(filtros):
    opciones = opciones_historico()
    errores = {}
    for campo, plural in [('plato', 'platos'), ('componente', 'componentes'), ('porcion', 'porciones')]:
        if filtros[campo] is not None and filtros[campo] not in {o['codigo'] for o in opciones[plural]}:
            errores[campo] = 'El código no aparece en los registros históricos.'
    consulta = Servicio.objects.all()
    if filtros['plato']:
        consulta = consulta.filter(plato=filtros['plato'])
    if filtros['componente']:
        consulta = consulta.filter(composicion__componente_codigo=filtros['componente'])
    if filtros['porcion']:
        consulta = consulta.filter(tipo_porcion=filtros['porcion'])
    if not errores and any(filtros[c] for c in ('plato', 'componente', 'porcion')) and not consulta.exists():
        campo = 'componente' if filtros['componente'] else 'porcion' if filtros['porcion'] else 'plato'
        errores[campo] = 'La combinación no aparece en los registros históricos.'
    if errores:
        raise FiltrosInvalidos(errores)


def seleccionar(filtros):
    validar_codigos(filtros)
    ultimo = AnalisisServicio.objects.filter(servicio_id=OuterRef('pk')).order_by('-creado_en', '-pk')
    primero_servido = FotografiaServicio.objects.filter(servicio_id=OuterRef('pk'), etapa='SERVIDO').order_by('fecha', 'pk')
    consulta = Servicio.objects.annotate(
        analisis_actual_id=Subquery(ultimo.values('pk')[:1]),
        origen_actual=Subquery(ultimo.values('origen')[:1]),
        fecha_servido_analitica=Coalesce(Subquery(ultimo.values('foto_servido__fecha')[:1]), Subquery(primero_servido.values('fecha')[:1])),
    ).filter(Q(origen_actual__isnull=True) | ~Q(origen_actual='SIMULADO'))
    if filtros['plato']:
        consulta = consulta.filter(plato=filtros['plato'])
    if filtros['porcion']:
        consulta = consulta.filter(tipo_porcion=filtros['porcion'])
    if filtros['componente']:
        consulta = consulta.filter(composicion__componente_codigo=filtros['componente'])
    consulta = consulta.distinct()
    temporal = any(filtros[c] is not None for c in ('inicio', 'fin', 'hora_desde', 'hora_hasta'))
    sin_fecha = consulta.filter(fecha_servido_analitica__isnull=True).count() if temporal else 0
    if filtros['inicio']:
        consulta = consulta.filter(fecha_servido_analitica__gte=filtros['inicio'])
    if filtros['fin']:
        consulta = consulta.filter(fecha_servido_analitica__lt=filtros['fin'])
    if filtros['hora_desde'] is not None:
        consulta = consulta.annotate(hora_local=TruncTime('fecha_servido_analitica', tzinfo=ZoneInfo(ZONA_HORARIA))).filter(
            hora_local__gte=filtros['hora_desde'], hora_local__lt=filtros['hora_hasta'])
    servicios = list(consulta.order_by(F('fecha_servido_analitica').desc(nulls_last=True), '-pk').prefetch_related('composicion'))
    ids = [s.analisis_actual_id for s in servicios if s.analisis_actual_id]
    analisis = AnalisisServicio.objects.filter(pk__in=ids).select_related(
        'foto_servido', 'foto_retorno', 'intento_vigente').prefetch_related(
            Prefetch('intentos', queryset=IntentoAnalisis.objects.order_by('-numero'), to_attr='_intentos_ordenados'),
            Prefetch('intento_vigente__resultados', queryset=ResultadoComponente.objects.select_related('servicio_componente'), to_attr='_resultados'),
            Prefetch('intento_vigente__revisiones', queryset=RevisionAnalisis.objects.filter(vigente=True), to_attr='_revisiones'),
        )
    por_id = {a.pk: a for a in analisis}
    datos = []
    for servicio in servicios:
        a = por_id.get(servicio.analisis_actual_id)
        intento = a.intento_vigente if a else None
        resultados = intento._resultados if intento else []
        revision = intento._revisiones[0] if intento and intento._revisiones else None
        componentes = list(servicio.composicion.all())
        motivo = motivo_exclusion(servicio, a, intento, resultados, revision, componentes)
        datos.append(dict(servicio=servicio, analisis=a, intento=intento, resultados=resultados,
                          componentes=componentes, motivo=motivo, fecha=servicio.fecha_servido_analitica))
    advertencias = [f'{sin_fecha} servicios sin fecha de servido no se pueden asignar al periodo u horario solicitado.'] if sin_fecha else []
    return datos, advertencias


def _decimal(valor):
    try:
        numero = Decimal(str(valor))
        return numero if numero.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _resultado_valido(r):
    porcentaje, inicial, residual, confianza, umbral = map(_decimal, (
        r.porcentaje, r.area_inicial, r.area_residual, r.confianza, r.umbral_aplicado))
    if any(v is None for v in (porcentaje, inicial, residual, confianza, umbral)):
        return False
    return (not r.motivo and 0 <= porcentaje <= 100 and inicial > 0 and residual >= 0 and 0 <= umbral <= confianza <= 1
            and abs(porcentaje - 100 * residual / inicial) <= Decimal('0.0001'))


def motivo_exclusion(servicio, analisis, intento, resultados, revision, componentes):
    if servicio.estado_captura == 'ANULADO':
        return 'ANULADO'
    if servicio.fecha_servido_analitica is None:
        return 'SIN_FECHA_SERVIDO'
    if servicio.estado_captura != 'PAR_COMPLETO':
        return 'PAR_INCOMPLETO'
    if analisis is None:
        return 'SIN_ANALISIS'
    if (intento is None or intento.estado != 'COMPLETADO' or not analisis._intentos_ordenados
            or analisis._intentos_ordenados[0].pk != intento.pk):
        return 'INTENTO_NO_COMPLETADO'
    if revision is None:
        return 'SIN_REVISION'
    if revision.decision != 'CONFIRMADO':
        return revision.decision if revision.decision in ('RECHAZADO', 'NO_CONCLUYENTE') else 'REVISION_NO_CONFIRMADA'
    esperados = {c.pk for c in componentes}
    if not esperados or esperados != {r.servicio_componente_id for r in resultados}:
        return 'COMPONENTES_INVALIDOS'
    fotos = [(analisis.foto_servido, 'SERVIDO'), (analisis.foto_retorno, 'RETORNO')]
    for foto, etapa in fotos:
        if (foto.servicio_id != servicio.pk or foto.etapa != etapa or not foto.vigente
                or not foto.protocolo_version or not isinstance(foto.checklist, dict)
                or set(foto.checklist) != set(CRITERIOS) or any(v is not True for v in foto.checklist.values())):
            return 'CRITERIOS_INVALIDOS'
    if (analisis.foto_servido.protocolo_version != analisis.foto_retorno.protocolo_version
            or not analisis.version_modelo or not analisis.version_configuracion):
        return 'CRITERIOS_INVALIDOS'
    elegibilidad = evaluar_elegibilidad(
        origen=analisis.origen, estado_intento=intento.estado,
        estados_componentes=[r.estado for r in resultados],
        configuracion_aprobada=all(r.configuracion_aprobada for r in resultados),
        evidencia_disponible=False, decision=revision.decision,
        intento_id=intento.pk, intento_revisado_id=revision.intento_id)
    if not elegibilidad['apto_historico'] or any(not _resultado_valido(r) for r in resultados):
        return 'CRITERIOS_INVALIDOS'
    return None
