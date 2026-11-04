"""Inferencia CPU de YOLO11-seg exportado, sin importar PyTorch ni descargar archivos."""
import ast
from pathlib import Path

import numpy as np
from PIL import Image

from .dataset import CLASES
from .inference import EntradaInvalida


def _sesion(pesos):
    import onnxruntime as ort
    opciones = ort.SessionOptions()
    opciones.intra_op_num_threads = 2
    opciones.inter_op_num_threads = 1
    opciones.enable_cpu_mem_arena = False
    return ort.InferenceSession(str(pesos), sess_options=opciones, providers=['CPUExecutionProvider'])


def _nms(cajas, scores, clases, limite=32):
    orden = np.argsort(-scores, kind='stable')[:3000]
    seleccion = []
    while orden.size and len(seleccion) < limite:
        actual = int(orden[0])
        seleccion.append(actual)
        otros = orden[1:]
        izquierda = np.maximum(cajas[actual, :2], cajas[otros, :2])
        derecha = np.minimum(cajas[actual, 2:], cajas[otros, 2:])
        inter = np.maximum(derecha - izquierda, 0).prod(axis=1)
        area = np.maximum(cajas[:, 2:] - cajas[:, :2], 0).prod(axis=1)
        union = area[actual] + area[otros] - inter
        iou = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
        orden = otros[(clases[otros] != clases[actual]) | (iou <= .7)]
    return seleccion


class PredictorONNX:
    def __init__(self, pesos):
        pesos = Path(pesos).resolve()
        if not pesos.is_file() or pesos.suffix.lower() != '.onnx':
            raise EntradaInvalida('Se necesitan pesos ONNX locales de segmentación.')
        self.sesion = _sesion(pesos)
        entradas = self.sesion.get_inputs()
        if len(entradas) != 1:
            raise EntradaInvalida('El modelo necesita una sola entrada RGB estática.')
        entrada = entradas[0]
        forma = entrada.shape
        if (entrada.type != 'tensor(float)' or len(forma) != 4 or forma[:2] != [1, 3]
                or type(forma[2]) is not int or forma[2] != forma[3] or not 64 <= forma[2] <= 1024):
            raise EntradaInvalida('Entrada ONNX incompatible con el motor privado.')
        self.entrada, self.lado = entrada.name, forma[2]
        metadata = self.sesion.get_modelmeta().custom_metadata_map
        try:
            nombres = ast.literal_eval(metadata.get('names', ''))
        except (ValueError, SyntaxError):
            raise EntradaInvalida('Faltan las clases verificables del modelo.') from None
        if (metadata.get('task') != 'segment' or not isinstance(nombres, dict) or not nombres
                or any(type(k) is not int for k in nombres) or set(nombres) != set(range(len(nombres)))
                or len(nombres) > len(CLASES)
                or any(n not in CLASES for n in nombres.values())
                or len(set(nombres.values())) != len(nombres)):
            raise EntradaInvalida('El modelo no segmenta los componentes del piloto.')
        self.nombres = nombres

    def __call__(self, imagen):
        ancho, alto = imagen.size
        ratio = min(self.lado / ancho, self.lado / alto)
        nw, nh = round(ancho * ratio), round(alto * ratio)
        izquierda, arriba = (self.lado - nw) // 2, (self.lado - nh) // 2
        cuadrada = Image.new('RGB', (self.lado, self.lado), (114, 114, 114))
        cuadrada.paste(imagen.resize((nw, nh), Image.Resampling.BILINEAR), (izquierda, arriba))
        tensor = np.asarray(cuadrada, dtype=np.float32).transpose(2, 0, 1)[None] / 255
        salidas = self.sesion.run(None, {self.entrada: tensor})
        if len(salidas) != 2:
            raise EntradaInvalida('El modelo no devuelve predicciones y prototipos de máscara.')
        pred, proto = salidas
        if (pred.ndim != 3 or pred.shape[0] != 1 or proto.ndim != 4 or proto.shape[0] != 1
                or not 1 <= proto.shape[1] <= 256 or max(proto.shape[2:]) > 1024
                or min(proto.shape[2:]) < 1 or not np.isfinite(pred).all() or not np.isfinite(proto).all()):
            raise EntradaInvalida('Tensores de segmentación inválidos.')
        nc, nm = len(self.nombres), proto.shape[1]
        canales = 4 + nc + nm
        if pred.shape[1] != canales or not 1 <= pred.shape[2] <= 100_000:
            raise EntradaInvalida('Salida ONNX incompatible; exporta YOLO11-seg sin NMS incorporado.')
        filas = pred[0].T
        scores = filas[:, 4:4 + nc].max(axis=1)
        clases = filas[:, 4:4 + nc].argmax(axis=1)
        validos = (scores >= .8) & (scores <= 1) & (filas[:, 2] > 0) & (filas[:, 3] > 0)
        filas, scores, clases = filas[validos], scores[validos], clases[validos]
        cajas = np.concatenate((filas[:, :2] - filas[:, 2:4] / 2, filas[:, :2] + filas[:, 2:4] / 2), axis=1)
        cajas[:, [0, 2]] = (cajas[:, [0, 2]] - izquierda) / ratio
        cajas[:, [1, 3]] = (cajas[:, [1, 3]] - arriba) / ratio
        cajas[:, [0, 2]] = cajas[:, [0, 2]].clip(0, ancho)
        cajas[:, [1, 3]] = cajas[:, [1, 3]].clip(0, alto)
        mh, mw = proto.shape[2:]
        gain = min(mh / alto, mw / ancho)
        px, py = (mw - ancho * gain) / 2, (mh - alto * gain) / 2
        corte = (round(px - .1), round(py - .1), round(mw - px + .1), round(mh - py + .1))
        # Limitar los intermedios float; el contrato conserva tamaño original y máscara binaria L.
        factor = min(1, 1280 / max(ancho, alto))
        trabajo = (max(1, round(ancho * factor)), max(1, round(alto * factor)))
        for i in _nms(cajas, scores, clases):
            logits = (filas[i, 4 + nc:] @ proto[0].reshape(nm, -1)).reshape(mh, mw)
            flotante = Image.fromarray(logits.astype(np.float32)).crop(corte).resize(trabajo, Image.Resampling.BILINEAR)
            binaria = np.asarray(flotante) > 0
            x1, y1, x2, y2 = np.rint(cajas[i] * np.array([factor, factor, factor, factor])).astype(int)
            binaria[:y1] = False
            binaria[y2:] = False
            binaria[:, :x1] = False
            binaria[:, x2:] = False
            mascara = Image.fromarray(binaria.astype(np.uint8) * 255)
            if mascara.size != imagen.size:
                mascara = mascara.resize(imagen.size, Image.Resampling.NEAREST)
            if mascara.getbbox():
                yield dict(codigo=self.nombres[int(clases[i])], confianza=float(scores[i]), mascara=mascara)
