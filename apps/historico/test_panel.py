from datetime import datetime
from decimal import Decimal

from django.urls import reverse

from apps.catalogo.models import TipoPorcion

from .services import consultar_panel
from .test_dominio_historico import BaseHistorico, ZONA

CONTEXTO = dict(sede='principal', modalidad='mesa', lote_preparacion='qa-lote')


def fecha(dia, hora=12):
    return datetime(2026, 10, dia, hora, tzinfo=ZONA)


class PanelHistoricoTests(BaseHistorico):
    def test_agrega_antes_de_paginar_y_pondera_por_registro(self):
        for _ in range(30):
            self.caso(0, fecha=fecha(5), contexto=CONTEXTO)
        self.caso(93, fecha=fecha(19), contexto=CONTEXTO)
        self.caso(100, fecha=fecha(19), contexto=CONTEXTO, origen='SIMULADO')
        self.client.force_login(self.admin)
        url = reverse('historico:lista')
        filtros = dict(componente='arroz', desde='2026-10-05', hasta='2026-10-25')
        primera = self.client.get(url, filtros)
        segunda = self.client.get(url, {**filtros, 'page': 2})
        self.assertEqual(primera.status_code, 200)
        self.assertEqual(len(primera.context['datos']['filas']), 30)
        self.assertEqual(len(segunda.context['datos']['filas']), 1)
        panel = primera.context['panel']
        self.assertEqual(panel, segunda.context['panel'])
        self.assertEqual(panel['grupo']['indicadores']['intensidad'], Decimal(3))
        self.assertEqual(panel['grupo']['indicadores']['n'], 31)
        self.assertEqual([(s['n'], s['intensidad']) for s in panel['semanas']], [(30, 0), (0, None), (1, 93)])
        self.assertContains(primera, 'Sin evidencia')
        self.assertContains(primera, '<details class="eva-week-details" open>')
        self.assertContains(primera, '<th scope="col">Intensidad</th>')
        self.assertContains(primera, '<td>0,00 %</td>')

    def test_semana_final_vacia_y_limites_parciales(self):
        self.caso(0, fecha=fecha(7), contexto=CONTEXTO)
        self.caso(20, fecha=fecha(12), contexto=CONTEXTO)
        _, panel = consultar_panel(dict(componente='arroz', desde='2026-10-07', hasta='2026-10-20'))
        self.assertEqual([s['parcial'] for s in panel['semanas']], [True, False, True])
        self.assertEqual([(s['inicio'].day, s['fin'].day) for s in panel['semanas']], [(7, 11), (12, 18), (19, 20)])
        self.assertEqual(panel['semanas'][0]['intensidad'], 0)
        self.assertEqual(panel['ultima']['n'], 0)
        self.assertIsNone(panel['ultima']['intensidad'])

    def test_perfiles_solo_varian_la_dimension_elegida(self):
        self.caso(10, contexto=CONTEXTO)
        self.caso(50, contexto=CONTEXTO, plato='arroz_menestra_carne')
        TipoPorcion.objects.create(codigo='reducida', nombre='Reducida')
        self.caso(30, contexto=CONTEXTO, porcion='reducida')
        for cambios in (dict(modelo='otra'), dict(configuracion='otra'), dict(protocolo='otro')):
            self.caso(90, contexto=CONTEXTO, **cambios)
        self.caso(90, fecha=fecha(3, 14), contexto=CONTEXTO)
        self.caso(90)
        filtros = dict(componente='arroz')
        _, sin_grupo = consultar_panel(filtros)
        self.assertIsNone(sin_grupo['grupo'])
        self.assertEqual(len(sin_grupo['opciones']), 8)
        elegido = next(g for g in sin_grupo['opciones'] if g['indicadores']['intensidad'] == 10)
        _, panel = consultar_panel(filtros, grupo=elegido['clave'])
        self.assertEqual(panel['grupo']['indicadores']['n'], 1)
        self.assertEqual([p['intensidad'] for p in panel['perfiles']['platos']], [50, 10])
        self.assertEqual([p['intensidad'] for p in panel['perfiles']['porciones']], [10, 30])
        desconocido = next(g for g in sin_grupo['opciones'] if not g['comparable'])
        _, panel = consultar_panel(filtros, grupo=desconocido['clave'])
        self.assertEqual(panel['grupo']['indicadores']['intensidad'], 90)
        self.assertEqual(panel['semanas'], [])
        self.assertEqual(panel['perfiles'], {})

    def test_sin_evidencia_no_publica_barras(self):
        self.caso(50, decision='RECHAZADO', contexto=CONTEXTO)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('historico:lista'))
        self.assertContains(response, 'Evidencia insuficiente')
        self.assertNotContains(response, '<meter')
        self.assertNotContains(response, 'eva-semanas')
