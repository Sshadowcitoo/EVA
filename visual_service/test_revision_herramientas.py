"""Controles de dataset/exportación, sin instalar paquetes ni entrenar pesos."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image
from .dataset import DatasetInvalido, validar
from .train import exportar, entrenar


class RevisionHerramientasTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory();self.addCleanup(temp.cleanup);self.raiz=Path(temp.name)
        self.datos=dict(schema_version=1,clases=['arroz','pollo'],imagenes=[])
        for i,particion in enumerate(('train','val','test')):
            Image.new('RGB',(4,4),(i*70,10,30)).save(self.raiz/f'{i}.png')
            (self.raiz/f'{i}.txt').write_text('0 0.1 0.1 0.4 0.1 0.4 0.4\n1 0.6 0.6 0.9 0.6 0.9 0.9\n')
            self.datos['imagenes'].append(dict(archivo=f'{i}.png',etiquetas=f'{i}.txt',particion=particion,grupo=f'preparacion-{i}',origen='REAL'))
        self.manifiesto=self.raiz/'manifiesto.json'

    def escribir(self):
        self.manifiesto.write_text(json.dumps(self.datos));return self.manifiesto

    def test_exportacion_conserva_orden_de_clases_y_etiquetas_originales(self):
        yaml,_=exportar(self.escribir(),self.raiz/'salida')
        self.assertEqual(json.loads(yaml.read_text())['names'],{'0':'arroz','1':'pollo'})
        self.assertEqual((self.raiz/'salida/labels/train/000000.txt').read_bytes(),(self.raiz/'0.txt').read_bytes())
        self.assertEqual((self.raiz/'salida/manifiesto_origen.json').read_bytes(),self.manifiesto.read_bytes())

    def test_train_sin_todas_las_clases_no_crea_destino(self):
        (self.raiz/'0.txt').write_text('0 0.1 0.1 0.4 0.1 0.4 0.4')
        with self.assertRaisesRegex(DatasetInvalido,'Faltan clases'):exportar(self.escribir(),self.raiz/'salida')
        self.assertFalse((self.raiz/'salida').exists())

    def test_val_test_sin_una_clase_informan_limitacion(self):
        (self.raiz/'2.txt').write_text('0 0.1 0.1 0.4 0.1 0.4 0.4')
        datos=validar(self.escribir())
        self.assertIn('test: clases sin anotaciones: pollo',datos['advertencias'])
        self.assertEqual(datos['resumen']['test']['clases'],{'arroz':1})

    def test_ruta_por_enlace_fuera_del_dataset_se_rechaza(self):
        with TemporaryDirectory() as externo:
            foto=Path(externo)/'externa.png';Image.new('RGB',(4,4)).save(foto)
            (self.raiz/'enlace.png').symlink_to(foto)
            self.datos['imagenes'][0]['archivo']='enlace.png'
            with self.assertRaises(DatasetInvalido):validar(self.escribir())

    def test_etiquetas_vacias_exigen_booleano_explicito(self):
        (self.raiz/'2.txt').write_text('')
        self.datos['imagenes'][2]['vacio_confirmado']='true'
        with self.assertRaises(DatasetInvalido):validar(self.escribir())
        self.datos['imagenes'][2]['vacio_confirmado']=True
        self.assertTrue(validar(self.escribir())['advertencias'])

    def test_pesos_ausentes_no_exportan_ni_importan_entrenamiento(self):
        self.escribir()
        with self.assertRaises(DatasetInvalido):entrenar(self.manifiesto,self.raiz/'entrenamiento',self.raiz/'no-existe.pt')
        self.assertFalse((self.raiz/'entrenamiento').exists())
