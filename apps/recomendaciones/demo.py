"""Ejemplos didácticos sin escrituras ni aprobaciones sobre evidencia operativa."""
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from django.conf import settings
from apps.analisis.services import evaluar_componente
from apps.historico.indicadores import calcular
from .contracts import CATEGORIAS
from .selectors import evaluar


ESCENARIOS = {
    'mantener': ('Poco sobrante', (0, 0, 5, 5, 10) * 2),
    'porcion': ('Sobrante frecuente', (20, 25, 30, 35, 40) * 2),
    'prueba': ('Resultado intermedio', (0, 10, 10, 10, 30) * 2),
    'insuficiente': ('Muestra insuficiente', (30, 40)),
}


def preparar(escenario):
    if escenario not in ESCENARIOS:
        raise ValueError('Escenario no disponible.')
    titulo, valores = ESCENARIOS[escenario]
    perfil = json.loads((Path(settings.BASE_DIR) / 'ops/analisis/criterios_piloto.propuesta.json').read_text(encoding='utf-8'))
    reglas = perfil['recomendaciones']['reglas']
    # Solo este DTO efímero supone condiciones cumplidas. No modifica settings,
    # configuraciones persistidas, revisiones, servicios ni aprobaciones reales.
    criterios = dict(version='demo-didactica-v1', aprobada=True, parametros=reglas)
    filas, datos = [], []
    for i, valor in enumerate(valores):
        calculo = evaluar_componente(area_inicial=10000, area_residual=valor * 100,
            confianza=.9, umbral_confianza=.8, comparable=True, oculto=False)
        dia = i // 5 + 1
        filas.append(dict(numero=i + 1, dia=dia, lote=f'Ejemplo-{dia}',
            inicial=10000, residual=valor * 100, porcentaje=calculo['porcentaje']))
        datos.append(dict(motivo=None, contexto_clave='contexto-didactico',
            servicio=SimpleNamespace(contexto_snapshot={'lote_preparacion':f'Ejemplo-{dia}'}),
            fecha=datetime(2026, 11, dia, 12, tzinfo=ZoneInfo('America/Guayaquil')),
            resultados=[SimpleNamespace(confianza=Decimal('.9'))]))
    indicadores = calcular([f['porcentaje'] for f in filas],
        dict(t=Decimal(str(reglas['presencia_t'])), version_criterio='demo-didactica-v1'))
    resumen = dict(resumen={'candidatos':len(filas)}, indicadores=indicadores,
        grupos=[dict(comparable=True, contexto_clave='contexto-didactico')])
    chequeos, categoria = evaluar(datos, resumen,
        dict(inicio=datetime(2026, 11, 1, tzinfo=ZoneInfo('America/Guayaquil')),
             desde=date(2026, 11, 1), hasta=date(2026, 11, 2)), criterios)
    suficiente = all(c['cumple'] for c in chequeos)
    return dict(escenario=escenario, titulo=titulo, filas=filas, indicadores=indicadores,
        chequeos=chequeos, suficiente=suficiente,
        categoria=categoria if suficiente else None,
        recomendacion=dict(CATEGORIAS).get(categoria) if suficiente else 'Evidencia insuficiente',
        opciones=[dict(codigo=k, titulo=v[0]) for k, v in ESCENARIOS.items()])
