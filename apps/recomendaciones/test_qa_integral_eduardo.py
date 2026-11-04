"""Regresiones dirigidas a E18–E20/E25 de la guía QA del 04/11.

Solo base temporal y escenarios didácticos; no crea/aprueba evidencia operativa.
"""
from copy import deepcopy
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.analisis.services import evaluar_componente
from apps.historico.indicadores import calcular
from .demo import preparar


class QAIntegralEduardoTests(TestCase):
    def setUp(self):
        self.cocina = get_user_model().objects.create_user(username="QA-EDUARDO-20261104-LOCAL")
        self.cocina.groups.add(Group.objects.get_or_create(name="Cocina")[0])

    def test_E02_credenciales_vacias_inexistentes_e_incorrectas_no_abren_sesion(self):
        for datos in ({}, {"username": "QA-INEXISTENTE", "password": "incorrecta"},
                      {"username": self.cocina.username, "password": "incorrecta"}):
            with self.subTest(usuario=datos.get("username", "vacio")):
                respuesta = self.client.post("/cuentas/login/", datos)
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.context["form"].errors)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_E19_cuatro_cifras_exactas_y_categorias_de_la_guia(self):
        casos = [
            ("mantener", 10, Decimal(4), Decimal(0), "MANTENER"),
            ("porcion", 10, Decimal(30), Decimal(100), "REVISAR_PORCION"),
            ("prueba", 10, Decimal(12), Decimal(20), "PRUEBA_CONTROLADA"),
            ("insuficiente", 2, Decimal(35), Decimal(100), None),
        ]
        for clave, n, media, prevalencia, categoria in casos:
            with self.subTest(escenario=clave):
                datos = preparar(clave)
                self.assertEqual(datos["indicadores"]["n"], n)
                self.assertEqual(datos["indicadores"]["intensidad"], media)
                self.assertEqual(datos["indicadores"]["prevalencia"], prevalencia)
                self.assertEqual(datos["categoria"], categoria)
                self.assertEqual(datos["suficiente"], categoria is not None)

    def test_E18_get_de_todos_los_escenarios_sin_escritura_SQL(self):
        self.client.force_login(self.cocina)
        criterios = deepcopy(settings.EVA_ANALISIS_CRITERIOS)
        with CaptureQueriesContext(connection) as consultas:
            for escenario in ("mantener", "porcion", "prueba", "insuficiente"):
                respuesta = self.client.get(reverse("recomendaciones:demo"), {"escenario": escenario})
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "Datos de ejemplo")
                self.assertContains(respuesta, "no son predicciones de la IA")
                self.assertIn("no-store", respuesta["Cache-Control"])
        escrituras = [q["sql"].split()[0].upper() for q in consultas
                      if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "REPLACE"))]
        self.assertEqual(escrituras, [])
        self.assertEqual(settings.EVA_ANALISIS_CRITERIOS, criterios)

    def test_E20_presencia_estrictamente_mayor_que_diez_y_no_deteccion_nula(self):
        datos = calcular([Decimal(0), Decimal(10), Decimal("10.01")],
                         {"t": Decimal(10), "version_criterio": "QA-hipotetico"})
        self.assertEqual(datos["prevalencia"], Decimal(100) / 3)
        sin = evaluar_componente(area_inicial=100, area_residual=None,
                                confianza=.9, umbral_confianza=.8,
                                comparable=True, oculto=False)
        self.assertIsNone(sin["porcentaje"])
        self.assertEqual(sin["motivo"], "SIN_DETECCION")
        cero = evaluar_componente(area_inicial=100, area_residual=0,
                                 confianza=.9, umbral_confianza=.8,
                                 comparable=True, oculto=False)
        self.assertEqual(cero["porcentaje"], Decimal(0))

    def test_E25_demo_y_foto_denegadas_anonimo_registro_con_get_y_post(self):
        rutas = [reverse("recomendaciones:demo"), reverse("recomendaciones:demo_foto")]
        for ruta in rutas:
            for metodo in ("get", "post"):
                self.assertEqual(getattr(self.client, metodo)(ruta).status_code, 302)
        usuario = get_user_model().objects.create_user(username="QA-REGISTRO-20261104-LOCAL")
        usuario.groups.add(Group.objects.get_or_create(name="Registro")[0])
        self.client.force_login(usuario)
        for ruta in rutas:
            for metodo in ("get", "post"):
                with self.subTest(ruta=ruta, metodo=metodo):
                    self.assertEqual(getattr(self.client, metodo)(ruta).status_code, 403)
