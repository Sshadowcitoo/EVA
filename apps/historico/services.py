"""Puntos de conexión estables; consultas y persistencia todavía no implementadas.

Las vistas deben traducir BackendHistoricoNoDisponible a 503. No importar fixtures
ni devolver muestras sintéticas desde estas funciones.
"""
from .contracts import (
    BackendHistoricoNoDisponible, Comparacion, FiltrosHistorico,
    OpcionesHistorico, Percepcion, ResumenHistorico,
)
from .filtros import normalizar_filtros  # Entrada pública compartida con las vistas.


def opciones_historico() -> OpcionesHistorico:
    raise BackendHistoricoNoDisponible('Las opciones históricas todavía no están conectadas.')


def consultar_historico(filtros: FiltrosHistorico, pagina: int = 1) -> ResumenHistorico:
    raise BackendHistoricoNoDisponible('La consulta del histórico todavía no está conectada.')


def comparar_periodos(filtros_a: FiltrosHistorico, filtros_b: FiltrosHistorico) -> Comparacion:
    raise BackendHistoricoNoDisponible('La comparación de periodos todavía no está conectada.')


def obtener_percepcion(servicio_id, usuario) -> Percepcion:
    raise BackendHistoricoNoDisponible('El registro de percepción todavía no está conectado.')


def registrar_percepcion(servicio_id, categoria, motivo, usuario, version_esperada: int) -> Percepcion:
    raise BackendHistoricoNoDisponible('El registro de percepción todavía no está conectado.')
