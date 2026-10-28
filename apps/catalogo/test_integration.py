"""Recorridos HTTP reales del bloque integrado; no sustituyen vistas por dobles."""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from apps.captura.models import Servicio
from .models import Componente, Plato, TipoPorcion
from .permissions import ADMINISTRACION, COCINA, REGISTRO


class BloqueIntegradoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_catalogo_demo", verbosity=0)
        cls.clave = uuid.uuid4().hex
        cls.usuarios = {}
        for nombre, roles in (
            ("registro", (REGISTRO,)),
            ("administracion", (ADMINISTRACION,)),
            ("cocina", (COCINA,)),
            ("mixto", (REGISTRO, ADMINISTRACION, COCINA)),
            ("sin_rol", ()),
        ):
            user = get_user_model().objects.create_user(username=nombre, password=cls.clave)
            for rol in roles:
                grupo, _ = Group.objects.get_or_create(name=rol)
                user.groups.add(grupo)
            cls.usuarios[nombre] = user

    def test_login_redirige_a_pantalla_real_permitida_por_rol(self):
        for nombre, destino in (
            ("registro", "captura:nueva_bandeja"),
            ("administracion", "catalogo:platos"),
            ("cocina", "cuentas:cocina_pendiente"),
            ("mixto", "captura:nueva_bandeja"),
        ):
            with self.subTest(rol=nombre):
                self.client.logout()
                response = self.client.post(reverse("cuentas:login"), {
                    "username": nombre, "password": self.clave,
                })
                self.assertRedirects(response, reverse(destino))

    def test_login_rechaza_clave_incorrecta_y_usuario_sin_rol(self):
        for nombre, clave in (("registro", "incorrecta"), ("sin_rol", self.clave)):
            with self.subTest(usuario=nombre):
                response = self.client.post(reverse("cuentas:login"), {
                    "username": nombre, "password": clave,
                })
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_conserva_next_local_y_no_admite_redireccion_externa(self):
        login = reverse("cuentas:login")
        destino = reverse("catalogo:componentes")
        response = self.client.get(login, {"next": destino})
        self.assertContains(response, f'value="{destino}"')
        for next_url, esperado in ((destino, destino), ("https://example.invalid/", reverse("catalogo:platos"))):
            self.client.logout()
            response = self.client.post(login, {
                "username": "administracion", "password": self.clave, "next": next_url,
            })
            self.assertRedirects(response, esperado)

    def test_logout_solo_post_con_csrf_y_sesion_se_cierra(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuarios["registro"])
        logout = reverse("cuentas:logout")
        self.assertEqual(client.get(logout).status_code, 405)
        self.assertEqual(client.post(logout).status_code, 403)
        self.assertIn("_auth_user_id", client.session)
        client.get(reverse("captura:nueva_bandeja"))
        token = client.cookies["csrftoken"].value
        self.assertRedirects(client.post(logout, {"csrfmiddlewaretoken": token}), reverse("cuentas:login"))
        self.assertNotIn("_auth_user_id", client.session)

    def test_catalogo_real_muestra_datos_y_acciones(self):
        self.client.force_login(self.usuarios["administracion"])
        for ruta, etiqueta, crear in (
            ("catalogo:platos", "Seco de pollo", "catalogo:plato_crear"),
            ("catalogo:componentes", "Arroz", "catalogo:componente_crear"),
            ("catalogo:porciones", "Estándar", "catalogo:porcion_crear"),
        ):
            with self.subTest(ruta=ruta):
                response = self.client.get(reverse(ruta))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, etiqueta)
                self.assertContains(response, reverse(crear))
                self.assertContains(response, "Desactivar")
                self.assertNotContains(response, 'href="/captura/nueva/"')
                self.assertEqual(self.client.get(reverse(crear)).status_code, 200)

    def test_crud_componentes_y_porciones_con_codigo_estable(self):
        self.client.force_login(self.usuarios["administracion"])
        for modelo, prefijo, lista in (
            (Componente, "componente", "componentes"),
            (TipoPorcion, "porcion", "porciones"),
        ):
            with self.subTest(modelo=modelo.__name__):
                response = self.client.post(reverse(f"catalogo:{prefijo}_crear"), {
                    "codigo": "nuevo", "nombre": "Nuevo elemento",
                })
                self.assertRedirects(response, reverse(f"catalogo:{lista}"))
                objeto = modelo.objects.get(codigo="nuevo")
                editar = reverse(f"catalogo:{prefijo}_editar", args=[objeto.pk])
                self.assertEqual(self.client.get(editar).status_code, 200)
                self.assertRedirects(self.client.post(editar, {"codigo": "cambiado", "nombre": "Editado"}), reverse(f"catalogo:{lista}"))
                objeto.refresh_from_db()
                self.assertEqual(objeto.codigo, "nuevo")
                self.assertEqual(objeto.nombre, "Editado")
                estado = reverse(f"catalogo:{prefijo}_estado", args=[objeto.pk])
                self.assertEqual(self.client.get(estado).status_code, 405)
                self.assertRedirects(self.client.post(estado), reverse(f"catalogo:{lista}"))
                objeto.refresh_from_db()
                self.assertFalse(objeto.activo)
                self.assertRedirects(self.client.post(estado), reverse(f"catalogo:{lista}"))
                objeto.refresh_from_db()
                self.assertTrue(objeto.activo)

    def test_editar_y_desactivar_plato_conserva_historial(self):
        self.client.force_login(self.usuarios["administracion"])
        plato = Plato.objects.get(codigo="seco_de_pollo")
        servicio = Servicio.registrar(plato=plato, porcion=TipoPorcion.objects.get(codigo="estandar"), usuario=self.usuarios["registro"])
        response = self.client.post(reverse("catalogo:plato_editar", args=[plato.pk]), {
            "codigo": "codigo_manipulado", "nombre": "Seco actualizado",
            "composicion": list(Componente.objects.filter(codigo__in=["arroz", "pollo"]).values_list("pk", flat=True)),
        })
        self.assertRedirects(response, reverse("catalogo:platos"))
        plato.refresh_from_db()
        servicio.refresh_from_db()
        self.assertEqual(plato.codigo, "seco_de_pollo")
        self.assertEqual(servicio.get_plato_display(), "Seco de pollo")
        self.assertSetEqual(set(servicio.composicion.values_list("componente_codigo", flat=True)), {"arroz", "pollo", "maduro"})
        self.assertFalse(plato.relaciones.get(componente__codigo="maduro").activo)
        self.assertRedirects(self.client.post(reverse("catalogo:plato_estado", args=[plato.pk])), reverse("catalogo:platos"))
        self.assertTrue(Servicio.objects.filter(pk=servicio.pk).exists())

    def test_crear_plato_y_duplicado_no_deja_relaciones_parciales(self):
        self.client.force_login(self.usuarios["administracion"])
        data = {"codigo": "plato_prueba", "nombre": "Plato de prueba", "composicion": [Componente.objects.get(codigo="arroz").pk]}
        url = reverse("catalogo:plato_crear")
        self.assertRedirects(self.client.post(url, data), reverse("catalogo:platos"))
        plato = Plato.objects.get(codigo="plato_prueba")
        self.assertEqual(plato.relaciones.count(), 1)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("codigo", response.context["form"].errors)
        self.assertEqual(Plato.objects.filter(codigo="plato_prueba").count(), 1)
        self.assertEqual(plato.relaciones.count(), 1)

    def test_permisos_reales_de_catalogo_get_post_y_cocina(self):
        plato = Plato.objects.get(codigo="seco_de_pollo")
        for nombre in ("registro", "cocina", "sin_rol"):
            self.client.force_login(self.usuarios[nombre])
            for ruta in (reverse("catalogo:platos"), reverse("catalogo:plato_crear"), reverse("catalogo:plato_estado", args=[plato.pk])):
                for metodo in ("get", "post"):
                    with self.subTest(usuario=nombre, ruta=ruta, metodo=metodo):
                        self.assertEqual(getattr(self.client, metodo)(ruta).status_code, 403)
        plato.refresh_from_db()
        self.assertTrue(plato.activo)
        self.client.force_login(self.usuarios["cocina"])
        response = self.client.get(reverse("cuentas:cocina_pendiente"))
        self.assertContains(response, "Funciones de Cocina pendientes")
        self.assertNotContains(response, 'href="/captura/nueva/"')
        self.client.force_login(self.usuarios["registro"])
        self.assertEqual(self.client.get(reverse("cuentas:cocina_pendiente")).status_code, 403)

    def test_catalogo_rechaza_cambio_sin_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuarios["administracion"])
        plato = Plato.objects.get(codigo="seco_de_pollo")
        self.assertEqual(client.post(reverse("catalogo:plato_estado", args=[plato.pk])).status_code, 403)
        plato.refresh_from_db()
        self.assertTrue(plato.activo)
