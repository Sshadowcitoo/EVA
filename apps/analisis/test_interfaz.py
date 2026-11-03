from django.template.loader import render_to_string
from django.test import SimpleTestCase


class InterfazAnalisisTests(SimpleTestCase):
    def test_sin_resultado_no_muestra_cero_ni_accion_falsa(self):
        html = render_to_string("analisis/detalle.html", {"caso": {"estado": "PENDIENTE", "plato_nombre": "Seco de pollo"}})
        self.assertIn("Aún no hay resultados", html)
        self.assertNotIn('action=""', html)
        self.assertNotIn("0 %", html)

    def test_simulado_y_no_concluyente_explicitos(self):
        html = render_to_string("analisis/detalle.html", {"caso": {"origen": "SIMULADO"},
            "resultados": [{"componente": "Pescado", "motivo": "OCULTACION"}]})
        self.assertIn("SIMULADO", html)
        self.assertIn("No concluyente", html)
        self.assertIn("OCULTACION", html)

    def test_lista_vacia_es_estado_legible(self):
        self.assertIn("No hay análisis disponibles", render_to_string("analisis/lista.html", {}))
