"""Contrato del comando de roles; no acredita endpoints ni modelos de bandejas.

Los permisos futuros se simulan exclusivamente en la base temporal de Django.
Requiere la base de César del bloque 2 para validar su nueva matriz.
"""

from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase


class SincronizacionPermisosBloque2Tests(TestCase):
    def setUp(self):
        self.permisos = {}
        for modelo, codigo in (
            ("servicio", "anular_servicio"),
            ("etiquetabandeja", "reemplazar_etiquetabandeja"),
            ("fotografiaservicio", "add_fotografiaservicio"),
            ("fotografiaservicio", "delete_fotografiaservicio"),
        ):
            tipo, _ = ContentType.objects.get_or_create(app_label="captura", model=modelo)
            self.permisos[codigo], _ = Permission.objects.get_or_create(
                content_type=tipo, codename=codigo, defaults={"name": codigo}
            )

    def configurar(self):
        call_command("configurar_roles", stdout=StringIO())

    def test_corrige_privilegios_indebidos_en_todos_los_grupos(self):
        for nombre in ("Registro", "Cocina", "Administración"):
            grupo, _ = Group.objects.get_or_create(name=nombre)
            grupo.permissions.add(*self.permisos.values())

        self.configurar()
        self.configurar()

        esperados = {
            "Registro": {"add_fotografiaservicio"},
            "Cocina": set(),
            "Administración": {"anular_servicio", "reemplazar_etiquetabandeja"},
        }
        for nombre, codigos in esperados.items():
            with self.subTest(rol=nombre):
                asignados = set(Group.objects.get(name=nombre).permissions.filter(
                    pk__in=[p.pk for p in self.permisos.values()]
                ).values_list("codename", flat=True))
                self.assertSetEqual(asignados, codigos)

    def test_no_cambia_contrasena_grupos_ajenos_ni_permisos_directos(self):
        usuario = get_user_model().objects.create_user(username="operador_sin_clave")
        hash_original = usuario.password
        grupo, _ = Group.objects.get_or_create(name="Grupo externo")
        grupo.permissions.add(self.permisos["delete_fotografiaservicio"])
        usuario.groups.add(grupo)
        usuario.user_permissions.add(self.permisos["anular_servicio"])

        self.configurar()

        usuario.refresh_from_db()
        self.assertEqual(usuario.password, hash_original)
        self.assertSetEqual(set(usuario.groups.values_list("name", flat=True)), {"Grupo externo"})
        self.assertTrue(usuario.user_permissions.filter(pk=self.permisos["anular_servicio"].pk).exists())
        self.assertTrue(grupo.permissions.filter(pk=self.permisos["delete_fotografiaservicio"].pk).exists())

    def test_retirar_grupo_registro_retira_permiso_efectivo(self):
        self.configurar()
        usuario = get_user_model().objects.create_user(username="registro_revocado")
        grupo = Group.objects.get(name="Registro")
        usuario.groups.add(grupo)
        # Instancias nuevas evitan confundir la caché has_perm con la política.
        self.assertTrue(get_user_model().objects.get(pk=usuario.pk).has_perm(
            "captura.add_fotografiaservicio"
        ))

        usuario.groups.remove(grupo)

        self.assertFalse(get_user_model().objects.get(pk=usuario.pk).has_perm(
            "captura.add_fotografiaservicio"
        ))
