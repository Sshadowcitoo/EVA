from django.template.loader import render_to_string
from django.test import SimpleTestCase

CASO = {"plato_nombre": "Seco de pollo", "porcion_nombre": "Porción mediana", "origen": "REAL"}
RESULTADOS = [
    {"componente": "Arroz", "porcentaje_texto": "24 %", "confianza_texto": "91 %", "estado": "CONCLUYENTE"},
    {"componente": "Ensalada", "estado": "NO_CONCLUYENTE", "motivo": "OCULTACION"},
]


def detalle(**contexto):
    return render_to_string("analisis/detalle.html", contexto)


class DetalleAnalisisTests(SimpleTestCase):
    def test_en_proceso_no_muestra_cifras_y_consulta_el_estado(self):
        html = detalle(caso={**CASO, "estado": "EN_PROCESO"}, estado_url="/analisis/1/estado/", resultados=RESULTADOS)
        self.assertIn("Analizando fotografías", html)
        self.assertIn("Aún no hay resultados", html)
        self.assertIn('data-estado-url="/analisis/1/estado/"', html)
        self.assertIn("js/analisis.js", html)
        self.assertNotIn("24 %", html)
        self.assertNotIn("Hallazgos por componente", html)

    def test_en_proceso_sin_ruta_de_estado_no_carga_el_script(self):
        html = detalle(caso={**CASO, "estado": "PENDIENTE"})
        self.assertNotIn("data-estado-url", html)
        self.assertNotIn("js/analisis.js", html)
        self.assertIn("Recarga la página", html)

    def test_fallo_no_muestra_porcentaje_y_ofrece_reintento_solo_con_ruta(self):
        html = detalle(caso={**CASO, "estado": "FALLIDO"}, reintentar_url="/analisis/1/reintentar/", resultados=RESULTADOS)
        self.assertIn("Fallo técnico del análisis", html)
        self.assertIn('action="/analisis/1/reintentar/"', html)
        self.assertNotIn("24 %", html)
        sin_ruta = detalle(caso={**CASO, "estado": "FALLIDO"})
        self.assertNotIn("Reintentar análisis", sin_ruta)
        self.assertNotIn('action=""', sin_ruta)

    def test_tiempo_agotado_tiene_su_propio_titulo(self):
        html = detalle(caso={**CASO, "estado": "TIEMPO_AGOTADO"})
        self.assertIn("El análisis tardó demasiado", html)
        self.assertNotIn("TIEMPO_AGOTADO", html)

    def test_completado_muestra_leyenda_y_no_concluyente_con_motivo(self):
        html = detalle(caso={**CASO, "estado": "COMPLETADO"}, resultados=RESULTADOS)
        self.assertIn("24 %", html)
        self.assertIn("91 %", html)
        self.assertIn("leyenda-punto", html)
        self.assertIn("No concluyente", html)
        self.assertIn("El componente está oculto", html)
        self.assertIn("OCULTACION", html)
        self.assertNotIn("0 %", html.replace("24 %", "").replace("91 %", ""))

    def test_reintento_no_aparece_si_el_analisis_termino_bien(self):
        html = detalle(caso={**CASO, "estado": "COMPLETADO"}, resultados=RESULTADOS, reintentar_url="/x/")
        self.assertNotIn("Reintentar análisis", html)

    def test_mascaras_se_dibujan_sobre_su_foto(self):
        html = detalle(
            caso={**CASO, "estado": "COMPLETADO"}, resultados=RESULTADOS,
            foto_servido_url="/f/servido.jpg", foto_retorno_url="/f/retorno.jpg",
            mascaras=[{"url": "/m/arroz-servido.png", "componente": "Arroz", "etapa": "SERVIDO"}],
        )
        self.assertEqual(html.count('class="analisis-mascara"'), 1)
        self.assertIn("Máscara de Arroz sobre el servido", html)
        self.assertNotIn("sobre el retorno", html)

    def test_simulado_intento_y_duracion_son_visibles(self):
        html = detalle(caso={**CASO, "origen": "SIMULADO", "estado": "COMPLETADO", "intento_numero": 2, "duracion_texto": "12 s"})
        self.assertIn("SIMULADO", html)
        self.assertIn("Intento 2", html)
        self.assertIn("Duración 12 s", html)

    def test_sin_estado_ni_resultados_explica_que_no_hay_datos(self):
        html = detalle(caso=CASO)
        self.assertIn("Aún no hay resultados aceptados del motor", html)
        self.assertNotIn("Reintentar", html)