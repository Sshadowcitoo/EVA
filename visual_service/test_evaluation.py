from decimal import Decimal
import unittest
from PIL import Image, ImageDraw
from .evaluation import evaluar_par,metricas_mascara


def mascara(caja=None):
    imagen=Image.new('L',(20,20))
    if caja:ImageDraw.Draw(imagen).rectangle(caja,fill=255)
    return imagen


class EvaluacionTests(unittest.TestCase):
    def test_error_en_puntos_y_segmentacion_no_son_lo_mismo(self):
        inicial,final=mascara((0,0,9,9)),mascara((0,0,4,4))
        datos=evaluar_par(inicial,final,inicial,mascara((0,0,4,5)),geometria_verificada=True)
        self.assertEqual(datos['porcentaje_manual'],25)
        self.assertEqual(datos['porcentaje_modelo'],30)
        self.assertEqual(datos['error_absoluto_pp'],5)
        self.assertEqual(datos['retorno']['iou'],Decimal(25)/30)

    def test_falta_deteccion_no_equivale_a_error_cero(self):
        datos=evaluar_par(mascara((0,0,9,9)),mascara(),mascara((0,0,9,9)),None,geometria_verificada=True)
        self.assertIsNone(datos['porcentaje_modelo'])
        self.assertIsNone(datos['error_absoluto_pp'])
        self.assertEqual(datos['estado'],'NO_CONCLUYENTE')

    def test_ambas_vacias_no_inflan_media_iou(self):
        datos=metricas_mascara(mascara(),mascara())
        self.assertTrue(datos['ambas_vacias']);self.assertIsNone(datos['iou']);self.assertIsNone(datos['dice'])

    def test_mayor_100_no_se_recorta(self):
        datos=evaluar_par(mascara((0,0,4,4)),mascara(),mascara((0,0,4,4)),mascara((0,0,9,9)),geometria_verificada=True)
        self.assertEqual(datos['porcentaje_modelo'],400)
        self.assertIn('MAYOR_100',datos['motivos'])
        self.assertEqual(datos['estado'],'NO_CONCLUYENTE')

    def test_geometria_no_aprobada_no_produce_porcentaje(self):
        imagen=mascara((0,0,9,9))
        datos=evaluar_par(imagen,imagen,imagen,imagen)
        self.assertIsNone(datos['porcentaje_modelo'])
        self.assertEqual(datos['servido']['iou'],1)
        self.assertIn('GEOMETRIA_NO_VERIFICADA',datos['motivos'])
