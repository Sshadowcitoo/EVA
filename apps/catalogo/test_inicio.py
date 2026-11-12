from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from io import StringIO
from django.urls import reverse

from .permissions import ADMINISTRACION, COCINA, REGISTRO


class InicioTests(TestCase):
    def test_inicio_requiere_sesion_y_rol(self):
        self.assertRedirects(self.client.get(reverse('inicio')),
                             reverse('cuentas:login') + '?next=' + reverse('inicio'))
        usuario = User.objects.create_user('sin_rol')
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(reverse('inicio')).status_code, 403)

    def test_inicio_ofrece_solo_las_tareas_del_rol(self):
        for rol in (REGISTRO, COCINA, ADMINISTRACION):
            with self.subTest(rol=rol):
                usuario = User.objects.create_user(rol)
                usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
                self.client.force_login(usuario)
                respuesta = self.client.get(reverse('inicio'))
                self.assertEqual(respuesta.status_code, 200)
                for ruta, visible in [('captura:resolver_bandeja', rol == REGISTRO),
                                      ('analisis:pendientes_revision', rol == COCINA),
                                      ('catalogo:platos', rol == ADMINISTRACION),
                                      ('recomendaciones:lista', rol == ADMINISTRACION),
                                      ('analisis:lista', rol == COCINA)]:
                    if visible:
                        self.assertContains(respuesta, 'href="' + reverse(ruta) + '"')
                    else:
                        self.assertNotContains(respuesta, 'href="' + reverse(ruta) + '"')

    def test_cocina_no_abre_enlaces_administrativos_ni_consulta_sus_servicios(self):
        from apps.recomendaciones import services
        call_command('configurar_roles', stdout=StringIO())
        usuario = User.objects.create_user('cocina_aislada')
        usuario.groups.add(Group.objects.get_or_create(name=COCINA)[0])
        self.client.force_login(usuario)
        identificador = '00000000-0000-4000-8000-000000000001'
        for ruta in ('historico:lista', 'historico:comparar', 'recomendaciones:lista', 'catalogo:platos', 'captura:gestion'):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(reverse(ruta)).status_code, 403)
        for operacion in (services.obtener_evaluacion, services.obtener_recomendacion, services.obtener_prueba):
            with self.subTest(operacion=operacion.__name__), self.assertRaises(PermissionDenied):
                operacion(identificador, usuario)
        with self.assertRaises(PermissionDenied):
            services.consultar_recomendaciones({}, usuario)
        for ruta in ('analisis:lista', 'analisis:pendientes_revision'):
            self.assertEqual(self.client.get(reverse(ruta)).status_code, 200)

    def test_administracion_conserva_el_acceso_a_indicadores_y_recomendaciones(self):
        usuario = User.objects.create_user('administracion_aislada')
        usuario.groups.add(Group.objects.get_or_create(name=ADMINISTRACION)[0])
        self.client.force_login(usuario)
        for ruta in ('historico:lista', 'historico:comparar', 'recomendaciones:lista'):
            self.assertEqual(self.client.get(reverse(ruta)).status_code, 200)
