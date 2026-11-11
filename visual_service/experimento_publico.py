"""Prepara y ejecuta el ajuste sin incorporar imágenes de prueba al dataset YOLO."""
import argparse
from hashlib import file_digest
import json
import os
from pathlib import Path
import shutil

from PIL import Image, ImageOps

from .dataset import validar
from .evaluar_candidato import CLASES_PILOTO

EXTENSIONES = {'.jpg', '.jpeg', '.png'}
PERFILES = {
    'conservador': dict(epochs=4, lr0=.00015, freeze=10),
    'completo': dict(epochs=6, lr0=.0004, freeze=0),
}


def _huella(ruta):
    with Image.open(ruta) as archivo:
        imagen = ImageOps.exif_transpose(archivo).convert('L').resize((9, 8), Image.Resampling.LANCZOS)
        datos = list(imagen.get_flattened_data())
    return sum((datos[i] > datos[i + 1]) << (i - i // 9) for i in range(71) if i % 9 != 8)


def auditar(manifiesto, base, reservadas):
    datos = validar(manifiesto)
    if tuple(datos['clases']) != CLASES_PILOTO:
        raise ValueError('El experimento exige las siete clases en orden.')
    originales = json.loads(manifiesto.read_text(encoding='utf-8'))['imagenes']
    fuentes = {}
    for fila in originales:
        fuente = fila.get('fuente')
        if not fuente or not all(fila.get(k) for k in ('autor', 'licencia', 'url', 'sha256_original')):
            raise ValueError('Falta procedencia de una imagen.')
        if fuentes.setdefault(fuente, fila['particion']) != fila['particion']:
            raise ValueError(f'Fuente compartida entre particiones: {fuente}.')
    referencias = []
    for particion, raiz in [('train', base / 'images/train'), ('val', base / 'images/val'), ('reservada', reservadas)]:
        archivos = sorted(p for p in raiz.rglob('*') if p.suffix.lower() in EXTENSIONES)
        if not archivos:
            raise ValueError(f'Falta la población de referencia: {particion}.')
        referencias.extend((particion, ruta, _huella(ruta)) for ruta in archivos)

    for entrada in datos['entradas']:
        ruta = entrada['archivo']
        original = manifiesto.parent / 'originales' / ruta.with_suffix('.jpg').name
        metadata = next(f for f in originales if (manifiesto.parent / f['archivo']).resolve() == ruta)
        with original.open('rb') as archivo:
            if file_digest(archivo, 'sha256').hexdigest() != metadata['sha256_original']:
                raise ValueError(f'La imagen original no coincide con su hash: {original.name}.')
        huellas = {_huella(original), _huella(ruta)}
        particion = entrada['particion']
        for otra, archivo, huella in referencias:
            if otra != particion and min((h ^ huella).bit_count() for h in huellas) <= 4:
                raise ValueError(f'Revisar similitud entre particiones: {ruta.name} y {archivo.name}.')
        referencias.extend((particion, ruta, h) for h in huellas)
    return datos


def preparar(manifiesto, base, reservadas, destino):
    datos = auditar(manifiesto, base, reservadas)
    destino.mkdir(parents=True, exist_ok=False)
    for tipo in ('images', 'labels'):
        for particion in ('train', 'val'):
            shutil.copytree(base / tipo / particion, destino / tipo / particion,
                            ignore=shutil.ignore_patterns('*.cache'))
    for i, fila in enumerate(datos['entradas']):
        particion = fila['particion']
        if particion == 'test':
            continue
        shutil.copyfile(fila['archivo'], destino / 'images' / particion / f'eva_publica_{i}.png')
        shutil.copyfile(fila['etiquetas'], destino / 'labels' / particion / f'eva_publica_{i}.txt')
    yaml = destino / 'dataset.yaml'
    yaml.write_text(json.dumps(dict(path=str(destino.resolve()), train='images/train', val='images/val',
                                    names=dict(enumerate(CLASES_PILOTO)))), encoding='utf-8')
    return yaml


def entrenar(dataset, pesos, destino, perfil):
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    import torch
    from ultralytics import YOLO
    torch.set_num_threads(2)
    modelo = YOLO(str(pesos), task='segment')
    modelo.train(data=str(dataset.resolve()), project=str(destino.resolve()), name=perfil,
                 seed=17, imgsz=320, patience=3, workers=0, batch=8, optimizer='AdamW',
                 device='cpu', plots=False, amp=False, pretrained=True, save_period=1,
                 mosaic=0, copy_paste=0, translate=.06, **PERFILES[perfil])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='accion', required=True)
    preparo = sub.add_parser('preparar')
    for nombre in ('manifiesto', 'base', 'reservadas', 'destino'):
        preparo.add_argument(nombre, type=Path)
    ajuste = sub.add_parser('entrenar')
    for nombre in ('dataset', 'pesos', 'destino'):
        ajuste.add_argument(nombre, type=Path)
    ajuste.add_argument('perfil', choices=PERFILES)
    args = parser.parse_args()
    try:
        if args.accion == 'preparar':
            print(preparar(args.manifiesto, args.base, args.reservadas, args.destino))
        else:
            entrenar(args.dataset, args.pesos, args.destino, args.perfil)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'No se completó el experimento: {exc}\n')


if __name__ == '__main__':
    main()
