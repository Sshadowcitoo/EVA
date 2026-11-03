"""Estados sintéticos de interfaz, sin ORM ni modificación del catálogo."""
from copy import deepcopy
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from apps.historico.testing.fixtures import historico_fixture, comparacion_fixture, opciones_fixture
from ..contracts import CONTRACT_VERSION
from ..filtros import normalizar_filtros, normalizar_periodo_evaluacion

ZONA = ZoneInfo('America/Guayaquil')
EID = '10000000-0000-4000-8000-000000000001'
RID = '20000000-0000-4000-8000-000000000001'
DID = '30000000-0000-4000-8000-000000000001'
PID = '40000000-0000-4000-8000-000000000001'


def opciones_fixture_recomendaciones():
    return dict(historico=opciones_fixture(),
                versiones_criterios=[dict(version='fixture-v1', descripcion='Reglas ilustrativas, solo pruebas', aprobada=True)],
                responsables=[dict(id=1, nombre='responsable_fixture')])


def evaluacion_fixture(escenario='insuficiente'):
    if escenario not in ('insuficiente', 'configuracion_pendiente', 'sin_datos', 'suficiente', 'obsoleta', 'simulada'):
        raise ValueError('Escenario desconocido.')
    base = historico_fixture('sin_datos' if escenario == 'sin_datos' else 'con_datos')
    base['filtros'] = normalizar_periodo_evaluacion(dict(plato='seco_de_pollo', componente='arroz',
        porcion='estandar', desde='2026-10-01', hasta='2026-10-14'))
    suficiente = escenario in ('suficiente', 'obsoleta')
    configurado = escenario != 'configuracion_pendiente'
    chequeos = [dict(codigo=c, etiqueta=e, cumple=suficiente, valor_texto=v, exigido_texto=x,
                     motivo=None if suficiente else 'Criterio no demostrado en este escenario de prueba.')
                for c, e, v, x in [('MUESTRA','Muestra mínima','4','3'),
                    ('PERSISTENCIA','Persistencia en periodos','2','2'), ('CALIDAD','Calidad','Revisada','Aprobada'),
                    ('CONFIANZA','Confianza histórica','Registrada','Aprobada'),
                    ('COMPARABILIDAD','Comparabilidad','Contexto de fixture','Contexto conocido')]]
    criterios = dict(version='fixture-v1' if configurado else None, aprobada=configurado,
        descripcion='Configuración ilustrativa; no aprobada para operación real.',
        parametros=dict(muestra_minima=3, periodos_minimos=2, periodo_dias=7, presencia_t=20,
                        cobertura_minima=80) if configurado else {})
    referencias = [dict(servicio_id=f['servicio_id'], intento_id=f'50000000-0000-4000-8000-{i:012d}',
                       revision_id=f'60000000-0000-4000-8000-{i:012d}', version_revision=1)
                  for i, f in enumerate(base['filas'], 1) if f['estado'] == 'APTO']
    motivos = [] if suficiente else ['Evidencia insuficiente: faltan condiciones verificadas.']
    if escenario == 'configuracion_pendiente':
        motivos = ['Falta una versión de criterios aprobada.']
        base['indicadores'].update(t=None, version_criterio=None, prevalencia=None,
                                   motivos_no_disponible=['SIN_CRITERIO_PRESENCIA'])
    if escenario == 'sin_datos':
        motivos = ['No hay observaciones aptas para evaluar.']
    if escenario == 'simulada':
        motivos = ['Los datos simulados no sustentan recomendaciones reales.']
    return deepcopy(dict(id=EID, solo_pruebas=True, origen='SIMULADO' if escenario == 'simulada' else 'REAL',
        suficiencia='SUFICIENTE' if suficiente else 'INSUFICIENTE', filtros=base['filtros'], criterios=criterios,
        resumen=base['resumen'], indicadores=base['indicadores'], grupos=base['grupos'], chequeos=chequeos,
        motivos=motivos, referencias=referencias, evaluada_en=datetime(2026,10,15,12,tzinfo=ZONA),
        vigente=escenario != 'obsoleta', motivos_vigencia=['Una revisión de origen cambió.'] if escenario == 'obsoleta' else []))


def detalle_fixture(escenario='sin_decision', administracion=True):
    opciones = ('insuficiente','configuracion_pendiente','sin_datos','sin_propuesta','sin_decision',
                'aceptada','descartada','en_observacion','obsoleta','simulada')
    if escenario not in opciones:
        raise ValueError('Escenario desconocido.')
    evaluacion = evaluacion_fixture(escenario if escenario in ('insuficiente','configuracion_pendiente','sin_datos','obsoleta','simulada') else 'suficiente')
    rec = None
    if evaluacion['suficiencia'] == 'SUFICIENTE' and escenario != 'sin_propuesta':
        rec = dict(id=RID, evaluacion_id=EID, categoria='REVISAR_PORCION',
            explicacion='Revisar la porción con una prueba supervisada; el sobrante no demuestra una causa.',
            creada_en=datetime(2026,10,15,12,5,tzinfo=ZONA))
    decision = None
    estados = {'aceptada':'ACEPTADA', 'descartada':'DESCARTADA', 'en_observacion':'EN_OBSERVACION'}
    if escenario in estados:
        decision = dict(id=DID, decision=estados[escenario], justificacion='Justificación humana de prueba.',
                        autor_visible='administracion_fixture', fecha=datetime(2026,10,16,12,tzinfo=ZONA),
                        version=1, sustituye_id=None)
    valido = evaluacion['vigente'] and evaluacion['origen'] == 'REAL' and evaluacion['suficiencia'] == 'SUFICIENTE'
    return dict(evaluacion=evaluacion, recomendacion=rec, decision_actual=decision,
                historial_decisiones=[deepcopy(decision)] if decision else [], version_esperada=decision['version'] if decision else 0,
                capacidades=dict(puede_evaluar=administracion, puede_generar=administracion and valido and rec is None,
                    puede_decidir=administracion and valido and rec is not None,
                    puede_registrar_prueba=administracion and valido and decision is not None and decision['decision']=='ACEPTADA',
                    puede_ver_analisis=not administracion), pruebas=[])


def lista_fixture(vacia=False):
    fila = dict(evaluacion_id=EID, recomendacion_id=None, plato_nombre='Seco de pollo', componente_nombre='Arroz',
                porcion_nombre='Estándar', suficiencia='INSUFICIENTE', categoria=None, decision=None,
                vigente=True, n=4, evaluada_en=datetime(2026,10,15,12,tzinfo=ZONA))
    return dict(version_contrato=CONTRACT_VERSION, solo_pruebas=True, filtros=normalizar_filtros({}),
                filas=[] if vacia else [fila], paginacion=dict(pagina=1,paginas=1,total_filas=0 if vacia else 1,por_pagina=30),
                resumen=dict(total=0 if vacia else 1, insuficientes=0 if vacia else 1,
                             sin_decision=0, en_observacion=0, obsoletas=0))


def prueba_fixture(estado='NO_EVALUABLE', administracion=True):
    if estado not in ('REGISTRADA','EVALUADA','NO_EVALUABLE'):
        raise ValueError('Estado desconocido.')
    caso = detalle_fixture('aceptada', administracion)
    comparacion = None if estado == 'REGISTRADA' else comparacion_fixture(estado == 'EVALUADA')
    if comparacion:
        for bloque in ('referencia','comparado'):
            dto = comparacion[bloque]
            for campo in ('desde','hasta','inicio','fin'):
                dto['filtros'][campo] += timedelta(days=16)
            for fila in dto['filas']:
                fila['fecha_servido'] += timedelta(days=16)
    prueba = dict(id=PID, recomendacion_id=RID, aceptacion_id=DID, estado=estado,
        cambio='Ensayo supervisado de porción, sin cambios automáticos del catálogo.',
        responsable_id=1, responsable_nombre='responsable_fixture',
        periodos=dict(referencia_desde=date(2026,10,17), referencia_hasta=date(2026,10,23),
                      intervencion_desde=date(2026,10,24), intervencion_hasta=date(2026,10,30)),
        registrada_en=datetime(2026,10,16,13,tzinfo=ZONA), registrada_por='administracion_fixture',
        evaluada_en=None if estado == 'REGISTRADA' else datetime(2026,10,31,13,tzinfo=ZONA),
        version=1 if estado == 'REGISTRADA' else 2, comparacion=comparacion,
        motivos=['No se ha demostrado comparabilidad.'] if estado == 'NO_EVALUABLE' else [],
        puede_evaluar=administracion)
    caso['pruebas'] = [{k:prueba[k] for k in ('id','estado','cambio','responsable_nombre','registrada_en','version')}]
    return dict(caso=caso, prueba=prueba)
