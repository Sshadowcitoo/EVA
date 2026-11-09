from copy import deepcopy
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from apps.captura.models import Servicio
from .demo import preparar
from .models import EvaluacionEvidencia, Recomendacion


class DemostracionTests(TestCase):
    def test_mismas_reglas_con_tres_resultados_y_muestra_insuficiente(self):
        for clave, categoria in [('mantener', 'MANTENER'), ('porcion', 'REVISAR_PORCION'),
                                 ('prueba', 'PRUEBA_CONTROLADA'), ('insuficiente', None)]:
            with self.subTest(clave=clave):
                ejemplo = preparar(clave)
                self.assertEqual(ejemplo['categoria'], categoria)
                self.assertEqual(ejemplo['suficiente'], categoria is not None)
        self.assertEqual(preparar('porcion')['indicadores']['intensidad'], Decimal(30))
        self.assertEqual(preparar('porcion')['indicadores']['prevalencia'], Decimal(100))
        # Diez exacto no es presencia: el umbral es estrictamente mayor.
        self.assertEqual(preparar('prueba')['indicadores']['prevalencia'], Decimal(20))

    def test_no_muta_criterios_operativos_ni_crea_evidencia(self):
        antes = deepcopy(settings.EVA_ANALISIS_CRITERIOS)
        for escenario in ('mantener', 'porcion', 'prueba', 'insuficiente'):
            preparar(escenario)
        self.assertEqual(settings.EVA_ANALISIS_CRITERIOS, antes)
        self.assertEqual(Servicio.objects.count(), 0)
        self.assertEqual(EvaluacionEvidencia.objects.count(), 0)
        self.assertEqual(Recomendacion.objects.count(), 0)

    def usuario(self, rol):
        usuario = get_user_model().objects.create_user('demo_' + rol)
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        self.client.force_login(usuario)

    def test_pantalla_y_foto_retiradas_para_todos(self):
        urls = ('/recomendaciones/demostracion/', '/recomendaciones/demostracion/foto/')
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 404)
        for rol in ('Registro', 'Cocina', 'Administración'):
            self.usuario(rol)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.post(url).status_code, 404)

    @override_settings(EVA_DEMO_SERVICIO_ID='00000000-0000-0000-0000-000000000001')
    def test_foto_retirada_incluso_con_configuracion_anterior(self):
        self.usuario('Cocina')
        self.assertEqual(self.client.get('/recomendaciones/demostracion/foto/', {'servicio':'cualquiera'}).status_code, 404)
