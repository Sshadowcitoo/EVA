import uuid

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from .models import Servicio
from apps.catalogo.models import Plato, TipoPorcion
from apps.catalogo.permissions import REGISTRO, ADMINISTRACION, COCINA


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
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_catalogo_demo", verbosity=0)
        cls.usuario = get_user_model().objects.create_user(username="registro")
        grupo, _ = Group.objects.get_or_create(name=REGISTRO)
        cls.usuario.groups.add(grupo)
        cls.plato = Plato.objects.get(codigo="seco_de_pollo")
        cls.porcion = TipoPorcion.objects.get(codigo="estandar")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.usuario)
        self.nueva_url = reverse("captura:nueva_bandeja")
        self.datos_validos = {
            "plato": self.plato.pk,
            "tipo_porcion": self.porcion.pk,
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
        self.assertEqual(servicio.plato_catalogo, self.plato)
        self.assertEqual(servicio.porcion_catalogo, self.porcion)
        self.assertEqual(servicio.creado_por, self.usuario)
        self.assertSetEqual(
            set(servicio.composicion.values_list("componente_codigo", flat=True)),
            {"arroz", "pollo", "maduro"},
        )
        self.assertRedirects(
            respuesta,
            reverse("captura:confirmacion", kwargs={"pk": servicio.pk}),
            fetch_redirect_response=False,
        )

    def test_post_invalido_muestra_errores_sin_crear_servicios(self):
        casos = [
            ({}, ("plato", "tipo_porcion")),
            ({"tipo_porcion": self.porcion.pk}, ("plato",)),
            ({"plato": self.plato.pk}, ("tipo_porcion",)),
            ({"plato": "inventado", "tipo_porcion": self.porcion.pk}, ("plato",)),
            (
                {"plato": self.plato.pk, "tipo_porcion": "inventada"},
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
        servicio = Servicio.registrar(
            plato=self.plato, porcion=self.porcion, usuario=self.usuario
        )
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

    def test_catalogo_inactivo_no_se_muestra_ni_se_acepta(self):
        for elemento in (self.plato, self.porcion):
            with self.subTest(elemento=type(elemento).__name__):
                elemento.activo = False
                elemento.save(update_fields=["activo"])
                response = self.client.get(self.nueva_url)
                campo = "plato" if elemento is self.plato else "tipo_porcion"
                self.assertFalse(response.context["form"].fields[campo].queryset.filter(pk=elemento.pk).exists())
                response = self.client.post(self.nueva_url, self.datos_validos)
                self.assertEqual(response.status_code, 200)
                self.assertIn(campo, response.context["form"].errors)
                self.assertEqual(Servicio.objects.count(), 0)
                elemento.activo = True
                elemento.save(update_fields=["activo"])

    def test_confirmacion_ajena_o_sin_creador_devuelve_404(self):
        otro_usuario = get_user_model().objects.create_user(username="otro_registro")
        ajeno = Servicio.registrar(plato=self.plato, porcion=self.porcion, usuario=otro_usuario)
        historico = Servicio.objects.create(plato="lentejas", tipo_porcion="grande")
        for servicio in (ajeno, historico):
            with self.subTest(servicio=servicio.pk):
                response = self.client.get(reverse("captura:confirmacion", kwargs={"pk": servicio.pk}))
                self.assertEqual(response.status_code, 404)

    def test_captura_exige_sesion_y_rol_registro_en_get_y_post(self):
        self.client.logout()
        for metodo in ("get", "post"):
            response = getattr(self.client, metodo)(self.nueva_url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith(reverse("cuentas:login")))
        for rol in (COCINA, ADMINISTRACION):
            usuario = get_user_model().objects.create_user(username=rol)
            grupo, _ = Group.objects.get_or_create(name=rol)
            usuario.groups.add(grupo)
            self.client.force_login(usuario)
            for metodo in ("get", "post"):
                with self.subTest(rol=rol, metodo=metodo):
                    response = getattr(self.client, metodo)(self.nueva_url, self.datos_validos)
                    self.assertEqual(response.status_code, 403)
        self.assertEqual(Servicio.objects.count(), 0)
