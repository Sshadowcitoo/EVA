"""Normalizadores compartidos; no certifican suficiencia ni permisos."""
from apps.historico.filtros import normalizar_filtros as filtros_historico
from apps.historico.contracts import FiltrosInvalidos
from .contracts import CATEGORIAS, DECISIONES, SUFICIENCIA, MAX_TEXTO, ParametrosInvalidos


def _historico(datos):
    try:
        return filtros_historico(datos)
    except FiltrosInvalidos as exc:
        raise ParametrosInvalidos(exc.errores) from None


def normalizar_filtros(datos):
    salida = dict(historico=_historico(datos))
    errores = {}
    for campo, opciones in [('categoria', CATEGORIAS), ('decision', DECISIONES), ('suficiencia', SUFICIENCIA)]:
        valor = datos.get(campo)
        if valor is None or valor == '':
            salida[campo] = None
        elif valor in [v for v, _ in opciones]:
            salida[campo] = valor
        else:
            errores[campo] = 'Selecciona una opción válida.'
    if errores:
        raise ParametrosInvalidos(errores)
    return salida


def normalizar_periodo_evaluacion(datos):
    filtros = _historico(datos)
    if filtros['inicio'] is None or filtros['fin'] is None:
        raise ParametrosInvalidos({'__all__': 'Define inicio y fin del periodo de evaluación.'})
    return filtros


def _entero(valor, campo, minimo=0):
    if isinstance(valor, str) and valor.isascii() and valor.isdigit() and len(valor) <= 10:
        valor = int(valor)
    if type(valor) is not int or not minimo <= valor < 2**31:
        raise ParametrosInvalidos({campo: 'Introduce un entero válido.'})
    return valor


def _texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip() or len(valor) > MAX_TEXTO:
        raise ParametrosInvalidos({campo: 'Escribe un texto de 1 a 1000 caracteres.'})
    return valor.strip()


def normalizar_decision(datos):
    if datos.get('decision') not in [c for c, _ in DECISIONES]:
        raise ParametrosInvalidos({'decision': 'Selecciona una decisión válida.'})
    return dict(decision=datos['decision'], justificacion=_texto(datos.get('justificacion'), 'justificacion'),
                version_esperada=_entero(datos.get('version_esperada'), 'version_esperada'))


def normalizar_prueba(datos):
    filtros = []
    errores = {}
    for prefijo in ('referencia', 'intervencion'):
        try:
            filtros.append(normalizar_periodo_evaluacion(dict(desde=datos.get(prefijo + '_desde'), hasta=datos.get(prefijo + '_hasta'))))
        except ParametrosInvalidos as exc:
            errores.update({prefijo + '_' + k if k in ('desde', 'hasta') else '__all__': v for k, v in exc.errores.items()})
    if errores:
        raise ParametrosInvalidos(errores)
    referencia, intervencion = filtros
    if referencia['fin'] > intervencion['inicio']:
        raise ParametrosInvalidos({'intervencion_desde': 'La intervención debe ser posterior al periodo de referencia.'})
    return dict(cambio=_texto(datos.get('cambio'), 'cambio'),
                responsable_id=_entero(datos.get('responsable_id'), 'responsable_id', 1),
                periodos=dict(referencia_desde=referencia['desde'], referencia_hasta=referencia['hasta'],
                              intervencion_desde=intervencion['desde'], intervencion_hasta=intervencion['hasta']))
