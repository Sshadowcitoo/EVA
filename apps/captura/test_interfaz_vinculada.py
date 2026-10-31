from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .test_interfaz import FotoForm


class InterfazVinculadaTests(SimpleTestCase):
    def test_solicitud_pendiente_no_anuncia_guardado_y_mutaciones_usan_csrf(self):
        html = render_to_string('captura/vincular_celular.html', {
            'estado': 'PENDIENTE', 'operacion_habilitada': True,
            'crear_url': '/crear/', 'cancelar_url': '/cancelar/',
            'estado_url': '/estado/', 'caduca_en': '2099-01-01T00:00:00Z',
            'csrf_token': 'token-prueba', 'qr_url': '/qr-privado/',
        })
        self.assertIn('Escanear el QR no confirma el guardado', html)
        self.assertEqual(html.count('name="csrfmiddlewaretoken"'), 2)
        self.assertIn('method="post" action="/cancelar/"', html)
        self.assertIn('src="/qr-privado/"', html)

    def test_enlace_terminal_no_ofrece_sobrescribir_foto(self):
        for estado in ('COMPLETADA', 'CANCELADA', 'EXPIRADA'):
            with self.subTest(estado=estado):
                html = render_to_string('captura/captura_vinculada.html', {
                    'estado': estado, 'form': FotoForm(), 'guardar_url': '/guardar/',
                    'operacion_habilitada': True, 'vinculo_vigente': False,
                })
                self.assertNotIn('type="file"', html)
                self.assertNotIn('action="/guardar/"', html)

    def test_vinculo_vigente_reutiliza_formulario_de_captura(self):
        html = render_to_string('captura/captura_vinculada.html', {
            'vinculo_vigente': True, 'operacion_habilitada': True,
            'form': FotoForm(), 'guardar_url': '/guardar/', 'etapa': 'RETORNO',
            'csrf_token': 'token-prueba',
        })
        self.assertIn('enctype="multipart/form-data"', html)
        self.assertIn('action="/guardar/"', html)

    def test_sin_endpoints_no_habilita_crear_enlace(self):
        html = render_to_string('captura/vincular_celular.html', {})
        self.assertIn('disabled>Crear enlace de captura', html)
