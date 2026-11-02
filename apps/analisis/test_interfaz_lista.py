from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings
from django.urls import include, path

# Ruta de prueba: permite comprobar el menú sin depender de las vistas reales.
urlpatterns = [
    path("analisis/", include(([path("", lambda request: HttpResponse("ok"), name="lista")], "analisis"))),
]

CASOS = [
    {"bandeja_numero": "EVA-001", "plato_nombre": "Seco de pollo", "porcion_nombre": "Porción mediana",
     "estado": "COMPLETADO", "origen": "REAL", "detalle_url": "/analisis/uno/"},
    {"plato_nombre": "Encebollado", "porcion_nombre": "Porción grande",
     "estado": "TIEMPO_AGOTADO", "origen": "SIMULADO"},
]


class ListaAnalisisTests(SimpleTestCase):
    def test_estados_legibles_y_origen_visible(self):
        html = render_to_string("analisis/lista.html", {"casos": CASOS})
        self.assertIn("Completado", html)
        self.assertIn("Tiempo agotado", html)
        self.assertNotIn("TIEMPO_AGOTADO", html)
        self.assertIn("Simulado", html)
        self.assertIn("Real", html)
        self.assertIn("EVA-001", html)

    def test_accion_solo_si_hay_ruta_de_detalle(self):
        html = render_to_string("analisis/lista.html", {"casos": CASOS})
        self.assertEqual(html.count("Abrir análisis"), 1)
        self.assertIn('href="/analisis/uno/"', html)

    def test_resumen_sin_datos_y_cero_no_se_confunden(self):
        sin_datos = render_to_string("analisis/lista.html", {"casos": CASOS})
        self.assertEqual(sin_datos.count("Sin datos"), 2)
        con_cero = render_to_string(
            "analisis/lista.html",
            {"casos": CASOS, "resumen": {"por_revisar": 0, "no_concluyentes": 1}},
        )
        self.assertIn("0 casos", con_cero)
        self.assertIn("1 caso", con_cero)
        self.assertNotIn("Sin datos", con_cero)

    def test_historial_sin_ruta_no_muestra_enlace_falso(self):
        html = render_to_string("analisis/lista.html", {"casos": CASOS})
        self.assertIn("Pendiente de conexión", html)
        self.assertNotIn("Ver registros", html)
        con_ruta = render_to_string("analisis/lista.html", {"casos": CASOS, "historial_url": "/historial/"})
        self.assertIn('href="/historial/"', con_ruta)

    @override_settings(ROOT_URLCONF=__name__)
    def test_menu_de_cocina_enlaza_pendientes_si_la_ruta_existe(self):
        html = render_to_string("analisis/lista.html", {"casos": [], "puede_cocina": True})
        self.assertIn('href="/analisis/"', html)
        self.assertIn("Pendientes", html)

    def test_lista_vacia_explica_que_no_hay_pares(self):
        html = render_to_string("analisis/lista.html", {"casos": []})
        self.assertIn("No hay análisis disponibles", html)
        self.assertIn("Los pares incompletos no se envían al motor", html)