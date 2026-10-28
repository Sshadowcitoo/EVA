"""Pruebas complementarias al contrato publicado por Isaac en 80f90d6.

Requieren sus modelos, migraciones y comando de carga, y catalogo registrado.
No sustituyen ni duplican la suite test_models.py publicada por Isaac.
"""

from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth.models import Group
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.urls import path, reverse

from apps.captura.models import Servicio, ServicioComponente
from apps.catalogo.models import Componente, Plato, PlatoComponente, TipoPorcion
from apps.catalogo.permissions import ADMINISTRACION, REGISTRO, roles_required


# Endpoints exclusivos de pruebas: no sustituyen las rutas pendientes de Lino.
@roles_required(ADMINISTRACION)
def catalogo_protegido_prueba(request):
    return HttpResponse("Administración autorizada")


@roles_required(REGISTRO)
def captura_protegida_prueba(request):
    return HttpResponse("Registro autorizado")


urlpatterns = [
    path("cuentas/login/", LoginView.as_view(template_name="login_prueba.html"), name="login_prueba"),
    path("cuentas/logout/", LogoutView.as_view(next_page="/cuentas/login/"), name="logout_prueba"),
    path("catalogo/", catalogo_protegido_prueba, name="catalogo_prueba"),
    path("captura/", captura_protegida_prueba, name="captura_prueba"),
]


@override_settings(
    ROOT_URLCONF=__name__,
    LOGIN_URL="/cuentas/login/",
    LOGIN_REDIRECT_URL="/captura/",
    TEMPLATES=[{
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "OPTIONS": {"loaders": [("django.template.loaders.locmem.Loader", {
            "login_prueba.html": '<form method="post">{% csrf_token %}{{ form.as_p }}</form>',
        })]},
    }],
)
class SesionesPermisosContratoTests(TestCase):
    """Contrato aislado: Django auth y helpers César; no vistas del producto."""

    def setUp(self):
        self.usuario = get_user_model().objects.create_user(username="operador_sesion")
        # Credencial efímera generada solo en la base de pruebas.
        self.clave = uuid.uuid4().hex
        self.usuario.set_password(self.clave)
        self.usuario.save()
        self.registro, _ = Group.objects.get_or_create(name=REGISTRO)
        self.admin, _ = Group.objects.get_or_create(name=ADMINISTRACION)

    def test_login_valido_crea_sesion(self):
        respuesta = self.client.post(reverse("login_prueba"), {
            "username": self.usuario.username, "password": self.clave,
        })
        self.assertRedirects(respuesta, reverse("captura_prueba"), fetch_redirect_response=False)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.usuario.pk))

    def test_login_invalido_no_crea_sesion(self):
        respuesta = self.client.post(reverse("login_prueba"), {
            "username": self.usuario.username, "password": "incorrecta",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_no_redirige_a_dominio_externo(self):
        respuesta = self.client.post(reverse("login_prueba"), {
            "username": self.usuario.username, "password": self.clave,
            "next": "https://example.invalid/",
        })
        self.assertRedirects(respuesta, reverse("captura_prueba"), fetch_redirect_response=False)

    def test_logout_exige_post_y_csrf_y_cierra_sesion(self):
        from django.test import Client
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.get(reverse("logout_prueba")).status_code, 405)
        self.assertIn("_auth_user_id", cliente.session)
        self.assertEqual(cliente.post(reverse("logout_prueba")).status_code, 403)
        self.assertIn("_auth_user_id", cliente.session)
        cliente.get(reverse("login_prueba"))
        token = cliente.cookies["csrftoken"].value
        respuesta = cliente.post(reverse("logout_prueba"), {"csrfmiddlewaretoken": token})
        self.assertEqual(respuesta.status_code, 302)
        self.assertNotIn("_auth_user_id", cliente.session)
        self.assertEqual(cliente.get(reverse("captura_prueba")).status_code, 302)

    def test_anonimo_redirigido_get_y_post(self):
        for ruta in ("catalogo_prueba", "captura_prueba"):
            for metodo in ("get", "post"):
                with self.subTest(ruta=ruta, metodo=metodo):
                    respuesta = getattr(self.client, metodo)(reverse(ruta))
                    self.assertEqual(respuesta.status_code, 302)
                    self.assertTrue(respuesta.url.startswith("/cuentas/login/?next="))

    def test_roles_get_post_sin_herencia_ni_acceso_staff(self):
        # El cliente normal omite CSRF para aislar la autorización por rol.
        self.client.force_login(self.usuario)
        for rol in (None, "Registro", "Cocina", "Administración"):
            self.usuario.groups.clear()
            if rol:
                grupo, _ = Group.objects.get_or_create(name=rol)
                self.usuario.groups.add(grupo)
            self.usuario.is_staff = True
            self.usuario.save(update_fields=["is_staff"])
            for ruta, permitido in (("catalogo_prueba", rol == ADMINISTRACION),
                                     ("captura_prueba", rol == REGISTRO)):
                for metodo in ("get", "post"):
                    with self.subTest(rol=rol, ruta=ruta, metodo=metodo):
                        respuesta = getattr(self.client, metodo)(reverse(ruta))
                        self.assertEqual(respuesta.status_code, 200 if permitido else 403)

    def test_dos_grupos_permiten_ambas_funciones(self):
        self.usuario.groups.add(self.registro, self.admin)
        self.client.force_login(self.usuario)
        for ruta in ("catalogo_prueba", "captura_prueba"):
            self.assertEqual(self.client.get(reverse(ruta)).status_code, 200)


class ServicioCatalogoComplementarioTests(TestCase):
    def setUp(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        self.plato = Plato.objects.get(codigo="seco_de_pollo")
        self.porcion = TipoPorcion.objects.get(codigo="estandar")

    def test_alta_conserva_usuario_creador(self):
        usuario = get_user_model().objects.create_user(username="registro_prueba")

        servicio = Servicio.registrar(
            plato=self.plato, porcion=self.porcion, usuario=usuario
        )

        servicio.refresh_from_db()
        self.assertEqual(Servicio.objects.count(), 1)
        self.assertEqual(servicio.creado_por_id, usuario.pk)

    def test_fallo_de_composicion_revierte_servicio_e_instantaneas(self):
        # Simula una escritura parcial antes del fallo para comprobar el rollback.
        def escribir_parcial_y_fallar(objetos):
            primero = next(iter(objetos))
            primero.save()
            raise RuntimeError("Fallo simulado al guardar la composición")

        with patch.object(
            ServicioComponente.objects,
            "bulk_create",
            side_effect=escribir_parcial_y_fallar,
        ):
            with self.assertRaisesMessage(RuntimeError, "Fallo simulado"):
                Servicio.registrar(plato=self.plato, porcion=self.porcion)

        self.assertEqual(Servicio.objects.count(), 0)
        self.assertEqual(ServicioComponente.objects.count(), 0)
        self.assertEqual(Plato.objects.count(), 3)

    def test_renombrar_porcion_no_reescribe_etiqueta_previa(self):
        anterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        self.porcion.nombre = "Estándar revisada"
        self.porcion.save(update_fields=["nombre"])

        posterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)

        anterior.refresh_from_db()
        posterior.refresh_from_db()
        self.assertEqual(anterior.get_tipo_porcion_display(), "Estándar")
        self.assertEqual(posterior.get_tipo_porcion_display(), "Estándar revisada")
        self.assertEqual(anterior.porcion_catalogo_id, posterior.porcion_catalogo_id)
        self.assertEqual(Servicio.objects.count(), 2)

    def test_relacion_inactiva_excluida_solo_de_servicios_nuevos(self):
        anterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)
        PlatoComponente.objects.filter(
            plato=self.plato, componente__codigo="maduro"
        ).update(activo=False)

        posterior = Servicio.registrar(plato=self.plato, porcion=self.porcion)

        self.assertSetEqual(
            set(anterior.composicion.values_list("componente_codigo", flat=True)),
            {"arroz", "pollo", "maduro"},
        )
        self.assertSetEqual(
            set(posterior.composicion.values_list("componente_codigo", flat=True)),
            {"arroz", "pollo"},
        )


class CargaDemoComplementariaTests(TestCase):
    def test_repetir_carga_conserva_elementos_y_composicion_personalizados(self):
        call_command("cargar_catalogo_demo", verbosity=0)
        plato = Plato.objects.get(codigo="seco_de_pollo")
        adicional = Componente.objects.create(codigo="aguacate", nombre="Aguacate")
        relacion = PlatoComponente.objects.create(plato=plato, componente=adicional)
        porcion = TipoPorcion.objects.get(codigo="estandar")
        porcion.nombre = "Porción de la casa"
        porcion.activo = False
        porcion.save()

        call_command("cargar_catalogo_demo", verbosity=0)

        porcion.refresh_from_db()
        self.assertEqual(porcion.nombre, "Porción de la casa")
        self.assertFalse(porcion.activo)
        self.assertTrue(PlatoComponente.objects.filter(pk=relacion.pk).exists())
        self.assertEqual(Plato.objects.count(), 3)
        self.assertEqual(Componente.objects.count(), 9)
        self.assertEqual(PlatoComponente.objects.count(), 10)
        self.assertEqual(TipoPorcion.objects.count(), 1)


class MigracionHistoricaTests(TransactionTestCase):
    """Migra filas reales del esquema antiguo en la base temporal de Django."""

    def test_conserva_servicios_anteriores_sin_remapear_catalogo(self):
        executor = MigrationExecutor(connection)
        destinos_originales = executor.loader.graph.leaf_nodes()

        def restaurar_esquema():
            MigrationExecutor(connection).migrate(destinos_originales)

        # También restaura el esquema si una aserción o migración falla.
        self.addCleanup(restaurar_esquema)
        origen = [("captura", "0001_initial")]
        executor.migrate(origen)
        estado_anterior = executor.loader.project_state(origen).apps
        ServicioAnterior = estado_anterior.get_model("captura", "Servicio")
        ejemplos = [
            ("arroz_con_pollo", "pequena", "Arroz con pollo", "Pequeña"),
            ("lentejas", "regular", "Lentejas", "Regular"),
            ("lentejas", "grande", "Lentejas", "Grande"),
        ]
        originales = []
        for plato, porcion, nombre_plato, nombre_porcion in ejemplos:
            registro = ServicioAnterior.objects.create(
                id=uuid.uuid4(), plato=plato, tipo_porcion=porcion
            )
            originales.append(
                (registro.pk, registro.fecha_creacion, plato, porcion,
                 nombre_plato, nombre_porcion)
            )

        destino = [("captura", "0003_etiquetas_historicas")]
        executor = MigrationExecutor(connection)
        executor.migrate(destino)
        estado_actual = executor.loader.project_state(destino).apps
        ServicioMigrado = estado_actual.get_model("captura", "Servicio")
        ComposicionMigrada = estado_actual.get_model("captura", "ServicioComponente")
        self.assertEqual(ServicioMigrado.objects.count(), len(originales))
        for pk, fecha, plato, porcion, nombre_plato, nombre_porcion in originales:
            with self.subTest(plato=plato, porcion=porcion):
                registro = ServicioMigrado.objects.get(pk=pk)
                self.assertEqual(registro.fecha_creacion, fecha)
                self.assertEqual(registro.plato, plato)
                self.assertEqual(registro.tipo_porcion, porcion)
                self.assertEqual(registro.plato_nombre, nombre_plato)
                self.assertEqual(registro.porcion_nombre, nombre_porcion)
                self.assertIsNone(registro.plato_catalogo_id)
                self.assertIsNone(registro.porcion_catalogo_id)
                self.assertIsNone(registro.creado_por_id)
        self.assertEqual(ComposicionMigrada.objects.count(), 0)
