from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

try:
    import numpy as np
    from .onnx_inference import PredictorONNX, _nms
except ImportError:
    np = None

from .inference import EntradaInvalida


@unittest.skipIf(np is None, 'Runtime ONNX opcional no instalado.')
class OnnxInferenceTests(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.pesos = Path(carpeta.name) / 'modelo.onnx'
        self.pesos.write_bytes(b'fixture-no-es-un-modelo')
        self.nombres = {0: 'arroz', 1: 'pollo'}
        self.pred = np.zeros((1, 7, 1), dtype=np.float32)
        self.pred[0, :, 0] = [32, 32, 32, 32, .9, .1, 1]
        self.proto = np.ones((1, 1, 16, 16), dtype=np.float32)
        self.forma = [1, 3, 64, 64]
        self.sesion = SimpleNamespace(
            get_inputs=lambda: [SimpleNamespace(name='images', shape=self.forma, type='tensor(float)')],
            get_modelmeta=lambda: SimpleNamespace(custom_metadata_map={'task': 'segment', 'names': str(self.nombres)}),
            run=self.ejecutar,
        )
        parche = patch('visual_service.onnx_inference._sesion', return_value=self.sesion)
        parche.start()
        self.addCleanup(parche.stop)

    def ejecutar(self, salidas, entradas):
        self.assertEqual(entradas['images'].shape, (1, 3, 64, 64))
        self.assertEqual(entradas['images'].dtype, np.float32)
        self.assertGreaterEqual(float(entradas['images'].min()), 0)
        self.assertLessEqual(float(entradas['images'].max()), 1)
        return [self.pred, self.proto]

    def test_decodifica_clase_y_mascara_binaria_alineada(self):
        resultados = list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 100))))
        self.assertEqual(len(resultados), 1)
        r = resultados[0]
        self.assertEqual(r['codigo'], 'arroz')
        self.assertAlmostEqual(r['confianza'], .9)
        self.assertEqual(r['mascara'].mode, 'L')
        self.assertEqual(r['mascara'].size, (100, 100))
        self.assertEqual(r['mascara'].getbbox(), (25, 25, 75, 75))
        self.assertEqual(sum(r['mascara'].histogram()[1:255]), 0)

    def test_sin_deteccion_no_inventa_una_mascara(self):
        self.pred[0, 4:6] = 0
        self.assertEqual(list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 60)))), [])
        self.pred[0, 4, 0] = .79
        self.assertEqual(list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 60)))), [])

    def test_rechaza_coco_y_formas_dinamicas(self):
        self.nombres[0] = 'person'
        with self.assertRaises(EntradaInvalida):
            PredictorONNX(self.pesos)
        self.nombres[0] = 'arroz'
        self.forma[2] = None
        with self.assertRaises(EntradaInvalida):
            PredictorONNX(self.pesos)

    def test_rechaza_tensores_incompatibles_y_no_finitos(self):
        self.pred[0, 0, 0] = np.nan
        with self.assertRaises(EntradaInvalida):
            list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 100))))
        self.pred = np.zeros((1, 8, 1), dtype=np.float32)
        with self.assertRaises(EntradaInvalida):
            list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 100))))

    def test_nms_no_confunde_componentes_distintos(self):
        cajas = np.array([[0, 0, 20, 20]] * 3, dtype=np.float32)
        scores = np.array([.95, .9, .85], dtype=np.float32)
        self.assertEqual(_nms(cajas, scores, np.array([0, 0, 1])), [0, 2])

    def test_mantiene_tamano_de_fotos_grandes(self):
        r = list(PredictorONNX(self.pesos)(Image.new('RGB', (1600, 1200))))[0]
        self.assertEqual(r['mascara'].size, (1600, 1200))
        self.assertEqual(sum(r['mascara'].histogram()[1:255]), 0)
