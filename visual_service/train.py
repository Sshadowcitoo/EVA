"""Entrenamiento explícito desde anotaciones y pesos locales, sin descargas implícitas."""
import argparse
import json
import os
from pathlib import Path
import shutil

from .dataset import DatasetInvalido, validar


def exportar(manifiesto, destino):
    datos = validar(manifiesto)
    faltantes = set(datos['clases']) - set(datos['resumen']['train']['clases'])
    if faltantes:
        raise DatasetInvalido('Faltan clases de entrenamiento: ' + ', '.join(sorted(faltantes)))
    destino = Path(destino).resolve()
    # No sobrescribir una exportación ni una carpeta de fotografías originales.
    destino.mkdir(parents=True, exist_ok=False)
    for particion in ('train', 'val', 'test'):
        (destino / 'images' / particion).mkdir(parents=True)
        (destino / 'labels' / particion).mkdir(parents=True)
    for numero, entrada in enumerate(datos['entradas']):
        nombre = f'{numero:06d}'
        extension = entrada['archivo'].suffix.lower()
        shutil.copyfile(entrada['archivo'], destino / 'images' / entrada['particion'] / (nombre + extension))
        shutil.copyfile(entrada['etiquetas'], destino / 'labels' / entrada['particion'] / (nombre + '.txt'))
    configuracion = dict(path=str(destino), train='images/train', val='images/val', test='images/test',
                         names={i:c for i,c in enumerate(datos['clases'])})
    # JSON es un subconjunto de YAML, aceptado por el lector de Ultralytics.
    yaml = destino / 'dataset.yaml'
    yaml.write_text(json.dumps(configuracion, ensure_ascii=False, indent=2), encoding='utf-8')
    (destino / 'manifiesto_origen.json').write_bytes(Path(manifiesto).read_bytes())
    return yaml, datos


def entrenar(manifiesto, destino, pesos, *, epochs=30, imgsz=640, device='cpu'):
    pesos = Path(pesos).resolve()
    if not pesos.is_file() or pesos.suffix.lower() != '.pt':
        raise DatasetInvalido('Selecciona un archivo .pt local de procedencia conocida; no se descarga automáticamente.')
    if type(epochs) is not int or not 1 <= epochs <= 1000 or type(imgsz) is not int or not 64 <= imgsz <= 2048:
        raise DatasetInvalido('epochs debe estar en 1..1000 e imgsz en 64..2048.')
    yaml, datos = exportar(manifiesto, destino)
    runtime = Path(destino).resolve() / 'runtime-config'
    runtime.mkdir()
    os.environ['YOLO_CONFIG_DIR'] = str(runtime)
    from ultralytics import YOLO
    modelo = YOLO(str(pesos))
    if modelo.task != 'segment':
        raise DatasetInvalido('Los pesos deben ser de segmentación, no de detección por cajas.')
    # AMP realiza comprobaciones que pueden descargar otros pesos: queda desactivado.
    resultado = modelo.train(data=str(yaml), epochs=epochs, imgsz=imgsz, device=device,
        project=str(Path(destino).resolve() / 'runs'), name='entrenamiento', exist_ok=False,
        seed=0, deterministic=True, amp=False, workers=0, batch=2, plots=False)
    return resultado, datos


def main():
    parser = argparse.ArgumentParser(description='Prepara y entrena segmentación con un dataset anotado.')
    parser.add_argument('manifiesto', type=Path)
    parser.add_argument('destino', type=Path)
    parser.add_argument('--pesos', type=Path)
    parser.add_argument('--epochs', type=int, default=30)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--device', default='cpu')
    args = parser.parse_args()
    try:
        if args.pesos is None:
            yaml, _ = exportar(args.manifiesto, args.destino)
            print(f'Dataset exportado, sin entrenar: {yaml}')
        else:
            entrenar(args.manifiesto, args.destino, args.pesos, epochs=args.epochs, imgsz=args.imgsz, device=args.device)
    except (DatasetInvalido, FileExistsError) as exc:
        parser.exit(2, f'No se completó el entrenamiento/exportación: {exc}\n')


if __name__ == '__main__':
    main()
