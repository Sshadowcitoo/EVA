"""Previsualiza un inventario sintético sin conectar con Django ni con una base."""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

PLATOS = {
    'encebollado': ('yuca', 'pescado'),
    'seco_de_pollo': ('arroz', 'pollo'),
    'arroz_menestra_carne': ('arroz', 'menestra', 'carne', 'ensalada'),
}
PORCIONES = ('estandar', 'reducida')
PERFILES = {
    'encebollado': (0, 2, 4, 5, 8),
    'seco_de_pollo': (18, 24, 30, 38, 48),
    'arroz_menestra_carne': (0, 6, 11, 16, 19),
}
ZONA = ZoneInfo('America/Guayaquil')


def construir(lote):
    if not re.fullmatch('[a-z0-9-]{1,24}', lote):
        raise ValueError('Usa un identificador de hasta 24 letras minúsculas, dígitos o guiones.')
    namespace = uuid5(NAMESPACE_URL, f'eva/presentacion/v1/{lote}')
    servicios = []
    for semana in range(4):
        for dia in (1, 3):
            comienzo = datetime(2026, 10, 5, 12, tzinfo=ZONA) + timedelta(weeks=semana, days=dia)
            for indice, (plato, componentes) in enumerate(PLATOS.items()):
                for numero_porcion, porcion in enumerate(PORCIONES):
                    minuto = 8 * (2 * indice + numero_porcion)
                    servido = comienzo + timedelta(minutes=minuto)
                    retorno = servido + timedelta(minutes=7)
                    for numero, valor in enumerate((*PERFILES[plato], None), 1):
                        referencia = f'{semana}-{dia}-{plato}-{porcion}-{numero}'
                        mediciones = {
                            c: dict(area_servido=100, area_retorno=max(0, valor + semana - numero_porcion - n))
                            for n, c in enumerate(componentes)
                        } if valor is not None else {}
                        servicios.append(dict(
                            id=str(uuid5(namespace, referencia)), bandeja=numero, plato=plato, porcion=porcion,
                            servido=servido.isoformat(), retorno=retorno.isoformat(),
                            sede='principal', modalidad='mesa', franja='m0720_0780',
                            lote_preparacion=f'{lote}-s{semana}-d{dia}-{indice}',
                            origen='SIMULADO', mediciones_sinteticas=mediciones,
                            escenario='PAR_COMPLETO_EJEMPLO' if mediciones else 'PAR_COMPLETO_SIN_ANALISIS',
                            percepcion='ADECUADA' if numero == 2 else None))
    return dict(version=1, lote=lote, destino='MANIFIESTO_LOCAL_SIN_CARGA',
                datos_de_ejemplo=True, servicios=servicios)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lote', required=True)
    parser.add_argument('--salida', type=Path, help='Archivo JSON nuevo. Sin este argumento solo previsualiza.')
    args = parser.parse_args()
    try:
        plan = construir(args.lote)
        servicios = plan['servicios']
        completos = sum(bool(s['mediciones_sinteticas']) for s in servicios)
        destino = args.salida.resolve() if args.salida else None
        print(json.dumps(dict(lote=args.lote, destino=str(destino) if destino else 'solo previsualización',
                              servicios=len(servicios), bandejas=6, pares_planificados=len(servicios),
                              ejemplos_con_mediciones=completos, sin_analisis=len(servicios)-completos,
                              persistencia='ninguna base de datos'), ensure_ascii=False, indent=2))
        if destino:
            contenido = json.dumps(plan, ensure_ascii=False, indent=2) + '\n'
            try:
                with destino.open('x', encoding='utf-8') as archivo:
                    archivo.write(contenido)
            except FileExistsError:
                if destino.read_text(encoding='utf-8') != contenido:
                    raise ValueError('El destino ya contiene otro inventario. Usa un archivo nuevo.') from None
    except (OSError, ValueError) as exc:
        parser.exit(2, f'No se completó la planificación: {exc}\n')


if __name__ == '__main__':
    main()
