from copy import deepcopy
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse
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

    def test_pantalla_restringida_y_origen_siempre_visible(self):
        self.assertEqual(self.client.get(reverse('recomendaciones:demo')).status_code, 302)
        self.usuario('Registro')
        self.assertEqual(self.client.get(reverse('recomendaciones:demo')).status_code, 403)
        self.assertEqual(self.client.get(reverse('recomendaciones:demo_foto')).status_code, 403)
        for rol in ('Cocina', 'Administración'):
            self.usuario(rol)
            respuesta = self.client.get(reverse('recomendaciones:demo'))
            self.assertContains(respuesta, 'Datos de ejemplo')
            self.assertContains(respuesta, 'no son predicciones de la IA')
            self.assertContains(respuesta, 'Revisar porción')
            self.assertEqual(self.client.post(reverse('recomendaciones:demo')).status_code, 405)
            self.assertEqual(self.client.get(reverse('recomendaciones:demo'), {'escenario':'otro'}).status_code, 404)

    @override_settings(EVA_DEMO_SERVICIO_ID='')
    def test_foto_sin_configuracion_no_acepta_id_arbitrario(self):
        self.usuario('Cocina')
        self.assertEqual(self.client.get(reverse('recomendaciones:demo_foto'), {'servicio':'cualquiera'}).status_code, 404)
