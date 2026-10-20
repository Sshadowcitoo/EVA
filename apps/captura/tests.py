import uuid

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Servicio


class ServicioModelTests(TestCase):
    def test_dos_servicios_reciben_uuid_distintos_y_fecha_automatica(self):
        inicio = timezone.now()
        primero = Servicio.objects.create(
            plato="arroz_con_pollo", tipo_porcion="regular"
        )
        segundo = Servicio.objects.create(plato="lentejas", tipo_porcion="pequena")
        fin = timezone.now()

        primero.refresh_from_db()
        segundo.refresh_from_db()

        self.assertEqual(Servicio.objects.count(), 2)
        self.assertNotEqual(primero.pk, segundo.pk)
        for servicio in (primero, segundo):
            with self.subTest(servicio=servicio.pk):
                self.assertIsInstance(servicio.pk, uuid.UUID)
                self.assertIsNotNone(servicio.fecha_creacion)
                self.assertGreaterEqual(servicio.fecha_creacion, inicio)
                self.assertLessEqual(servicio.fecha_creacion, fin)


class CapturaViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.nueva_url = reverse("captura:nueva_bandeja")
        self.datos_validos = {
            "plato": "arroz_con_pollo",
            "tipo_porcion": "regular",
        }

    def test_get_muestra_formulario_vacio_sin_crear_servicios(self):
        respuesta = self.client.get(self.nueva_url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.context["form"].is_bound)
        self.assertContains(respuesta, 'name="plato"')
        self.assertContains(respuesta, 'name="tipo_porcion"')
        self.assertEqual(Servicio.objects.count(), 0)

    def test_post_valido_crea_un_servicio_y_redirige_a_su_confirmacion(self):
        respuesta = self.client.post(self.nueva_url, self.datos_validos)

        self.assertEqual(Servicio.objects.count(), 1)
        servicio = Servicio.objects.get()
        self.assertEqual(servicio.plato, self.datos_validos["plato"])
        self.assertEqual(servicio.tipo_porcion, self.datos_validos["tipo_porcion"])
        self.assertRedirects(
            respuesta,
            reverse("captura:confirmacion", kwargs={"pk": servicio.pk}),
            fetch_redirect_response=False,
        )

    def test_post_invalido_muestra_errores_sin_crear_servicios(self):
        casos = [
            ({}, ("plato", "tipo_porcion")),
            ({"tipo_porcion": "regular"}, ("plato",)),
            ({"plato": "arroz_con_pollo"}, ("tipo_porcion",)),
            ({"plato": "inventado", "tipo_porcion": "regular"}, ("plato",)),
            (
                {"plato": "arroz_con_pollo", "tipo_porcion": "inventada"},
                ("tipo_porcion",),
            ),
        ]
        for datos, campos_con_error in casos:
            with self.subTest(datos=datos):
                respuesta = self.client.post(self.nueva_url, datos)

                self.assertEqual(respuesta.status_code, 200)
                formulario = respuesta.context["form"]
                self.assertTrue(formulario.is_bound)
                for campo in campos_con_error:
                    self.assertIn(campo, formulario.errors)
                    for error in formulario.errors[campo]:
                        self.assertContains(respuesta, str(error))
                self.assertEqual(Servicio.objects.count(), 0)

    def test_confirmacion_muestra_servicio_correcto_y_recarga_no_duplica(self):
        servicio = Servicio.objects.create(**self.datos_validos)
        otro = Servicio.objects.create(plato="lentejas", tipo_porcion="grande")
        url = reverse("captura:confirmacion", kwargs={"pk": servicio.pk})

        for visita in range(2):
            with self.subTest(visita=visita):
                respuesta = self.client.get(url)

                self.assertEqual(respuesta.status_code, 200)
                self.assertEqual(respuesta.context["servicio"].pk, servicio.pk)
                self.assertContains(respuesta, str(servicio.pk))
                self.assertContains(respuesta, servicio.get_plato_display())
                self.assertContains(respuesta, servicio.get_tipo_porcion_display())
                self.assertNotContains(respuesta, str(otro.pk))
                self.assertEqual(Servicio.objects.count(), 2)

    def test_uuid_inexistente_devuelve_404_sin_crear_servicios(self):
        url = reverse("captura:confirmacion", kwargs={"pk": uuid.uuid4()})

        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(Servicio.objects.count(), 0)

    def test_uuid_mal_formado_devuelve_404_sin_crear_servicios(self):
        respuesta = self.client.get("/captura/no-es-un-uuid/confirmacion/")

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(Servicio.objects.count(), 0)
