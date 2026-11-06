from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.captura.models import Servicio, FotografiaServicio
from .demo import construir


class DatosDemostracionTests(SimpleTestCase):
    def test_datos_en_memoria_y_grupos_coherentes(self):
        datos, panel = construir()
        self.assertTrue(datos["solo_pruebas"])
        self.assertEqual(datos["resumen"]["candidatos"], 14)
        self.assertEqual(panel["grupo"]["indicadores"]["n"], 8)
        self.assertEqual(panel["grupo"]["indicadores"]["intensidad"], Decimal(35))
        self.assertEqual([s["n"] for s in panel["semanas"]], [2, 2, 0, 4])
        self.assertIsNone(panel["semanas"][2]["intensidad"])
        self.assertTrue(all(f["origen"] == "SIMULADO" for f in datos["filas"]))
        self.assertTrue(any(f["porcentaje_visual"] == 0 for f in datos["filas"]))
        self.assertEqual({p["nombre"] for p in panel["perfiles"]["componentes"]}, {"Arroz", "Pollo"})

    def test_sin_evidencia_y_copias_independientes(self):
        vacio, panel = construir("sin_aptos")
        self.assertEqual(vacio["resumen"]["aptos"], 0)
        self.assertEqual(panel["semanas"], [])
        self.assertIsNone(panel["grupo"])
        primero, _ = construir()
        primero["filas"].clear()
        self.assertTrue(construir()[0]["filas"])


class DemostracionHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuarios = {}
        for rol in ("Registro", "Cocina", "Administración"):
            u = get_user_model().objects.create_user(username=rol)
            u.groups.add(Group.objects.get_or_create(name=rol)[0])
            cls.usuarios[rol] = u

    def test_permisos_y_metodo(self):
        url = reverse("historico:demostracion")
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.usuarios["Registro"])
        self.assertEqual(self.client.get(url).status_code, 403)
        for rol in ("Cocina", "Administración"):
            self.client.force_login(self.usuarios[rol])
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.post(url).status_code, 405)

    def test_no_usa_selector_real_ni_escribe_servicios_o_fotos(self):
        self.client.force_login(self.usuarios["Administración"])
        with patch("apps.historico.selectors.seleccionar", side_effect=AssertionError("No consultar datos reales")):
            respuesta = self.client.get(reverse("historico:demostracion"))
        self.assertContains(respuesta, "Datos de demostración")
        self.assertContains(respuesta, "Sin validez operativa")
        self.assertContains(respuesta, 'id="eva-semanas"')
        self.assertEqual(respuesta.context["panel"]["grupo"]["indicadores"]["intensidad"], 35)
        self.assertEqual(Servicio.objects.count(), 0)
        self.assertEqual(FotografiaServicio.objects.count(), 0)

    def test_entrada_invalida_y_escenario_sin_evidencia(self):
        self.client.force_login(self.usuarios["Cocina"])
        url = reverse("historico:demostracion")
        for datos in ({"escenario": "desconocido"}, {"page": "²"}, {"page": "0"}):
            self.assertEqual(self.client.get(url, datos).status_code, 400)
        respuesta = self.client.get(url, {"escenario": "sin_aptos"})
        self.assertContains(respuesta, "Evidencia insuficiente")
        self.assertNotContains(respuesta, '<svg')
        self.assertNotContains(respuesta, '<meter')
