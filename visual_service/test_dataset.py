from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image
from .dataset import DatasetInvalido, validar
from .train import exportar


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temporal = TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.datos = dict(schema_version=1, clases=['arroz'], imagenes=[])
        for i, particion in enumerate(('train', 'val', 'test')):
            Image.new('RGB', (20, 20), (i*60, 20, 30)).save(self.raiz / f'{i}.png')
            (self.raiz / f'{i}.txt').write_text('0 0.1 0.1 0.8 0.1 0.8 0.8', encoding='utf-8')
            self.datos['imagenes'].append(dict(archivo=f'{i}.png', etiquetas=f'{i}.txt',
                grupo=f'preparacion-{i}', particion=particion, origen='REAL'))
        self.manifiesto = self.raiz / 'manifest.json'

    def escribir(self):
        self.manifiesto.write_text(json.dumps(self.datos), encoding='utf-8')
        return self.manifiesto

    def test_validar_y_exportar_sin_modificar_originales(self):
        resultado = validar(self.escribir())
        self.assertEqual(resultado['resumen']['train']['grupos'], 1)
        self.assertEqual(resultado['resumen']['test']['clases'], {'arroz':1})
        foto = (self.raiz/'0.png').read_bytes()
        yaml, _ = exportar(self.manifiesto, self.raiz/'exportado')
        self.assertEqual(json.loads(yaml.read_text())['names'], {'0':'arroz'})
        self.assertEqual((self.raiz/'0.png').read_bytes(), foto)
        with self.assertRaises(FileExistsError):
            exportar(self.manifiesto, self.raiz/'exportado')

    def test_todas_las_etapas_y_variantes_de_preparacion_quedan_juntas(self):
        self.datos['imagenes'][1]['grupo'] = 'preparacion-0'
        with self.assertRaisesRegex(DatasetInvalido, 'Fuga de datos'):
            validar(self.escribir())

    def test_pixeles_repetidos_detectados_con_otro_nombre(self):
        (self.raiz/'1.png').write_bytes((self.raiz/'0.png').read_bytes())
        with self.assertRaisesRegex(DatasetInvalido, 'píxeles idénticos'):
            validar(self.escribir())

    def test_sinteticas_solo_entrenamiento_y_con_origen_real(self):
        self.datos['imagenes'][1]['origen'] = 'SINTETICO'
        with self.assertRaisesRegex(DatasetInvalido, 'solo pertenecen a train'):
            validar(self.escribir())
        self.datos['imagenes'][1]['origen'] = 'REAL'
        self.datos['imagenes'][0]['origen'] = 'SINTETICO'
        with self.assertRaisesRegex(DatasetInvalido, 'captura REAL'):
            validar(self.escribir())

    def test_poligonos_no_finitos_clase_invalida_y_fuera_de_imagen(self):
        self.escribir()
        for linea in ('0 NaN 0 1 0 1 1', '2 0 0 1 0 1 1', '0 -0.1 0 1 0 1 1', '0 0 0 0 0 0 0', '0 0 0 1 1'):
            (self.raiz/'0.txt').write_text(linea)
            with self.subTest(linea=linea), self.assertRaises(DatasetInvalido):
                validar(self.manifiesto)

    def test_vacio_requiere_confirmacion_no_equivale_a_sin_etiquetar(self):
        (self.raiz/'2.txt').write_text('')
        with self.assertRaises(DatasetInvalido):
            validar(self.escribir())
        self.datos['imagenes'][2]['vacio_confirmado'] = True
        self.assertTrue(validar(self.escribir())['advertencias'])

    def test_no_hay_acceso_a_rutas_externas(self):
        self.datos['imagenes'][0]['archivo'] = '../externa.png'
        with self.assertRaises(DatasetInvalido):
            validar(self.escribir())

    def test_se_exigen_las_tres_particiones_independientes(self):
        self.datos['imagenes'].pop()
        with self.assertRaisesRegex(DatasetInvalido, 'test'):
            validar(self.escribir())

    def test_no_acepta_clases_ajenas_ni_version_booleana(self):
        original = deepcopy(self.datos)
        for cambios in (dict(clases=['persona']), dict(schema_version=True), dict(clases=['arroz','arroz'])):
            self.datos = dict(original, **cambios)
            with self.assertRaises(DatasetInvalido):
                validar(self.escribir())
