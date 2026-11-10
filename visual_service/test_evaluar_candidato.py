from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from .evaluar_candidato import CLASES_PILOTO, _verificar_clases, evaluar


class EvaluarCandidatoTests(unittest.TestCase):
    def test_mide_omision_clase_ausente_y_confusion_sin_inferencia(self):
        with TemporaryDirectory() as temporal:
            imagen = Path(temporal) / 'foto.png'
            etiqueta = Path(temporal) / 'foto.txt'
            Image.new('RGB', (8, 8)).save(imagen)
            etiqueta.write_text('3 0 0 1 0 1 1 0 1\n', encoding='utf-8')
            informe = evaluar([dict(archivo=imagen, etiquetas=etiqueta)], lambda foto: [
                dict(codigo='carne', mascara=Image.new('L', foto.size, 255))])
        self.assertEqual(informe['por_clase']['pollo']['omisiones'], 1)
        self.assertEqual(informe['por_clase']['pollo']['iou_medio_con_omisiones'], 0)
        self.assertEqual(informe['por_clase']['carne']['clase_ausente'], 1)
        self.assertIsNone(informe['por_clase']['carne']['iou_medio_con_omisiones'])
        self.assertEqual(informe['confusiones_posibles'], [dict(anotada='pollo', detectada='carne', imagenes=1)])

    def test_clases_exigen_orden_y_excluyen_maduro(self):
        _verificar_clases(dict(enumerate(CLASES_PILOTO)))
        for clases in (CLASES_PILOTO[::-1], CLASES_PILOTO + ('maduro',), CLASES_PILOTO[:-1]):
            with self.assertRaises(ValueError):
                _verificar_clases(dict(enumerate(clases)))
