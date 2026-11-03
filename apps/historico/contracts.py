"""Contrato v1 del bloque 6: nombres y tipos consumidos por las vistas.

Los DTO son diccionarios Python; Decimal se redondea únicamente al presentar.
No contienen instancias ORM, rutas de almacenamiento ni datos del comensal.
"""
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal, TypedDict

CONTRACT_VERSION = 1
ZONA_HORARIA = 'America/Guayaquil'
CATEGORIAS_PERCEPCION = (
    ('INSUFICIENTE', 'Insuficiente'), ('ADECUADA', 'Adecuada'),
    ('EXCESIVA', 'Excesiva'), ('NO_INFORMADO', 'No informado'),
)
MAX_MOTIVO = 1000


class ErrorHistorico(Exception):
    codigo = 'ERROR_HISTORICO'


class FiltrosInvalidos(ErrorHistorico):
    codigo = 'FILTROS_INVALIDOS'

    def __init__(self, errores: dict[str, str]):
        self.errores = errores
        super().__init__('Revisa los filtros indicados.')


class BackendHistoricoNoDisponible(ErrorHistorico):
    codigo = 'BACKEND_PENDIENTE'


class ServicioNoDisponible(ErrorHistorico):
    codigo = 'SERVICIO_NO_DISPONIBLE'


class ConflictoPercepcion(ErrorHistorico):
    codigo = 'CONFLICTO_PERCEPCION'


class FiltrosHistorico(TypedDict):
    plato: str | None
    componente: str | None
    porcion: str | None
    desde: date | None
    hasta: date | None
    inicio: datetime | None
    fin: datetime | None
    hora_desde: time | None
    hora_hasta: time | None
    zona_horaria: str
    origen: Literal['REAL']


class Opcion(TypedDict):
    codigo: str
    nombre: str


class OpcionesHistorico(TypedDict):
    platos: list[Opcion]
    componentes: list[Opcion]
    porciones: list[Opcion]
    contexto_disponible: bool


class FilaHistorico(TypedDict):
    fila_id: str
    servicio_id: str
    fecha_servido: datetime | None
    plato_codigo: str
    plato_nombre: str
    componente_codigo: str
    componente_nombre: str
    porcion_codigo: str
    porcion_nombre: str
    origen: Literal['REAL', 'SIMULADO'] | None
    estado: Literal['APTO', 'EXCLUIDO']
    porcentaje_visual: Decimal | None
    motivo_exclusion: str | None


class Paginacion(TypedDict):
    pagina: int
    paginas: int
    total_filas: int
    por_pagina: int


class ResumenMuestra(TypedDict):
    candidatos: int
    aptos: int
    excluidos: int
    proporcion_excluidos: Decimal | None
    motivos: dict[str, int]


class Indicadores(TypedDict):
    n: int
    t: Decimal | None
    version_criterio: str | None
    prevalencia: Decimal | None
    intensidad: Decimal | None
    motivos_no_disponible: list[str]


class GrupoHistorico(TypedDict):
    clave: str
    plato_codigo: str
    componente_codigo: str
    porcion_codigo: str
    contexto_clave: str | None
    version_modelo: str
    version_configuracion: str
    protocolo_version: str
    comparable: bool
    motivos: list[str]
    indicadores: Indicadores


class ResumenHistorico(TypedDict):
    version_contrato: int
    solo_pruebas: bool
    filtros: FiltrosHistorico
    filas: list[FilaHistorico]
    paginacion: Paginacion
    resumen: ResumenMuestra
    indicadores: Indicadores
    grupos: list[GrupoHistorico]
    advertencias: list[str]


class Diferencias(TypedDict):
    prevalencia_pp: Decimal | None
    intensidad_pp: Decimal | None


class Comparacion(TypedDict):
    referencia: ResumenHistorico
    comparado: ResumenHistorico
    comparable: bool
    motivos: list[str]
    diferencias: Diferencias


class Percepcion(TypedDict):
    servicio_id: str
    categoria: Literal['INSUFICIENTE', 'ADECUADA', 'EXCESIVA', 'NO_INFORMADO']
    motivo: str
    version: int
    registrada_en: datetime | None
    operador_visible: str | None
