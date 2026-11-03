"""Métricas descriptivas frente a máscaras manuales; no aprueban el modelo."""
from decimal import Decimal
from PIL import Image, ImageChops


def _validar(mascara):
    if not isinstance(mascara, Image.Image) or mascara.mode != 'L' or sum(mascara.histogram()[1:255]):
        raise ValueError('Se necesitan máscaras L binarias con valores 0 y 255.')


def metricas_mascara(referencia, prediccion):
    _validar(referencia);_validar(prediccion)
    if referencia.size != prediccion.size:
        raise ValueError('Las máscaras deben tener la misma geometría.')
    area_ref, area_pred = referencia.histogram()[255], prediccion.histogram()[255]
    interseccion = ImageChops.darker(referencia, prediccion).histogram()[255]
    union = ImageChops.lighter(referencia, prediccion).histogram()[255]
    return dict(iou=Decimal(interseccion)/union if union else None,
        dice=Decimal(2*interseccion)/(area_ref+area_pred) if area_ref+area_pred else None,
        ambas_vacias=not union, area_manual=area_ref, area_modelo=area_pred)


def evaluar_par(manual_servido, manual_retorno, modelo_servido=None, modelo_retorno=None, *, geometria_verificada=False):
    for imagen in (manual_servido, manual_retorno):_validar(imagen)
    resultado = dict(porcentaje_manual=None, porcentaje_modelo=None, error_absoluto_pp=None,
                     servido=None, retorno=None, estado='NO_CONCLUYENTE', motivos=[])
    geometria = geometria_verificada is True and manual_servido.size == manual_retorno.size
    if not geometria:
        resultado['motivos'].append('GEOMETRIA_NO_VERIFICADA')
    area_inicial=manual_servido.histogram()[255]
    if area_inicial and geometria:
        resultado['porcentaje_manual']=Decimal(100)*manual_retorno.histogram()[255]/area_inicial
        if resultado['porcentaje_manual'] > 100:
            resultado['motivos'].append('REFERENCIA_MAYOR_100')
    elif not area_inicial:
        resultado['motivos'].append('SIN_AREA_MANUAL_INICIAL')
    for etapa, manual, modelo in [('servido',manual_servido,modelo_servido),('retorno',manual_retorno,modelo_retorno)]:
        if modelo is not None:resultado[etapa]=metricas_mascara(manual,modelo)
        else:resultado['motivos'].append('SIN_DETECCION_'+etapa.upper())
    if modelo_servido is not None and modelo_retorno is not None and geometria:
        inicial=modelo_servido.histogram()[255]
        if inicial:
            resultado['porcentaje_modelo']=Decimal(100)*modelo_retorno.histogram()[255]/inicial
        else:
            resultado['motivos'].append('SIN_AREA_MODELO_INICIAL')
    if resultado['porcentaje_manual'] is not None and resultado['porcentaje_modelo'] is not None:
        if resultado['porcentaje_manual'] <= 100:
            resultado['error_absoluto_pp']=abs(resultado['porcentaje_modelo']-resultado['porcentaje_manual'])
        if resultado['porcentaje_modelo'] > 100:resultado['motivos'].append('MAYOR_100')
        if not resultado['motivos']:resultado['estado']='EVALUABLE'
    return resultado
