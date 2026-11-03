"""Presentación textual de snapshots; sin interpretar criterios."""
import json


def parametros_texto(caso):
    return json.dumps(caso['evaluacion']['criterios']['parametros'], ensure_ascii=False, indent=2, default=str) if caso else ''


CATEGORIAS_VISIBLES = {'MANTENER':'Mantener', 'REVISAR_PORCION':'Revisar porción', 'REVISAR_PREPARACION':'Revisar preparación', 'PRUEBA_CONTROLADA':'Prueba controlada'}
DECISIONES_VISIBLES = {'ACEPTADA':'Aceptada', 'DESCARTADA':'Descartada', 'EN_OBSERVACION':'En observación'}


def textos_caso(caso):
    recomendacion = caso['recomendacion'] if caso else None
    decision = caso['decision_actual'] if caso else None
    return dict(categoria_visible=CATEGORIAS_VISIBLES.get(recomendacion['categoria'], recomendacion['categoria']) if recomendacion else None,
                decision_visible=DECISIONES_VISIBLES.get(decision['decision'], decision['decision']) if decision else None,
                historial_visible=[{**x, 'decision_visible':DECISIONES_VISIBLES.get(x['decision'],x['decision'])} for x in caso['historial_decisiones']] if caso else [])


def filas_visibles(datos):
    if not datos:
        return []
    return [{**x, 'categoria_visible':CATEGORIAS_VISIBLES.get(x['categoria'],x['categoria']),
             'decision_visible':DECISIONES_VISIBLES.get(x['decision'],x['decision']),
             'suficiencia_visible':'Suficiente' if x['suficiencia']=='SUFICIENTE' else 'Evidencia insuficiente'} for x in datos['filas']]
