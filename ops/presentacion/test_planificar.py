from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import unittest

from .planificar import construir


class PlanPresentacionTests(unittest.TestCase):
    def test_identidad_reproducible_sin_reclasificar_origen(self):
        a = construir('expo-01')
        self.assertEqual(a, construir('expo-01'))
        ids = {s['id'] for s in a['servicios']}
        self.assertEqual(len(ids), 288)
        self.assertTrue(ids.isdisjoint(s['id'] for s in construir('expo-02')['servicios']))
        self.assertTrue(all(s['origen'] == 'SIMULADO' for s in a['servicios']))

    def test_bandejas_sin_superposicion_y_franja_constante(self):
        fin = {}
        for s in construir('expo-01')['servicios']:
            servido = datetime.fromisoformat(s['servido'])
            retorno = datetime.fromisoformat(s['retorno'])
            self.assertLess(servido, retorno)
            self.assertEqual(servido.hour, 12)
            self.assertGreaterEqual(servido, fin.get(s['bandeja'], servido))
            fin[s['bandeja']] = retorno

    def test_cobertura_periodos_lotes_y_perfiles_planeados(self):
        ruta = Path(__file__).resolve().parents[1] / 'analisis/criterios_piloto.propuesta.json'
        perfil = json.loads(ruta.read_text(encoding='utf-8'))
        self.assertFalse(perfil['recomendaciones']['aprobada'])
        reglas = perfil['recomendaciones']['reglas']
        grupos = defaultdict(list)
        for s in construir('expo-01')['servicios']:
            grupos[s['plato'], s['porcion']].append(s)
        self.assertEqual(len(grupos), 6)
        categorias = set()
        for filas in grupos.values():
            for periodo in (filas[:24], filas[24:]):
                aptos = [s for s in periodo if s['mediciones_sinteticas']]
                dias = Counter(s['servido'][:10] for s in aptos)
                self.assertGreaterEqual(sum(n >= reglas['muestra_minima'] for n in dias.values()), reglas['periodos_minimos'])
                self.assertGreaterEqual(len({s['lote_preparacion'] for s in aptos}), reglas['lotes_minimos'])
                self.assertGreaterEqual(100 * Decimal(len(aptos)) / len(periodo), reglas['cobertura_minima'])
                # Componente principal del grupo. Los otros se conservan separados.
                valores = [next(iter(s['mediciones_sinteticas'].values()))['area_retorno'] for s in aptos]
                intensidad = Decimal(sum(valores)) / len(valores)
                prevalencia = Decimal(100 * sum(v > reglas['presencia_t'] for v in valores)) / len(valores)
                categorias.add(next(r['categoria'] for r in reglas['categorias'] if
                    r['intensidad_desde'] <= intensidad <= r['intensidad_hasta'] and
                    r['prevalencia_desde'] <= prevalencia <= r['prevalencia_hasta']))
        self.assertEqual(categorias, {'MANTENER', 'REVISAR_PORCION', 'PRUEBA_CONTROLADA'})
