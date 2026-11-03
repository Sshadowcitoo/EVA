"""Agregación descriptiva por grupo, manteniendo unidades y cobertura."""
from collections import Counter
from decimal import Decimal
import hashlib
import json
from zoneinfo import ZoneInfo

from django.core.paginator import Paginator
from .configuration import criterio_presencia
from .contracts import CONTRACT_VERSION, ZONA_HORARIA


def calcular(valores, criterio):
    n = len(valores)
    t = criterio['t']
    motivos = []
    if not n:
        motivos.append('SIN_REGISTROS_APTOS')
    if t is None:
        motivos.append('SIN_CRITERIO_PRESENCIA')
    return dict(n=n, **criterio,
                prevalencia=Decimal(100) * sum(p > t for p in valores) / n if n and t is not None else None,
                intensidad=sum(valores, Decimal(0)) / n if n else None,
                motivos_no_disponible=motivos)


def resumir(datos, advertencias, filtros, pagina):
    criterio = criterio_presencia()
    filas, grupos = [], {}
    motivos = Counter(d['motivo'] for d in datos if d['motivo'])
    aptos = sum(d['motivo'] is None for d in datos)
    for dato in datos:
        servicio, a = dato['servicio'], dato['analisis']
        resultados = {r.servicio_componente_id: r for r in dato['resultados']}
        composicion = sorted(dato['componentes'], key=lambda c: (c.componente_nombre, c.componente_codigo))
        seleccionados = [c for c in composicion if not filtros['componente'] or c.componente_codigo == filtros['componente']]
        # Un servicio sin composición también debe ser visible como excluido.
        for comp in seleccionados or [None]:
            codigo = comp.componente_codigo if comp else ''
            resultado = resultados.get(comp.pk) if comp else None
            porcentaje = resultado.porcentaje if dato['motivo'] is None and resultado else None
            filas.append(dict(fila_id=f'{servicio.pk}/{codigo}', servicio_id=str(servicio.pk),
                fecha_servido=dato['fecha'].astimezone(ZoneInfo(ZONA_HORARIA)) if dato['fecha'] else None,
                plato_codigo=servicio.plato, plato_nombre=servicio.get_plato_display(),
                componente_codigo=codigo, componente_nombre=comp.componente_nombre if comp else 'Sin composición histórica',
                porcion_codigo=servicio.tipo_porcion, porcion_nombre=servicio.get_tipo_porcion_display(),
                origen=a.origen if a and a.origen in ('REAL', 'SIMULADO') else None,
                estado='APTO' if dato['motivo'] is None else 'EXCLUIDO',
                porcentaje_visual=porcentaje, motivo_exclusion=dato['motivo']))
            if dato['motivo'] is not None:
                continue
            clave = (servicio.plato, codigo, servicio.tipo_porcion, None,
                     a.version_modelo, a.version_configuracion, a.foto_servido.protocolo_version)
            grupos.setdefault(clave, {})[str(servicio.pk)] = porcentaje
    salida_grupos = []
    for clave, valores in sorted(grupos.items(), key=lambda item: repr(item[0])):
        plato, componente, porcion, contexto, modelo, config, protocolo = clave
        identificador = hashlib.sha256(json.dumps(clave, ensure_ascii=True).encode()).hexdigest()[:24]
        salida_grupos.append(dict(clave='grupo-' + identificador, plato_codigo=plato, componente_codigo=componente,
            porcion_codigo=porcion, contexto_clave=contexto, version_modelo=modelo,
            version_configuracion=config, protocolo_version=protocolo,
            comparable=contexto is not None, motivos=[] if contexto is not None else ['SIN_CONTEXTO_HISTORICO'],
            indicadores=calcular(list(valores.values()), criterio)))
    if len(salida_grupos) == 1:
        cabecera = salida_grupos[0]['indicadores'].copy()
    else:
        cabecera = calcular([], criterio)
        if salida_grupos:
            cabecera['motivos_no_disponible'] = ['MULTIPLES_GRUPOS']
        elif not datos:
            cabecera['motivos_no_disponible'] = ['SIN_DATOS'] + (['SIN_CRITERIO_PRESENCIA'] if criterio['t'] is None else [])
    paginador = Paginator(filas, 30)
    pagina_actual = paginador.get_page(pagina)
    candidatos = len(datos)
    return dict(version_contrato=CONTRACT_VERSION, solo_pruebas=False, filtros=filtros,
        filas=list(pagina_actual.object_list),
        paginacion=dict(pagina=pagina_actual.number, paginas=paginador.num_pages, total_filas=len(filas), por_pagina=30),
        resumen=dict(candidatos=candidatos, aptos=aptos, excluidos=candidatos - aptos,
                     proporcion_excluidos=Decimal(100) * (candidatos - aptos) / candidatos if candidatos else None,
                     motivos=dict(motivos)),
        indicadores=cabecera, grupos=salida_grupos, advertencias=advertencias)


def comparar_resumenes(referencia, comparado):
    motivos = []
    if len(referencia['grupos']) != 1 or len(comparado['grupos']) != 1:
        motivos.append('GRUPOS_NO_COMPARABLES')
    else:
        primero, segundo = referencia['grupos'][0], comparado['grupos'][0]
        campos = ('plato_codigo', 'componente_codigo', 'porcion_codigo', 'contexto_clave',
                  'version_modelo', 'version_configuracion', 'protocolo_version')
        if any(primero[c] != segundo[c] for c in campos):
            motivos.append('GRUPOS_INCOMPATIBLES')
        for grupo in (primero, segundo):
            if not grupo['comparable']:
                motivos.extend(grupo['motivos'] or ['NO_COMPARABLE'])
    if not referencia['resumen']['aptos'] or not comparado['resumen']['aptos']:
        motivos.append('SIN_REGISTROS_APTOS')
    comparable = not motivos
    diferencias = dict(prevalencia_pp=None, intensidad_pp=None)
    if comparable:
        a, b = referencia['indicadores'], comparado['indicadores']
        if a['intensidad'] is not None and b['intensidad'] is not None:
            diferencias['intensidad_pp'] = b['intensidad'] - a['intensidad']
        if (a['t'], a['version_criterio']) != (b['t'], b['version_criterio']):
            motivos.append('CRITERIOS_PRESENCIA_DIFERENTES')
        elif a['prevalencia'] is not None and b['prevalencia'] is not None:
            diferencias['prevalencia_pp'] = b['prevalencia'] - a['prevalencia']
        else:
            motivos.append('SIN_CRITERIO_PRESENCIA')
    return dict(referencia=referencia, comparado=comparado, comparable=comparable,
                motivos=list(dict.fromkeys(motivos)), diferencias=diferencias)
