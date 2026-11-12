from decimal import Decimal

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

    def test_demostracion_retirada_para_todos_los_roles(self):
        url = '/historico/demostracion/'
        self.assertEqual(self.client.get(url).status_code, 404)
        for usuario in self.usuarios.values():
            self.client.force_login(usuario)
            for metodo in (self.client.get, self.client.post):
                self.assertEqual(metodo(url).status_code, 404)
        self.assertEqual(Servicio.objects.count(), 0)
        self.assertEqual(FotografiaServicio.objects.count(), 0)

    def test_navegacion_operativa_sin_demostracion_ni_prototipo(self):
        for rol in ('Cocina', 'Administración'):
            self.client.force_login(self.usuarios[rol])
            for url in (reverse('historico:lista'), reverse('recomendaciones:lista')):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 200 if rol == 'Administración' else 403)
                self.assertNotContains(respuesta, '/historico/demostracion/', status_code=respuesta.status_code)
                self.assertNotContains(respuesta, '/recomendaciones/demostracion/', status_code=respuesta.status_code)
                self.assertNotContains(respuesta, 'Prototipo académico', status_code=respuesta.status_code)
