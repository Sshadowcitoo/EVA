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

    def test_umbral_080_es_estricto_como_la_referencia(self):
        self.pred[0, 4, 0] = .8
        self.assertEqual(list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 60)))), [])
        self.pred[0, 4, 0] = np.nextafter(np.float32(.8), np.float32(1))
        self.assertEqual(len(list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 60))))), 1)

    def test_reduccion_sin_antialias_y_letterbox_rgb_114(self):
        # Cada bloque 2x2 tiene dos ceros y dos 255: INTER_LINEAR da 128.
        patron = ((np.indices((64, 128)).sum(axis=0) % 2) * 255).astype(np.uint8)
        imagen = Image.fromarray(np.repeat(patron[:, :, None], 3, axis=2))
        with patch.object(self.sesion, 'run', wraps=self.ejecutar) as ejecutar:
            list(PredictorONNX(self.pesos)(imagen))
        tensor = ejecutar.call_args.args[1]['images']
        esperado = np.full((1, 3, 64, 64), 114, dtype=np.float32)
        esperado[:, :, 16:48] = 128
        np.testing.assert_array_equal(tensor, esperado / 255)

    def test_padding_impar_no_elimina_una_fila_del_prototipo(self):
        self.pred[0, :4, 0] = [32, 32, 64, 64]
        self.proto[:, :, :8] = -1
        # 768x429 -> prototipo 16x16: alto sin padding round(8.9375)=9.
        # Se recortan filas [3:12], no [4:12]; la frontera queda en y=238.
        r = list(PredictorONNX(self.pesos)(Image.new('RGB', (768, 429))))[0]
        self.assertEqual(r['mascara'].getbbox(), (0, 238, 768, 429))

    def test_recorte_fraccionario_usa_indices_enteros_dentro_de_la_caja(self):
        self.pred[0, :4, 0] = [32.16, 32.16, 32, 32]
        r = list(PredictorONNX(self.pesos)(Image.new('RGB', (100, 100))))[0]
        self.assertEqual(r['mascara'].getbbox(), (26, 26, 76, 76))

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
