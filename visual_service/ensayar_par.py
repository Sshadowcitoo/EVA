"""Prueba un par privado con el ONNX de EVA sin afirmar identidad geométrica."""
import argparse
import json
from pathlib import Path
from uuid import uuid4

from .evaluar_candidato import CLASES_PILOTO
from .inference import analizar


def ensayar(predictor, servido, retorno, codigos, version):
    metadata = dict(schema_version=1, request_id=str(uuid4()), servicio_id=str(uuid4()),
                    version_modelo=version, version_configuracion='ensayo-privado-v1', origen='SIMULADO',
                    componentes=[dict(id=i, codigo=c) for i, c in enumerate(codigos, 1)])
    respuesta = analizar(metadata, servido, retorno, predictor, version_modelo=version, identidad_verificada=False)
    for codigo, fila in zip(codigos, respuesta['componentes'], strict=True):
        fila.update(codigo=codigo, etapas=[m['etapa'] for m in fila.pop('mascaras')])
    respuesta['alcance'] = 'Ensayo privado de captura e inferencia. Geometría sin verificar y sin porcentajes.'
    return respuesta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for nombre in ('pesos', 'servido', 'retorno', 'salida'):
        parser.add_argument(nombre, type=Path)
    parser.add_argument('--componentes', nargs='+', choices=CLASES_PILOTO, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    from .onnx_inference import PredictorONNX
    try:
        informe = ensayar(PredictorONNX(args.pesos), args.servido.read_bytes(), args.retorno.read_bytes(),
                         args.componentes, args.version)
        with args.salida.open('x', encoding='utf-8') as archivo:
            json.dump(informe, archivo, ensure_ascii=False, indent=2)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'No se completó el ensayo: {exc}\n')


if __name__ == '__main__':
    main()
