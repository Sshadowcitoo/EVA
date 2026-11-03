"""Evidencia completa del histórico; nunca derivada de filas paginadas."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from django.conf import settings
from apps.historico import selectors as historico, indicadores
from apps.historico.configuration import criterio_presencia
from .serialization import huella, guardar


def criterios_actuales():
    config = getattr(settings, 'EVA_RECOMENDACIONES_CRITERIOS', {})
    if not isinstance(config, dict):
        config = {}
    version = config.get('version')
    version = version.strip() if isinstance(version, str) else None
    parametros = deepcopy(config.get('reglas', {}))
    aprobada = config.get('aprobada') is True
    try:
        guardar(parametros)
    except (ValueError, TypeError):
        parametros, aprobada = {}, False
    return dict(version=version or None, aprobada=aprobada,
                descripcion=str(config.get('descripcion', 'Configuración pendiente.')),
                parametros=parametros)


def seleccionar(filtros):
    datos, advertencias = historico.seleccionar(filtros)
    resumen = indicadores.resumir(datos, advertencias, filtros, 1)
    referencias, fuentes = [], []
    for dato in datos:
        intento, analisis, servicio = dato['intento'], dato['analisis'], dato['servicio']
        revision = intento._revisiones[0] if intento and intento._revisiones else None
        if dato['motivo'] is None:
            referencias.append(dict(servicio_id=str(servicio.pk), intento_id=str(intento.pk),
                                    revision_id=str(revision.pk), version_revision=revision.version))
        fuentes.append(dict(servicio=str(servicio.pk), estado=servicio.estado_captura, fecha=dato['fecha'],
            analisis=str(analisis.pk) if analisis else None, motivo=dato['motivo'],
            intento=str(intento.pk) if intento else None,
            revision=[str(revision.pk), revision.version, revision.decision] if revision else None,
            resultados=sorted([dict(id=str(r.pk), porcentaje=r.porcentaje, confianza=r.confianza,
                umbral=r.umbral_aplicado, criterio=r.criterio, aprobado=r.configuracion_aprobada,
                estado=r.estado, motivo=r.motivo) for r in dato['resultados']], key=lambda r:r['id'])))
    firma = huella(dict(filtros=filtros, fuentes=sorted(fuentes, key=lambda f:f['servicio']),
                        grupos=resumen['grupos'], resumen=resumen['resumen'],
                        presencia=criterio_presencia(), criterios=criterios_actuales()))
    return datos, resumen, referencias, firma


def numero(reglas, campo, minimo=0, maximo=None, entero=False):
    valor = reglas.get(campo)
    if isinstance(valor, bool) or (entero and type(valor) is not int):
        return None
    try:
        valor = Decimal(str(valor))
        if not valor.is_finite() or valor < minimo or (maximo is not None and valor > maximo):
            return None
        return int(valor) if entero else valor
    except (InvalidOperation, ValueError, TypeError):
        return None


def evaluar(datos, resumen, filtros, criterios):
    reglas = criterios['parametros']
    if not isinstance(reglas, dict):
        reglas = {}
    aprobada = bool(criterios['version']) and criterios['aprobada']
    chequeos = []

    def check(codigo, etiqueta, cumple, valor=None, exigido=None, motivo=None):
        chequeos.append(dict(codigo=codigo, etiqueta=etiqueta, cumple=bool(cumple),
            valor_texto=str(valor) if valor is not None else None,
            exigido_texto=str(exigido) if exigido is not None else None,
            motivo=None if cumple else motivo or f'{etiqueta}: criterio ausente o no demostrado.'))

    check('CONFIGURACION', 'Criterios aprobados', aprobada, criterios['version'], 'Versión aprobada')
    aptos = [d for d in datos if d['motivo'] is None]
    n_min = numero(reglas, 'muestra_minima', 1, entero=True)
    check('MUESTRA', 'Muestra mínima', n_min is not None and len(aptos) >= n_min, len(aptos), n_min)
    dias = numero(reglas, 'periodo_dias', 1, entero=True)
    periodos_min = numero(reglas, 'periodos_minimos', 1, entero=True)
    # Persistencia exige muestra mínima en cada bloque temporal completo.
    bloques = {}
    for d in aptos:
        bloque = (d['fecha'].astimezone(filtros['inicio'].tzinfo).date() - filtros['desde']).days // dias if dias else None
        if bloque is not None:
            bloques[bloque] = bloques.get(bloque, 0) + 1
    duracion = (filtros['hasta'] - filtros['desde']).days + 1
    completos = sum(n >= n_min for b, n in bloques.items()
                    if n_min is not None and (b + 1) * dias <= duracion) if dias else 0
    check('PERSISTENCIA', 'Persistencia en periodos completos',
          periodos_min is not None and completos >= periodos_min, completos, periodos_min)
    candidatos = resumen['resumen']['candidatos']
    cobertura = Decimal(100) * len(aptos) / candidatos if candidatos else None
    cobertura_min = numero(reglas, 'cobertura_minima', 0, 100)
    check('CALIDAD', 'Cobertura de evidencia validada', reglas.get('calidad') == 'REVISION_CONFIRMADA'
          and cobertura is not None and cobertura_min is not None and cobertura >= cobertura_min, cobertura, cobertura_min)
    confianza_min = numero(reglas, 'confianza', 0, 1)
    confianzas = [Decimal(str(r.confianza)) for d in aptos for r in d['resultados']]
    check('CONFIANZA', 'Confianza histórica mínima', confianza_min is not None and bool(confianzas)
          and min(confianzas) >= confianza_min, min(confianzas) if confianzas else None, confianza_min)
    grupos = resumen['grupos']
    check('COMPARABILIDAD', 'Grupo y contexto comparables', reglas.get('comparabilidad') == 'CONTEXTO_Y_GRUPO'
          and len(grupos) == 1 and grupos[0]['comparable'] and grupos[0]['contexto_clave'] is not None,
          len(grupos), 'Un grupo con contexto histórico conocido')
    t = numero(reglas, 'presencia_t', 0, 100)
    check('PRESENCIA', 'Criterio de presencia coherente', t is not None and resumen['indicadores']['t'] == t
          and resumen['indicadores']['version_criterio'] is not None, resumen['indicadores']['t'], t)
    categoria = elegir_categoria(reglas, resumen['indicadores'])
    check('REGLAS', 'Regla de recomendación aplicable', categoria is not None,
          categoria, 'Reglas ordenadas y versionadas')
    return chequeos, categoria


def elegir_categoria(reglas, metricas):
    """Primera regla ordenada que satisface ambos intervalos inclusivos."""
    from .contracts import CATEGORIAS
    categorias = {c for c, _ in CATEGORIAS}
    opciones = reglas.get('categorias')
    if not isinstance(opciones, list) or not opciones:
        return None
    seleccion = None
    for regla in opciones:
        if not isinstance(regla, dict) or regla.get('categoria') not in categorias:
            return None
        limites = [numero(regla, clave, 0, 100) for clave in
                   ('intensidad_desde', 'intensidad_hasta', 'prevalencia_desde', 'prevalencia_hasta')]
        if any(v is None for v in limites) or limites[0] > limites[1] or limites[2] > limites[3]:
            return None
        intensidad, prevalencia = metricas['intensidad'], metricas['prevalencia']
        if (seleccion is None and intensidad is not None and prevalencia is not None
                and limites[0] <= intensidad <= limites[1] and limites[2] <= prevalencia <= limites[3]):
            seleccion = regla['categoria']
    return seleccion
