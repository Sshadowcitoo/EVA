"""Contrato v1: DTO de diccionarios, sin ORM ni URLs de almacenamiento."""
from datetime import date, datetime
from typing import Literal, TypedDict
from apps.historico.contracts import FiltrosHistorico, OpcionesHistorico, Paginacion, ResumenMuestra, Indicadores, GrupoHistorico, Comparacion

CONTRACT_VERSION = 1
MAX_TEXTO = 1000
CATEGORIAS = (('MANTENER', 'Mantener'), ('REVISAR_PORCION', 'Revisar porción'),
              ('REVISAR_PREPARACION', 'Revisar preparación'), ('PRUEBA_CONTROLADA', 'Realizar prueba controlada'))
DECISIONES = (('ACEPTADA', 'Aceptar'), ('DESCARTADA', 'Descartar'), ('EN_OBSERVACION', 'Mantener en observación'))
SUFICIENCIA = (('SUFICIENTE', 'Suficiente'), ('INSUFICIENTE', 'Evidencia insuficiente'))


class ErrorRecomendaciones(Exception):
    codigo = 'ERROR_RECOMENDACIONES'


class ParametrosInvalidos(ErrorRecomendaciones):
    codigo = 'PARAMETROS_INVALIDOS'

    def __init__(self, errores: dict[str, str]):
        self.errores = errores
        super().__init__('Revisa los campos indicados.')


class BackendRecomendacionesNoDisponible(ErrorRecomendaciones):
    codigo = 'BACKEND_PENDIENTE'


class CasoNoDisponible(ErrorRecomendaciones):
    codigo = 'CASO_NO_DISPONIBLE'


class ConflictoRecomendacion(ErrorRecomendaciones):
    codigo = 'CONFLICTO_RECOMENDACION'


class EvidenciaDesactualizada(ConflictoRecomendacion):
    codigo = 'EVIDENCIA_DESACTUALIZADA'


class FiltrosRecomendaciones(TypedDict):
    historico: FiltrosHistorico
    categoria: str | None
    decision: str | None
    suficiencia: str | None


class VersionCriterios(TypedDict):
    version: str
    descripcion: str
    aprobada: bool


class Responsable(TypedDict):
    id: int
    nombre: str


class OpcionesRecomendaciones(TypedDict):
    historico: OpcionesHistorico
    versiones_criterios: list[VersionCriterios]
    responsables: list[Responsable]


class CriteriosEvaluados(TypedDict):
    version: str | None
    aprobada: bool
    descripcion: str
    parametros: dict  # Snapshot de valores JSON; la interfaz solo los presenta.


class Chequeo(TypedDict):
    codigo: str
    etiqueta: str
    cumple: bool
    valor_texto: str | None
    exigido_texto: str | None
    motivo: str | None


class ReferenciaResultado(TypedDict):
    servicio_id: str
    intento_id: str
    revision_id: str
    version_revision: int


class EvaluacionEvidencia(TypedDict):
    id: str
    solo_pruebas: bool
    origen: Literal['REAL', 'SIMULADO']
    suficiencia: Literal['SUFICIENTE', 'INSUFICIENTE']
    filtros: FiltrosHistorico
    criterios: CriteriosEvaluados
    resumen: ResumenMuestra
    indicadores: Indicadores
    grupos: list[GrupoHistorico]
    chequeos: list[Chequeo]
    motivos: list[str]
    referencias: list[ReferenciaResultado]
    evaluada_en: datetime
    vigente: bool
    motivos_vigencia: list[str]


class DecisionRecomendacion(TypedDict):
    id: str
    decision: Literal['ACEPTADA', 'DESCARTADA', 'EN_OBSERVACION']
    justificacion: str
    autor_visible: str
    fecha: datetime
    version: int
    sustituye_id: str | None


class Recomendacion(TypedDict):
    id: str
    evaluacion_id: str
    categoria: Literal['MANTENER', 'REVISAR_PORCION', 'REVISAR_PREPARACION', 'PRUEBA_CONTROLADA']
    explicacion: str
    creada_en: datetime


class Capacidades(TypedDict):
    puede_evaluar: bool
    puede_generar: bool
    puede_decidir: bool
    puede_registrar_prueba: bool
    puede_ver_analisis: bool


class ResumenPrueba(TypedDict):
    id: str
    estado: Literal['REGISTRADA', 'EVALUADA', 'NO_EVALUABLE']
    cambio: str
    responsable_nombre: str
    registrada_en: datetime
    version: int


class DetalleCaso(TypedDict):
    evaluacion: EvaluacionEvidencia
    recomendacion: Recomendacion | None
    decision_actual: DecisionRecomendacion | None
    historial_decisiones: list[DecisionRecomendacion]
    version_esperada: int
    capacidades: Capacidades
    pruebas: list[ResumenPrueba]


class FilaRecomendaciones(TypedDict):
    evaluacion_id: str
    recomendacion_id: str | None
    plato_nombre: str
    componente_nombre: str
    porcion_nombre: str
    suficiencia: str
    categoria: str | None
    decision: str | None
    vigente: bool
    n: int
    evaluada_en: datetime


class ListaRecomendaciones(TypedDict):
    version_contrato: int
    solo_pruebas: bool
    filtros: FiltrosRecomendaciones
    filas: list[FilaRecomendaciones]
    paginacion: Paginacion
    resumen: dict[str, int]  # total, insuficientes, sin_decision, en_observacion, obsoletas.


class PeriodosPrueba(TypedDict):
    referencia_desde: date
    referencia_hasta: date
    intervencion_desde: date
    intervencion_hasta: date


class PruebaControlada(ResumenPrueba):
    recomendacion_id: str
    aceptacion_id: str
    responsable_id: int
    periodos: PeriodosPrueba
    registrada_por: str
    evaluada_en: datetime | None
    comparacion: Comparacion | None
    motivos: list[str]
    puede_evaluar: bool


class DetallePrueba(TypedDict):
    caso: DetalleCaso
    prueba: PruebaControlada
