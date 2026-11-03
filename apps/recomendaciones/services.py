"""Frontera pública v1; no sustituir operaciones pendientes por fixtures."""
from .contracts import BackendRecomendacionesNoDisponible
from .filtros import normalizar_filtros, normalizar_periodo_evaluacion, normalizar_decision, normalizar_prueba


def opciones_recomendaciones(usuario):
    raise BackendRecomendacionesNoDisponible('El módulo de recomendaciones todavía no está conectado.')


def consultar_recomendaciones(filtros, usuario, pagina=1):
    raise BackendRecomendacionesNoDisponible('La consulta de recomendaciones todavía no está conectada.')


def evaluar_evidencia(filtros, version_criterios, usuario):
    raise BackendRecomendacionesNoDisponible('La evaluación todavía no está conectada.')


def obtener_evaluacion(evaluacion_id, usuario):
    raise BackendRecomendacionesNoDisponible('La evaluación todavía no está conectada.')


def generar_recomendacion(evaluacion_id, usuario):
    raise BackendRecomendacionesNoDisponible('La generación de recomendaciones todavía no está conectada.')


def obtener_recomendacion(recomendacion_id, usuario):
    raise BackendRecomendacionesNoDisponible('La recomendación todavía no está conectada.')


def decidir_recomendacion(recomendacion_id, decision, justificacion, usuario, version_esperada):
    raise BackendRecomendacionesNoDisponible('La decisión todavía no está conectada.')


def registrar_prueba(recomendacion_id, cambio, responsable_id, periodos, usuario):
    raise BackendRecomendacionesNoDisponible('El registro de pruebas todavía no está conectado.')


def obtener_prueba(prueba_id, usuario):
    raise BackendRecomendacionesNoDisponible('La prueba todavía no está conectada.')


def evaluar_prueba(prueba_id, usuario, version_esperada):
    raise BackendRecomendacionesNoDisponible('La evaluación de pruebas todavía no está conectada.')
