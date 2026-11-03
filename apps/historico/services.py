"""Puntos de conexión del contrato v1, sin acoplar las vistas a modelos internos."""
from django.db import transaction
from .contracts import (
    Comparacion, FiltrosHistorico, FiltrosInvalidos,
    OpcionesHistorico, Percepcion, ResumenHistorico,
)
from .filtros import normalizar_filtros  # Entrada pública compartida con las vistas.
from . import indicadores, percepcion, selectors


def opciones_historico() -> OpcionesHistorico:
    with transaction.atomic():
        return selectors.opciones_historico()


def consultar_historico(filtros: FiltrosHistorico, pagina: int = 1) -> ResumenHistorico:
    filtros = normalizar_filtros(filtros)
    if type(pagina) is not int or pagina < 1:
        raise FiltrosInvalidos({'page': 'La página debe ser un entero positivo.'})
    with transaction.atomic():
        datos, advertencias = selectors.seleccionar(filtros)
        return indicadores.resumir(datos, advertencias, filtros, pagina)


def comparar_periodos(filtros_a: FiltrosHistorico, filtros_b: FiltrosHistorico) -> Comparacion:
    a, b = normalizar_filtros(filtros_a), normalizar_filtros(filtros_b)
    if any(f[c] is None for f in (a, b) for c in ('inicio', 'fin')):
        raise FiltrosInvalidos({'__all__': 'Define inicio y fin de ambos periodos.'})
    if a['inicio'] < b['fin'] and b['inicio'] < a['fin']:
        raise FiltrosInvalidos({'__all__': 'Los periodos no deben superponerse.'})
    campos = ('plato', 'componente', 'porcion', 'hora_desde', 'hora_hasta', 'origen')
    if any(a[c] != b[c] for c in campos):
        raise FiltrosInvalidos({'__all__': 'Mantén los mismos filtros y horarios para ambos periodos.'})
    with transaction.atomic():
        return indicadores.comparar_resumenes(consultar_historico(a), consultar_historico(b))


def obtener_percepcion(servicio_id, usuario) -> Percepcion:
    return percepcion.obtener_percepcion(servicio_id, usuario)


def registrar_percepcion(servicio_id, categoria, motivo, usuario, version_esperada: int) -> Percepcion:
    return percepcion.registrar_percepcion(servicio_id, categoria, motivo, usuario, version_esperada)
