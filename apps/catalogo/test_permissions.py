from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views import View

from .permissions import (
    ADMINISTRACION,
    COCINA,
    REGISTRO,
    ROLES,
    RolesRequiredMixin,
    roles_required,
    tiene_rol,
)


class RolesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="operador")
        self.factory = RequestFactory()
        self.salida = StringIO()
        call_command("configurar_roles", stdout=self.salida)

    def asignar(self, rol):
        self.user.groups.add(Group.objects.get(name=rol))

    def test_repetir_comando_conserva_usuarios_membresias_y_permisos_ajenos(self):
        self.asignar(REGISTRO)
        grupo = Group.objects.get(name=REGISTRO)
        ajeno = Permission.objects.get(content_type__app_label="auth", codename="view_user")
        grupo.permissions.add(ajeno)
        call_command("configurar_roles", stdout=StringIO())
        self.assertEqual(Group.objects.filter(name__in=ROLES).count(), 3)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertTrue(self.user.groups.filter(pk=grupo.pk).exists())
        self.assertTrue(grupo.permissions.filter(pk=ajeno.pk).exists())

    def test_sincroniza_sin_otorgar_borrado_o_registro_a_administracion(self):
        grupo = Group.objects.get(name=REGISTRO)
        borrar = Permission.objects.get(content_type__app_label="captura", codename="delete_servicio")
        grupo.permissions.add(borrar)
        call_command("configurar_roles", stdout=StringIO())
        self.assertFalse(grupo.permissions.filter(pk=borrar.pk).exists())
        self.asignar(REGISTRO)
        self.assertTrue(self.user.has_perm("captura.add_servicio"))
        self.assertFalse(self.user.has_perm("captura.change_servicio"))
        admin = Group.objects.get(name=ADMINISTRACION)
        self.assertFalse(admin.permissions.filter(content_type__app_label="captura").exists())

    def test_modelos_pendientes_se_informan_sin_inventar_permisos(self):
        codigo = "catalogo.view_modelo_pendiente_de_prueba"
        salida = StringIO()
        with patch(
            "apps.catalogo.management.commands.configurar_roles.PERMISOS_POR_ROL",
            {REGISTRO: (codigo,)},
        ):
            call_command("configurar_roles", stdout=salida)
        self.assertIn(codigo, salida.getvalue())
        self.assertFalse(
            Permission.objects.filter(codename="view_modelo_pendiente_de_prueba").exists()
        )

    def test_repetir_tras_integrar_catalogo_asigna_solo_permisos_de_cada_rol(self):
        content_type, _ = ContentType.objects.get_or_create(app_label="catalogo", model="plato")
        for accion in ("add", "view", "change", "delete"):
            Permission.objects.get_or_create(
                content_type=content_type,
                codename=f"{accion}_plato",
                defaults={"name": f"Puede {accion} plato"},
            )
        call_command("configurar_roles", stdout=StringIO())
        self.asignar(ADMINISTRACION)
        self.assertTrue(self.user.has_perm("catalogo.add_plato"))
        self.assertTrue(self.user.has_perm("catalogo.change_plato"))
        self.assertFalse(self.user.has_perm("catalogo.delete_plato"))
        registro = Group.objects.get(name=REGISTRO)
        self.assertTrue(registro.permissions.filter(codename="view_plato").exists())
        self.assertFalse(registro.permissions.filter(codename="change_plato").exists())

    def test_rol_no_hereda_otro_y_admite_multiples_funciones_explicitas(self):
        self.asignar(ADMINISTRACION)
        self.assertTrue(tiene_rol(self.user, ADMINISTRACION))
        self.assertFalse(tiene_rol(self.user, REGISTRO))
        self.asignar(REGISTRO)
        self.assertTrue(tiene_rol(self.user, COCINA, REGISTRO))

    def test_staff_no_bypassea_y_superusuario_activo_si(self):
        self.user.is_staff = True
        self.assertFalse(tiene_rol(self.user, ADMINISTRACION))
        self.user.is_superuser = True
        self.assertTrue(tiene_rol(self.user, ADMINISTRACION))
        self.user.is_active = False
        self.assertFalse(tiene_rol(self.user, ADMINISTRACION))

    def test_anonimo_no_tiene_rol_y_declaraciones_invalidas_fallan(self):
        self.assertFalse(tiene_rol(AnonymousUser(), REGISTRO))
        with self.assertRaises(ImproperlyConfigured):
            roles_required("rol_inexistente")
        with self.assertRaises(ImproperlyConfigured):
            roles_required()

    def test_decorator_redirige_anonimo_con_next(self):
        request = self.factory.get("/catalogo/?pagina=2")
        request.user = AnonymousUser()
        view = roles_required(ADMINISTRACION)(lambda request: HttpResponse("ok"))
        response = view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/cuentas/login/?next=", response.url)
        self.assertIn("catalogo", response.url)

    def test_decorator_controla_get_y_post_en_servidor(self):
        view = roles_required(ADMINISTRACION)(lambda request: HttpResponse("ok"))
        for method in ("get", "post"):
            with self.subTest(method=method):
                request = getattr(self.factory, method)("/catalogo/")
                request.user = self.user
                with self.assertRaises(PermissionDenied):
                    view(request)
        self.asignar(ADMINISTRACION)
        self.assertEqual(view(request).status_code, 200)

    def test_mixin_redirige_anonimo_deniega_rol_y_admite_autorizado(self):
        class CatalogoView(RolesRequiredMixin, View):
            allowed_roles = (ADMINISTRACION,)

            def get(self, request):
                return HttpResponse("ok")

        request = self.factory.get("/catalogo/")
        request.user = AnonymousUser()
        self.assertEqual(CatalogoView.as_view()(request).status_code, 302)
        request.user = self.user
        with self.assertRaises(PermissionDenied):
            CatalogoView.as_view()(request)
        self.asignar(ADMINISTRACION)
        self.assertEqual(CatalogoView.as_view()(request).status_code, 200)
