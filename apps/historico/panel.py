"""Proyección de lectura de Indicadores, independiente de las filas paginadas."""
from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from .contracts import ZONA_HORARIA
from .indicadores import calcular

MAX_SEMANAS_GRAFICO = 52
ZONA = ZoneInfo(ZONA_HORARIA)


def _lunes(fecha):
    return fecha - timedelta(days=fecha.weekday())


def _semana(lunes, desde, hasta, valores):
    inicio = max(desde, lunes)
    fin = lunes + timedelta(days=min(6, (hasta - lunes).days))
    indicadores = calcular(valores, {'t': None, 'version_criterio': None})
    return dict(inicio=inicio, fin=fin, parcial=inicio != lunes or fin.weekday() != 6,
                n=indicadores['n'], intensidad=indicadores['intensidad'])


def proyectar(datos, filtros, solicitado, grupos, nombres, claves, resumenes):
    opciones = []
    for g in resumenes:
        clave = claves[g['clave']]
        plato, componente, porcion = nombres[clave]
        opciones.append({**g, 'etiqueta': f'{plato} · {componente} · {porcion}',
                         'contexto_corto': (g['contexto_clave'] or '')[:12]})
    seleccion = solicitado or (opciones[0]['clave'] if len(opciones) == 1 else '')
    elegido = next((g for g in opciones if g['clave'] == seleccion), None)
    fechas = {str(d['servicio'].pk): d['fecha'].astimezone(ZONA).date() for d in datos if d['fecha']}
    desde = filtros['desde'] or min(fechas.values(), default=None)
    hasta = filtros['hasta'] or max(fechas.values(), default=None)
    panel = dict(opciones=opciones, grupo=elegido, seleccion_invalida=bool(solicitado and not elegido),
                 desde=desde, hasta=hasta, semanas=[], ultima=None, periodo_extenso=False, perfiles={})
    if not elegido:
        return panel
    clave = claves[seleccion]
    por_semana = defaultdict(list)
    if elegido['comparable'] and desde and hasta and desde <= hasta:
        for servicio, porcentaje in grupos[clave].items():
            if servicio in fechas:
                por_semana[_lunes(fechas[servicio])].append(porcentaje)
        primero, ultimo = _lunes(desde), _lunes(hasta)
        panel['ultima'] = _semana(ultimo, desde, hasta, por_semana[ultimo])
        cantidad = (ultimo - primero).days // 7 + 1
        panel['periodo_extenso'] = cantidad > MAX_SEMANAS_GRAFICO
        if not panel['periodo_extenso']:
            panel['semanas'] = [
                _semana(lunes, desde, hasta, por_semana[lunes])
                for i in range(cantidad)
                for lunes in (primero + timedelta(weeks=i),)
            ]
    if elegido['comparable']:
        for dimension, posicion in [('platos', 0), ('componentes', 1), ('porciones', 2)]:
            perfiles = []
            for g in opciones:
                otra = claves[g['clave']]
                if otra[:posicion] == clave[:posicion] and otra[posicion + 1:] == clave[posicion + 1:]:
                    perfiles.append(dict(nombre=nombres[otra][posicion], **g['indicadores']))
            panel['perfiles'][dimension] = sorted(perfiles, key=lambda p: p['nombre'].casefold())
    return panel
