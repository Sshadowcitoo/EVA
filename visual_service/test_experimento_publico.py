import hashlib
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from .ensayar_par import ensayar
from .evaluar_candidato import CLASES_PILOTO
from .experimento_publico import preparar


class ExperimentoPublicoTests(unittest.TestCase):
    def test_fuentes_y_controles_no_entran_en_el_ajuste(self):
        with TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            base, reserva = raiz / 'base', raiz / 'reserva'
            originales = raiz / 'originales'
            originales.mkdir()
            reserva.mkdir()
            for nombre in ('images/train', 'images/val', 'labels/train', 'labels/val'):
                (base / nombre).mkdir(parents=True)
            ascendente = Image.new('L', (9, 8))
            ascendente.putdata([i % 9 * 25 for i in range(72)])
            descendente = ascendente.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            for nombre in ('train', 'val'):
                ascendente.save(base / 'images' / nombre / 'base.png')
                (base / 'labels' / nombre / 'base.txt').write_text('')
            ascendente.save(reserva / 'reservada.png')
            filas = []
            for i, particion in enumerate(('train', 'val', 'test')):
                foto = raiz / f'{i}.png'
                # Patrones distintos para verificar la distancia visual.
                imagen = Image.new('L', (9, 8))
                imagen.putdata([(x if y < i * 2 + 1 else 8 - x) * 25 for y in range(8) for x in range(9)])
                imagen.save(foto)
                original = originales / f'{i}.jpg'
                imagen.save(original)
                etiqueta = raiz / f'{i}.txt'
                etiqueta.write_text('')
                filas.append(dict(archivo=foto.name, etiquetas=etiqueta.name, particion=particion,
                                  grupo=str(i), origen='REAL', vacio_confirmado=True, fuente=str(i),
                                  autor=str(i), url=f'https://example.org/{i}', licencia='CC0',
                                  sha256_original=hashlib.sha256(original.read_bytes()).hexdigest()))
            manifiesto = raiz / 'manifiesto.json'
            contenido = dict(schema_version=1, clases=list(CLASES_PILOTO), imagenes=filas)
            filas[2]['fuente'] = filas[0]['fuente']
            manifiesto.write_text(json.dumps(contenido))
            with self.assertRaisesRegex(ValueError, 'Fuente compartida'):
                preparar(manifiesto, base, reserva, raiz / 'resultado')
            filas[2]['fuente'] = '2'
            manifiesto.write_text(json.dumps(contenido))
            destino = raiz / 'resultado'
            preparar(manifiesto, base, reserva, destino)
            self.assertTrue((destino / 'images/train/eva_publica_0.png').is_file())
            self.assertTrue((destino / 'images/val/eva_publica_1.png').is_file())
            self.assertFalse(list(destino.rglob('eva_publica_2.png')))
            self.assertFalse(list(destino.rglob('reservada.png')))
            descendente.save(raiz / '2.png')
            descendente.save(reserva / 'similar.png')
            with self.assertRaisesRegex(ValueError, 'Revisar similitud'):
                preparar(manifiesto, base, reserva, raiz / 'duplicado')

    def test_ensayo_no_habilita_comparabilidad_ni_completa_omisiones(self):
        archivo = BytesIO()
        Image.new('RGB', (16, 16)).save(archivo, 'PNG')

        def predecir(imagen):
            return [dict(codigo='arroz', confianza=.91, mascara=Image.new('L', imagen.size, 255))]

        salida = ensayar(predecir, archivo.getvalue(), archivo.getvalue(), ['arroz', 'pollo'], 'prueba')
        arroz, pollo = salida['componentes']
        self.assertEqual(arroz['etapas'], ['SERVIDO', 'RETORNO'])
        self.assertEqual(pollo['etapas'], [])
        self.assertIsNone(pollo['area_residual'])
        self.assertTrue(all(not c['comparable'] and 'porcentaje' not in c for c in (arroz, pollo)))
