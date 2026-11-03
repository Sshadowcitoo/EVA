"""Normalización compartida de filtros, sin consultas ni escrituras."""
from collections.abc import Mapping
from datetime import date, datetime, time, timedelta
import re
from zoneinfo import ZoneInfo

from .contracts import FiltrosHistorico, FiltrosInvalidos, ZONA_HORARIA


def normalizar_filtros(datos: Mapping) -> FiltrosHistorico:
    errores, salida = {}, {}
    for campo, maximo in [('plato', 50), ('componente', 50), ('porcion', 20)]:
        valor = datos.get(campo)
        if valor is None or valor == '':
            salida[campo] = None
        elif not isinstance(valor, str) or len(valor.strip()) > maximo or not re.fullmatch(r'[-a-zA-Z0-9_]+', valor.strip()):
            errores[campo] = 'Usa un código histórico válido.'
        else:
            salida[campo] = valor.strip()
    for campo in ('desde', 'hasta'):
        valor = datos.get(campo)
        salida[campo] = None
        try:
            if valor is None or valor == '':
                continue
            if isinstance(valor, date) and not isinstance(valor, datetime):
                salida[campo] = valor
            elif isinstance(valor, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', valor):
                salida[campo] = date.fromisoformat(valor)
            else:
                raise ValueError()
            # Se necesita construir el límite exclusivo del día siguiente.
            if salida[campo] == date.max:
                raise ValueError()
        except ValueError:
            errores[campo] = 'Usa una fecha válida en formato AAAA-MM-DD.'
    for campo in ('hora_desde', 'hora_hasta'):
        valor = datos.get(campo)
        salida[campo] = None
        try:
            if valor is None or valor == '':
                continue
            if isinstance(valor, time) and valor.tzinfo is None and valor.second == 0 and valor.microsecond == 0:
                salida[campo] = valor
            elif isinstance(valor, str) and re.fullmatch(r'\d{2}:\d{2}', valor):
                salida[campo] = time.fromisoformat(valor)
            else:
                raise ValueError()
        except ValueError:
            errores[campo] = 'Usa una hora local válida en formato HH:MM.'
    if datos.get('origen') not in (None, '', 'REAL'):
        errores['origen'] = 'El histórico analítico solo consulta evidencia REAL.'
    if salida['desde'] and salida['hasta'] and salida['desde'] > salida['hasta']:
        errores['hasta'] = 'La fecha final no puede ser anterior a la inicial.'
    h_desde, h_hasta = salida['hora_desde'], salida['hora_hasta']
    if (h_desde is None) != (h_hasta is None):
        errores['hora_hasta'] = 'Indica ambas horas o deja ambas vacías.'
    elif h_desde is not None and h_hasta is not None and h_desde >= h_hasta:
        errores['hora_hasta'] = 'El rango debe avanzar dentro del mismo día; divide los horarios nocturnos.'
    if errores:
        raise FiltrosInvalidos(errores)
    zona = ZoneInfo(ZONA_HORARIA)
    salida.update(inicio=datetime.combine(salida['desde'], time.min, zona) if salida['desde'] else None,
                  fin=datetime.combine(salida['hasta'] + timedelta(days=1), time.min, zona) if salida['hasta'] else None,
                  zona_horaria=ZONA_HORARIA, origen='REAL')
    return salida
