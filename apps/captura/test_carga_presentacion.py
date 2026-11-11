import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import Group, User
from django.core.management import call_command, CommandError
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

from apps.analisis.models import AnalisisServicio
from apps.captura.models import Bandeja, FotografiaServicio, Servicio
from apps.catalogo.models import TipoPorcion
from apps.historico import services
from apps.recomendaciones.models import EvaluacionPrueba, Recomendacion
from ops.presentacion.planificar import construir


class PresentacionLocalTests(TransactionTestCase):
    def test_previsualizar_cargar_consultar_y_retirar(self):
        call_command('cargar_catalogo_demo', stdout=StringIO())
        TipoPorcion.objects.get_or_create(codigo='reducida', defaults={'nombre': 'Reducida'})
        usuarios = {}
        for clave, rol in [('registro', 'Registro'), ('cocina', 'Cocina'), ('administracion', 'Administración')]:
            usuario = User.objects.create_user(clave)
            usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
            usuarios[clave] = usuario
        previa = Bandeja.objects.create(numero=101)
        with self.assertRaisesMessage(CommandError, 'configuración local'):
            call_command('cargar_presentacion', stdout=StringIO())
        with TemporaryDirectory() as directorio:
            raiz = Path(directorio)
            perfil = json.loads(Path('ops/analisis/criterios_piloto.propuesta.json').read_text())
            config = dict(
                SETTINGS_MODULE='config.settings_presentacion', EVA_PRESENTACION_LOTE='prueba',
                EVA_PRESENTACION_IDS=tuple(f['id'] for f in construir('prueba')['servicios']),
                EVA_CAPTURE_PRIVATE_ROOT=raiz,
                EVA_HISTORICO_CRITERIOS={**perfil['historico'], 'aprobada': True},
                EVA_RECOMENDACIONES_CRITERIOS={**perfil['recomendaciones'], 'aprobada': True},
            )
            with override_settings(**config):
                salida = StringIO()
                call_command('cargar_presentacion', stdout=salida)
                self.assertIn('288 servicios', salida.getvalue())
                self.assertEqual(Servicio.objects.count(), 0)
                with self.assertRaisesMessage(CommandError, 'identificador exacto'):
                    call_command('cargar_presentacion', retirar=True)
                args = {clave: usuario.username for clave, usuario in usuarios.items()}
                for _ in range(2):
                    call_command('cargar_presentacion', aplicar=True, confirmar='prueba', stdout=salida, **args)
                self.assertIn('ya está cargado', salida.getvalue())
                self.assertEqual(Servicio.objects.count(), 288)
                self.assertEqual(FotografiaServicio.objects.count(), 576)
                self.assertEqual(AnalisisServicio.objects.filter(origen='SIMULADO').count(), 240)
                self.assertEqual(Recomendacion.objects.count(), 3)
                self.assertEqual(EvaluacionPrueba.objects.get().snapshot['estado'], 'EVALUADA')
                self.client.force_login(usuarios['administracion'])
                filtros = dict(desde='2026-10-05', hasta='2026-11-01', plato='seco_de_pollo',
                               componente='pollo', porcion='estandar')
                respuesta = self.client.get(reverse('historico:lista'), filtros)
                self.assertContains(respuesta, 'Datos de prueba')
                self.assertTrue(respuesta.context['datos']['solo_pruebas'])
                self.assertContains(self.client.get(reverse('recomendaciones:lista')), 'Datos de prueba')
                with override_settings(SETTINGS_MODULE='config.settings'):
                    # Los 240 análisis siguen excluidos bajo el selector operativo.
                    datos = services.consultar_historico(filtros)
                    self.assertFalse(datos['solo_pruebas'])
                    self.assertEqual(datos['paginacion']['total_filas'], 8)
                archivo = next(raiz.rglob('*.png'))
                original = archivo.read_bytes()
                archivo.write_bytes(b'archivo sustituido')
                with self.assertRaisesMessage(CommandError, 'cambió'):
                    call_command('cargar_presentacion', retirar=True, confirmar='prueba', stdout=salida)
                self.assertEqual(Servicio.objects.count(), 288)
                archivo.write_bytes(original)
                for _ in range(2):
                    call_command('cargar_presentacion', retirar=True, confirmar='prueba', stdout=salida)
                self.assertFalse(Servicio.objects.exists())
                self.assertFalse(Recomendacion.objects.exists())
                self.assertFalse(list(raiz.rglob('*.png')))
                self.assertEqual(list(Bandeja.objects.values_list('pk', flat=True)), [previa.pk])
                self.assertEqual(User.objects.count(), 3)
