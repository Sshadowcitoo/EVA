"""DTO sintéticos sin ORM, fotos, usuarios reales ni acceso a almacenamiento.

Importar únicamente en pruebas. Cada llamada produce un objeto independiente.
Los umbrales del ejemplo no son parámetros aprobados para el piloto.
"""
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from ..contracts import CONTRACT_VERSION, ZONA_HORARIA
from ..filtros import normalizar_filtros

ESCENARIOS = ('con_datos', 'sin_datos', 'sin_aptos', 'configuracion_pendiente')


def opciones_fixture():
    return dict(platos=[dict(codigo='seco_de_pollo', nombre='Seco de pollo')],
                componentes=[dict(codigo='arroz', nombre='Arroz')],
                porciones=[dict(codigo='estandar', nombre='Estándar')], contexto_disponible=False)


def historico_fixture(escenario='con_datos'):
    if escenario not in ESCENARIOS:
        raise ValueError('Escenario de prueba desconocido.')
    filtros = normalizar_filtros(dict(plato='seco_de_pollo', componente='arroz', porcion='estandar',
                                     desde='2026-10-01', hasta='2026-10-07'))
    filas = []
    for i, porcentaje in enumerate((0, 10, 30, 60, None), 1):
        servicio = f'00000000-0000-4000-8000-{i:012d}'
        filas.append(dict(fila_id=servicio + '/arroz', servicio_id=servicio,
                          fecha_servido=datetime(2026, 10, i, 12, tzinfo=ZoneInfo(ZONA_HORARIA)),
                          plato_codigo='seco_de_pollo', plato_nombre='Seco de pollo',
                          componente_codigo='arroz', componente_nombre='Arroz',
                          porcion_codigo='estandar', porcion_nombre='Estándar', origen='REAL',
                          estado='APTO' if porcentaje is not None else 'EXCLUIDO',
                          porcentaje_visual=Decimal(porcentaje) if porcentaje is not None else None,
                          motivo_exclusion=None if porcentaje is not None else 'RECHAZADO'))
    indicadores = dict(n=4, t=Decimal(20), version_criterio='fixture-t20', prevalencia=Decimal(50),
                       intensidad=Decimal(25), motivos_no_disponible=[])
    resumen = dict(candidatos=5, aptos=4, excluidos=1, proporcion_excluidos=Decimal(20), motivos={'RECHAZADO': 1})
    grupo = dict(clave='fixture/grupo-arroz', plato_codigo='seco_de_pollo', componente_codigo='arroz',
                 porcion_codigo='estandar', contexto_clave='fixture/contexto',
                 version_modelo='fixture-modelo', version_configuracion='fixture-criterios',
                 protocolo_version='captura-v1', comparable=True, motivos=[], indicadores=deepcopy(indicadores))
    datos = dict(version_contrato=CONTRACT_VERSION, solo_pruebas=True, filtros=filtros, filas=filas,
                 paginacion=dict(pagina=1, paginas=1, total_filas=5, por_pagina=30),
                 resumen=resumen, indicadores=indicadores, grupos=[grupo],
                 advertencias=['Datos sintéticos de prueba; no acreditan precisión ni parámetros aprobados.'])
    if escenario == 'sin_datos':
        datos.update(filas=[], grupos=[], paginacion=dict(pagina=1, paginas=1, total_filas=0, por_pagina=30),
                     resumen=dict(candidatos=0, aptos=0, excluidos=0, proporcion_excluidos=None, motivos={}),
                     indicadores=dict(n=0, t=Decimal(20), version_criterio='fixture-t20',
                                      prevalencia=None, intensidad=None, motivos_no_disponible=['SIN_DATOS']))
    elif escenario == 'sin_aptos':
        for fila in filas:
            fila.update(estado='EXCLUIDO', porcentaje_visual=None, motivo_exclusion='NO_CONCLUYENTE')
        resumen.update(aptos=0, excluidos=5, proporcion_excluidos=Decimal(100), motivos={'NO_CONCLUYENTE': 5})
        indicadores.update(n=0, prevalencia=None, intensidad=None, motivos_no_disponible=['SIN_REGISTROS_APTOS'])
        grupo['indicadores'] = deepcopy(indicadores)
    elif escenario == 'configuracion_pendiente':
        indicadores.update(t=None, version_criterio=None, prevalencia=None,
                           motivos_no_disponible=['SIN_CRITERIO_PRESENCIA'])
        grupo['indicadores'] = deepcopy(indicadores)
    return deepcopy(datos)


def comparacion_fixture(comparable=True):
    referencia = historico_fixture()
    comparado = historico_fixture()
    comparado['filtros'] = normalizar_filtros(dict(plato='seco_de_pollo', componente='arroz', porcion='estandar',
                                                 desde='2026-10-08', hasta='2026-10-14'))
    for fila in comparado['filas']:
        fila['servicio_id'] = fila['servicio_id'].replace('8000-', '9000-')
        fila['fila_id'] = fila['servicio_id'] + '/arroz'
        fila['fecha_servido'] = fila['fecha_servido'].replace(day=fila['fecha_servido'].day + 7)
    # Misma muestra ilustrativa: diferencias reales de esta fixture = cero, no mejora.
    if not comparable:
        comparado['grupos'][0].update(comparable=False, contexto_clave=None, motivos=['SIN_CONTEXTO_HISTORICO'])
    return dict(referencia=referencia, comparado=comparado, comparable=comparable,
                motivos=[] if comparable else ['SIN_CONTEXTO_HISTORICO'],
                diferencias=dict(prevalencia_pp=Decimal(0) if comparable else None,
                                 intensidad_pp=Decimal(0) if comparable else None))


def percepcion_fixture(registrada=False):
    return dict(servicio_id='00000000-0000-4000-8000-000000000001',
                categoria='ADECUADA' if registrada else 'NO_INFORMADO',
                motivo='Respuesta declarada de prueba' if registrada else '',
                version=1 if registrada else 0,
                registrada_en=datetime(2026, 10, 1, 13, tzinfo=ZoneInfo(ZONA_HORARIA)) if registrada else None,
                operador_visible='operador_fixture' if registrada else None)
