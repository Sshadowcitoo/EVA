"""Evalúa pesos privados a 0,80 con máscaras anotadas y sin cambiar el motor de EVA."""
import argparse
from collections import Counter
from hashlib import file_digest
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

from PIL import Image, ImageChops, ImageDraw

from .dataset import leer_poligonos, validar
from .evaluation import metricas_mascara

CLASES_PILOTO = ('yuca', 'pescado', 'arroz', 'pollo', 'menestra', 'carne', 'ensalada')


def _verificar_clases(nombres):
    if not isinstance(nombres, dict) or nombres != dict(enumerate(CLASES_PILOTO)):
        raise ValueError('El modelo debe contener las siete clases del piloto en el orden exacto.')


def _predictor(pesos, lado, runtime):
    if pesos.suffix.lower() == '.onnx':
        from .onnx_inference import PredictorONNX
        predictor = PredictorONNX(pesos)
        _verificar_clases(predictor.nombres)
        if predictor.lado != lado:
            raise ValueError('La entrada ONNX debe coincidir con --imgsz.')
        return predictor
    if pesos.suffix.lower() != '.pt' or not pesos.is_file():
        raise ValueError('Selecciona un archivo PT u ONNX local.')
    os.environ['YOLO_CONFIG_DIR'] = str(runtime)
    os.environ['YOLO_AUTOINSTALL'] = 'false'
    from ultralytics import YOLO
    modelo = YOLO(str(pesos))
    _verificar_clases(modelo.names)
    if modelo.task != 'segment':
        raise ValueError('Se requieren pesos de segmentación.')

    def predecir(imagen):
        import numpy as np
        salida = modelo.predict(np.asarray(imagen)[:, :, ::-1].copy(),
                                imgsz=lado, rect=False, retina_masks=True, conf=.8,
                                iou=.7, max_det=32, device='cpu', verbose=False, save=False)[0]
        if salida.masks is not None:
            for clase, confianza, datos in zip(salida.boxes.cls, salida.boxes.conf, salida.masks.data):
                if float(confianza) > .8:
                    yield dict(codigo=modelo.names[int(clase)],
                               mascara=Image.fromarray((datos.cpu().numpy() > 0).astype('uint8') * 255))
    return predecir


def evaluar(entradas, predecir):
    if not entradas:
        raise ValueError('La partición de evaluación está vacía.')
    totales = {c: dict(referencias=0, omisiones=0, clase_ausente=0, iou_050=0, suma_iou=0.0)
               for c in CLASES_PILOTO}
    filas, tiempos = [], []
    confusiones = Counter()
    for indice, entrada in enumerate(entradas, 1):
        with Image.open(entrada['archivo']) as archivo:
            imagen = archivo.convert('RGB')
        ancho, alto = imagen.size
        referencias = {}
        for clase, puntos in leer_poligonos(entrada['etiquetas'], len(CLASES_PILOTO), vacio_confirmado=True):
            mascara = referencias.setdefault(CLASES_PILOTO[clase], Image.new('L', imagen.size))
            ImageDraw.Draw(mascara).polygon([(x * (ancho - 1), y * (alto - 1)) for x, y in puntos], fill=255)
        inicio = perf_counter()
        predicciones = list(predecir(imagen))
        tiempos.append(1000 * (perf_counter() - inicio))
        uniones = {}
        vacia = Image.new('L', imagen.size)
        for pred in predicciones:
            clase, mascara = pred['codigo'], pred['mascara']
            if clase not in totales or mascara.size != imagen.size:
                raise ValueError('Clase o geometría de máscara incompatible.')
            uniones[clase] = ImageChops.lighter(uniones.get(clase, vacia), mascara)
        resultados = {}
        for clase in CLASES_PILOTO:
            referencia = referencias.get(clase, vacia)
            prediccion = uniones.get(clase, vacia)
            m = metricas_mascara(referencia, prediccion)
            anotada, detectada = bool(m['area_manual']), bool(m['area_modelo'])
            if not (anotada or detectada):
                continue
            t = totales[clase]
            t['referencias'] += anotada
            t['omisiones'] += anotada and not detectada
            t['clase_ausente'] += detectada and not anotada
            iou = float(m['iou'])
            if anotada:
                t['suma_iou'] += iou
                t['iou_050'] += iou >= .5
            resultados[clase] = dict(anotada=anotada, detectada=detectada, iou=iou,
                                     dice=float(m['dice']))
            if detectada and not anotada:
                for esperada, verdad in referencias.items():
                    cruce = metricas_mascara(verdad, prediccion)['iou']
                    if cruce is not None and cruce >= .5:
                        confusiones[(esperada, clase)] += 1
        filas.append(dict(indice=indice, resultados=resultados))
    for total in totales.values():
        suma = total.pop('suma_iou')
        total['iou_medio_con_omisiones'] = suma / total['referencias'] if total['referencias'] else None
    return dict(por_clase=totales, por_imagen=filas,
                confusiones_posibles=[dict(anotada=a, detectada=b, imagenes=n)
                                      for (a, b), n in sorted(confusiones.items())],
                cpu_ms=dict(primera=tiempos[0], mediana_posterior=median(tiempos[1:]) if len(tiempos) > 1 else None))


def _pico_rss():
    try:
        import resource
    except ImportError:
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss if sys.platform == 'darwin' else rss * 1024


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifiesto', type=Path)
    p.add_argument('pesos', type=Path)
    p.add_argument('salida', type=Path)
    p.add_argument('--particion', choices=('val', 'test'), required=True)
    p.add_argument('--imgsz', type=int, default=320)
    args = p.parse_args()
    try:
        datos = validar(args.manifiesto)
        if tuple(datos['clases']) != CLASES_PILOTO:
            raise ValueError('El manifiesto no usa las siete clases en orden.')
        if args.salida.exists():
            raise ValueError('La salida debe ser nueva.')
        pesos = args.pesos.resolve()
        with pesos.open('rb') as f:
            huella = file_digest(f, 'sha256').hexdigest()
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix='eva-evaluacion-') as temporal:
            predecir = _predictor(pesos, args.imgsz, Path(temporal))
            entradas = [e for e in datos['entradas'] if e['particion'] == args.particion]
            informe = evaluar(entradas, predecir)
        versiones = {}
        for paquete in ('Pillow', 'numpy', 'torch', 'ultralytics', 'onnxruntime', 'opencv-python'):
            try:
                versiones[paquete] = version(paquete)
            except PackageNotFoundError:
                continue
        with args.manifiesto.open('rb') as f:
            huella_manifiesto = file_digest(f, 'sha256').hexdigest()
        informe.update(sha256_pesos=huella, sha256_manifiesto=huella_manifiesto,
                       versiones=versiones, particion=args.particion,
                       imgsz=args.imgsz, umbral=.8, rect=False, pico_rss_proceso_bytes=_pico_rss(),
                       alcance='Máscaras por imagen antes de eliminar solapamientos. No mide consumo ni autoriza despliegue.')
        with args.salida.open('x', encoding='utf-8') as f:
            json.dump(informe, f, ensure_ascii=False, indent=2)
    except (ValueError, OSError, ImportError) as exc:
        p.exit(2, f'No se completó la evaluación: {exc}\n')


if __name__ == '__main__':
    main()
