"""Verificación optativa: artefactos privados, nunca descargados ni versionados.

EVA_DIAGNOSTICO_PRIVADO=/ruta/al/paquete python -m unittest visual_service.test_paridad_privada
No mide precisión contra anotaciones ni habilita comparabilidad.
"""
import base64
from io import BytesIO
import os
from pathlib import Path
import unittest
from uuid import uuid4


@unittest.skipUnless(os.environ.get('EVA_DIAGNOSTICO_PRIVADO'), 'Requiere el paquete privado de diagnóstico.')
class ParidadPrivadaTests(unittest.TestCase):
    def comparar(self, referencia):
        import numpy as np
        from PIL import Image
        from ultralytics import YOLO
        from .onnx_inference import PredictorONNX
        base = Path(os.environ['EVA_DIAGNOSTICO_PRIVADO'])
        predictor = PredictorONNX(base / 'pesos/modelo_demo_7_clases.onnx')
        modelo = YOLO(str(base / 'pesos' / referencia), task='segment')
        for nombre in ('encebollado_000', 'arroz_carne_menestra_000', 'seco_pollo_000'):
            with self.subTest(imagen=nombre, pesos=referencia):
                imagen = Image.open(base / 'imagenes' / (nombre + '.png')).convert('RGB')
                resultado = modelo.predict(np.asarray(imagen)[:, :, ::-1].copy(), imgsz=320,
                    rect=False, retina_masks=True, conf=.8, iou=.7, max_det=32,
                    device='cpu', verbose=False, save=False)[0]
                nuestro, otro = {}, {}
                for d in predictor(imagen):
                    c = d['codigo']
                    nuestro[c] = nuestro.get(c, False) | (np.asarray(d['mascara']) > 0)
                if resultado.masks is not None:
                    for k, m in zip(resultado.boxes.cls.cpu().numpy().astype(int), resultado.masks.data.cpu().numpy()):
                        c = resultado.names[int(k)]
                        otro[c] = otro.get(c, False) | (m > 0)
                self.assertEqual(set(nuestro), set(otro))
                self.assertTrue(nuestro)
                for c in nuestro:
                    union = (nuestro[c] | otro[c]).sum()
                    self.assertGreaterEqual(float((nuestro[c] & otro[c]).sum() / union), .999)

    def test_mismo_onnx_en_ambas_implementaciones(self):
        self.comparar('modelo_demo_7_clases.onnx')

    def test_checkpoint_pt_del_mismo_entrenamiento(self):
        self.comparar('best.pt')

    def test_encebollado_elimina_conflictos_sin_aprobar_porcentajes(self):
        import numpy as np
        from PIL import Image
        from .inference import analizar
        from .onnx_inference import PredictorONNX
        base = Path(os.environ['EVA_DIAGNOSTICO_PRIVADO'])
        datos = (base / 'imagenes/encebollado_000.png').read_bytes()
        imagen = Image.open(BytesIO(datos)).convert('RGB')
        predictor = PredictorONNX(base / 'pesos/modelo_demo_7_clases.onnx')
        uniones = {}
        for d in predictor(imagen):
            c = d['codigo']
            uniones[c] = uniones.get(c, False) | (np.asarray(d['mascara']) > 0)
        compartidos = uniones['yuca'] & uniones['pescado']
        self.assertTrue(compartidos.any(), 'El control debe ejercitar un solapamiento real entre salidas.')
        meta = dict(schema_version=1, request_id=str(uuid4()), servicio_id=str(uuid4()),
            version_modelo='diagnostico', version_configuracion='diagnostico', origen='SIMULADO',
            componentes=[dict(id=i + 1, codigo=c) for i, c in enumerate(('yuca', 'pescado'))])
        dto = analizar(meta, datos, datos, predictor, version_modelo='diagnostico', identidad_verificada=True)
        for componente, c in zip(dto['componentes'], ('yuca', 'pescado')):
            self.assertFalse(componente['comparable'])
            self.assertNotIn('porcentaje', componente)
            for m in componente['mascaras']:
                salida = np.asarray(Image.open(BytesIO(base64.b64decode(m['png_base64'])))) > 0
                np.testing.assert_array_equal(salida, uniones[c] & ~compartidos)
