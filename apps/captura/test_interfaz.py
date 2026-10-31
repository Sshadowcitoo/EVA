from django import forms
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class FotoForm(forms.Form):
    fotografia = forms.FileField(label="Fotografía")


class InterfazCapturaTests(SimpleTestCase):
    def test_foto_con_endpoint_tiene_csrf_multipart_y_contexto_escapado(self):
        html = render_to_string("captura/fotografia.html", {
            "form": FotoForm(), "guardar_url": "/captura/prueba/",
            "operacion_habilitada": True, "etapa": "RETORNO",
            "plato_nombre": "<script>malicioso</script>", "csrf_token": "token-prueba",
        })
        self.assertIn('enctype="multipart/form-data"', html)
        self.assertIn('name="csrfmiddlewaretoken"', html)
        self.assertIn('action="/captura/prueba/"', html)
        self.assertIn('&lt;script&gt;malicioso&lt;/script&gt;', html)
        self.assertNotIn('<script>malicioso</script>', html)

    def test_sin_contrato_no_habilita_guardado(self):
        html = render_to_string("captura/fotografia.html", {"etapa": "SERVIDO"})
        self.assertIn('data-photo-submit disabled', html)
        self.assertIn('aún no está disponible', html)

    def test_estado_no_confunde_par_completo_con_analisis(self):
        html = render_to_string("captura/estado_servicio.html", {"estado": "PAR_COMPLETO"})
        self.assertIn('etapas posteriores', html)
        pendiente = render_to_string("captura/estado_servicio.html", {})
        self.assertNotIn('Par de fotografías completo', pendiente)

    def test_busqueda_no_muta_y_confirmacion_usa_post(self):
        html = render_to_string("captura/buscar_bandeja.html", {
            "operacion_habilitada": True, "buscar_url": "/buscar/",
            "bandeja": {"numero": "001"}, "confirmar_url": "/confirmar/",
            "form": FotoForm(), "csrf_token": "token-prueba",
        })
        self.assertIn('method="get"', html)
        self.assertIn('method="post" action="/confirmar/"', html)

    def test_lector_solo_se_habilita_con_contrato_y_js_local(self):
        html = render_to_string("captura/buscar_bandeja.html", {"lector_habilitado": True})
        self.assertIn('name="etiqueta"', html)
        self.assertIn('/static/vendor/jsqr/jsQR.js', html)
        self.assertNotIn('https://', html)
        sin_lector = render_to_string("captura/buscar_bandeja.html", {})
        self.assertNotIn('name="etiqueta"', sin_lector)
