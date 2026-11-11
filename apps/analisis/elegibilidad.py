"""Regla compartida: la revisión no convierte simulaciones o incertidumbre en evidencia."""


def evaluar_elegibilidad(*, origen, estado_intento, estados_componentes,
                        configuracion_aprobada, evidencia_disponible,
                        decision=None, intento_id=None, intento_revisado_id=None, origen_esperado="REAL"):
    estados = list(estados_componentes)
    motivos = []
    if origen != origen_esperado:
        motivos.append("ORIGEN_NO_REAL")
    if estado_intento != "COMPLETADO":
        motivos.append("INTENTO_NO_COMPLETADO")
    if configuracion_aprobada is not True:
        motivos.append("SIN_CONFIGURACION_APROBADA")
    if not estados or any(estado != "CONCLUYENTE" for estado in estados):
        motivos.append("COMPONENTES_NO_CONCLUYENTES")
    tecnico_valido = not motivos
    misma_version = intento_id is not None and intento_revisado_id is not None and intento_id == intento_revisado_id
    return {
        "puede_confirmar": tecnico_valido and evidencia_disponible is True,
        # Una revisión previamente válida no se borra al vencer los bytes.
        "apto_historico": tecnico_valido and decision == "CONFIRMADO" and misma_version,
        "motivos": motivos + ([] if evidencia_disponible is True else ["EVIDENCIA_NO_DISPONIBLE"]),
    }
