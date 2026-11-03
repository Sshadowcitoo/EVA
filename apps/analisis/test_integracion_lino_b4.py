import base64
import hashlib
import json
import subprocess
import sys
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO, StringIO
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.analisis import evidencia, jobs, motor, services
from apps.analisis.models import ArtefactoAnalisis, IntentoAnalisis
from apps.analisis.test_dominio_analisis import BaseAnalisis
from apps.captura import limpieza, storage
from apps.captura.models import CargaFotografia, FotografiaServicio
from apps.captura.protocolo import CRITERIOS, VERSION


def png(imagen):
    destino = BytesIO()
    imagen.save(destino, format='PNG')
    return destino.getvalue()


@override_settings(EVA_STORAGE_BACKEND='local', EVA_VISUAL_ENDPOINT='http://127.0.0.1:1/v1/analizar-par',
                   EVA_VISUAL_TOKEN='fixture-no-real', EVA_VISUAL_VERSION_MODELO='m1', EVA_VISUAL_ORIGEN='REAL')
class BaseWebMotor(BaseAnalisis):
    def setUp(self):
        super().setUp()
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        ajuste = self.settings(EVA_CAPTURE_PRIVATE_ROOT=carpeta.name,
                               EVA_ANALISIS_CRITERIOS=dict(version='c1', aprobada=True,
                                   comparabilidad_aprobada=True,
                                   umbrales={c.componente_codigo: .7 for c in self.comps}))
        ajuste.enable()
        self.addCleanup(ajuste.disable)
        for f in (self.servido, self.retorno):
            datos = png(Image.new('RGB', (8, 8), 'white'))
            guardado = storage.guardar(datos, f.clave_archivo)
            FotografiaServicio.objects.filter(pk=f.pk).update(ancho=8, alto=8,
                hash_sha256=guardado.hash_sha256, tipo_contenido='image/png', tamano_bytes=len(datos),
                protocolo_version=VERSION, checklist=dict.fromkeys(CRITERIOS, True))
            f.refresh_from_db()
        call_command('configurar_roles', stdout=StringIO())
        self.usuario.groups.add(Group.objects.get(name='Cocina'))
        self.client.force_login(self.usuario)

    def respuesta_motor(self, intento):
        componentes = []
        for i, comp in enumerate(self.comps):
            mascaras = []
            for etapa, alto in [('SERVIDO', 4), ('RETORNO', 2)]:
                imagen = Image.new('L', (8, 8), 0)
                imagen.paste(255, (i * 2, 0, i * 2 + 2, alto))
                mascaras.append(dict(etapa=etapa, ancho=8, alto=8,
                                     png_base64=base64.b64encode(png(imagen)).decode()))
            componentes.append(dict(id=str(comp.pk), area_inicial=8, area_residual=4,
                                     confianza=.9, comparable=True, oculto=False, mascaras=mascaras))
        return dict(schema_version=1, request_id=str(intento.pk), version_modelo='m1',
                    version_configuracion='c1', origen='REAL', componentes=componentes,
                    transformacion={'tipo': 'IDENTIDAD', 'escala_comun': True})

    def ejecutar(self):
        intento = self.en_proceso()
        resultado = motor.validar(self.respuesta_motor(intento), intento, self.comps)
        with patch('apps.analisis.jobs.motor.llamar', return_value=resultado):
            jobs.procesar(intento.pk)
        intento.refresh_from_db()
        return intento


class ContratoMotorTests(BaseWebMotor):
    def test_areas_derivadas_de_mascaras_y_criterios_servidor(self):
        intento = self.en_proceso()
        datos, archivos = motor.validar(self.respuesta_motor(intento), intento, self.comps)
        self.assertEqual(len(archivos), 6)
        self.assertEqual(datos[0]['area_inicial'], 8)
        self.assertTrue(datos[0]['comparable'])
        self.assertEqual(datos[0]['umbral_confianza'], .7)

    def test_sin_criterio_o_transformacion_no_certifica_comparabilidad(self):
        intento = self.en_proceso()
        respuesta = self.respuesta_motor(intento)
        respuesta.pop('transformacion')
        self.assertFalse(motor.validar(respuesta, intento, self.comps)[0][0]['comparable'])
        with override_settings(EVA_ANALISIS_CRITERIOS={}):
            datos, _ = motor.validar(self.respuesta_motor(intento), intento, self.comps)
            self.assertFalse(datos[0]['comparable'])
            self.assertIsNone(datos[0]['umbral_confianza'])

    def test_identidad_y_origen_no_son_del_motor(self):
        intento = self.en_proceso()
        for campo, valor in [('request_id', 'otro'), ('origen', 'SIMULADO'), ('version_modelo', 'otro'), ('version_configuracion', 'otra')]:
            respuesta = self.respuesta_motor(intento)
            respuesta[campo] = valor
            with self.subTest(campo=campo), self.assertRaises(ValidationError):
                motor.validar(respuesta, intento, self.comps)

    def test_no_acepta_areas_inventadas_componentes_repetidos_ni_urls(self):
        intento = self.en_proceso()
        for tipo in ('area', 'duplicado', 'url', 'geometria', 'nan', 'solapamiento'):
            respuesta = self.respuesta_motor(intento)
            item = respuesta['componentes'][0]
            if tipo == 'area': item['area_inicial'] = 200
            if tipo == 'duplicado': respuesta['componentes'][1]['id'] = item['id']
            if tipo == 'url': item['mascaras'][0]['png_base64'] = 'https://ejemplo.test/m.png'
            if tipo == 'geometria': item['mascaras'][0]['ancho'] = 9
            if tipo == 'nan': item['confianza'] = float('nan')
            if tipo == 'solapamiento':
                respuesta['componentes'][1]['mascaras'] = item['mascaras']
            with self.subTest(tipo=tipo), self.assertRaises(ValidationError):
                motor.validar(respuesta, intento, self.comps)

    def test_mascara_sin_deteccion_no_inventa_residuo_cero(self):
        intento = self.en_proceso()
        respuesta = self.respuesta_motor(intento)
        item = respuesta['componentes'][0]
        item['mascaras'] = item['mascaras'][:1]
        item.pop('area_residual')
        datos, _ = motor.validar(respuesta, intento, self.comps)
        self.assertIsNone(datos[0]['area_residual'])

    def test_http_real_envia_metadata_y_token_sin_seguir_redirecciones(self):
        intento = self.en_proceso()
        respuesta = self.respuesta_motor(intento)
        observado = {}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                observado['token'] = self.headers.get('Authorization')
                observado['body'] = self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(respuesta).encode())
        servidor = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        try:
            with override_settings(EVA_VISUAL_ENDPOINT=f'http://127.0.0.1:{servidor.server_port}/v1/analizar-par'):
                datos, _ = motor.llamar(intento, time.monotonic() + 5)
            self.assertEqual(len(datos), 3)
            self.assertEqual(observado['token'], 'Bearer fixture-no-real')
            self.assertIn(str(intento.pk).encode(), observado['body'])
        finally:
            servidor.shutdown()
            servidor.server_close()
            hilo.join()

    def test_configuracion_rechaza_red_insegura_y_credenciales_en_url(self):
        for endpoint in ('http://motor.example/v1', 'https://usuario:clave@motor.example/v1', ''):
            with self.subTest(endpoint=endpoint), override_settings(EVA_VISUAL_ENDPOINT=endpoint), self.assertRaises(motor.SinMotor):
                motor.configuracion()


class WorkerEvidenciaTests(BaseWebMotor):
    def test_supervisor_interrumpe_un_subproceso_real_bloqueado(self):
        self.solicitar()
        original = subprocess.Popen
        procesos = []
        def iniciar(*args, **kwargs):
            proceso = original([sys.executable, '-c', 'import time; time.sleep(15)'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            procesos.append(proceso)
            return proceso
        inicio = time.monotonic()
        with patch('apps.analisis.jobs.subprocess.Popen', side_effect=iniciar), patch(
                'apps.analisis.jobs.disponible', return_value=.15):
            jobs.ejecutar_uno()
        self.assertLess(time.monotonic() - inicio, 5)
        self.assertIsNotNone(procesos[0].poll())
        self.assertEqual(IntentoAnalisis.objects.get().estado, 'TIEMPO_AGOTADO')

    def test_persiste_mascaras_y_publica_solo_resultado_completo(self):
        intento = self.ejecutar()
        self.assertEqual(intento.estado, 'COMPLETADO')
        self.assertEqual(ArtefactoAnalisis.objects.count(), 6)
        self.assertFalse(CargaFotografia.objects.filter(resuelta_en=None).exists())
        self.assertEqual(intento.resultados.first().porcentaje, 50)

    def test_fallo_de_publicacion_deja_cola_reconciliable_sin_resultados(self):
        intento = self.en_proceso()
        datos = motor.validar(self.respuesta_motor(intento), intento, self.comps)
        with patch('apps.analisis.jobs.motor.llamar', return_value=datos), patch(
                'apps.analisis.jobs.services.completar_intento', side_effect=ValidationError('fixture')):
            jobs.procesar(intento.pk)
        intento.refresh_from_db()
        self.assertEqual(intento.estado, 'FALLIDO')
        self.assertFalse(intento.resultados.exists())
        self.assertTrue(CargaFotografia.objects.filter(resuelta_en=None).exists())
        informe = limpieza.ejecutar(aplicar=True, ahora=timezone.now() + timedelta(hours=25))
        self.assertEqual(informe['cargas_eliminadas'], 6)

    def test_supervisor_mata_proceso_lento_y_cierra_timeout(self):
        self.solicitar()
        proceso = Mock()
        proceso.wait.side_effect = [subprocess.TimeoutExpired('fixture', 30), 0]
        with patch('apps.analisis.jobs.subprocess.Popen', return_value=proceso):
            self.assertTrue(jobs.ejecutar_uno())
        proceso.kill.assert_called_once()
        self.assertEqual(IntentoAnalisis.objects.get().estado, 'TIEMPO_AGOTADO')
        self.assertLessEqual(proceso.wait.call_args_list[0].kwargs['timeout'], 30)

    def test_cola_no_borra_mascaras_vinculadas_y_retencion_heredada(self):
        self.ejecutar()
        CargaFotografia.objects.update(creada_en=timezone.now() - timedelta(hours=25), resuelta_en=None)
        informe = limpieza.ejecutar(aplicar=True)
        self.assertEqual(informe['cargas_vinculadas'], 6)
        FotografiaServicio.objects.filter(pk=self.servido.pk).update(fecha=timezone.now() - timedelta(days=91))
        simulacion = limpieza.ejecutar()
        self.assertEqual(simulacion['mascaras_candidatas'], 3)
        self.assertEqual(simulacion['mascaras_eliminadas'], 0)
        self.assertEqual(limpieza.ejecutar(aplicar=True)['mascaras_eliminadas'], 3)


class EndpointsAnalisisTests(BaseWebMotor):
    def test_solicitar_idempotente_y_estado_json_privado(self):
        url = reverse('analisis:solicitar', args=[self.servicio.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        respuesta = self.client.post(url)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(IntentoAnalisis.objects.count(), 1)
        intento = IntentoAnalisis.objects.get()
        estado = self.client.get(reverse('analisis:estado', args=[intento.analisis_id]))
        self.assertEqual(estado.json(), {'estado': 'PENDIENTE'})
        self.assertIn('no-store', estado['Cache-Control'])

    def test_roles_aislados_y_csrf(self):
        intento = self.en_proceso()
        url = reverse('analisis:estado', args=[intento.analisis_id])
        for rol in ('Registro', 'Administración'):
            self.usuario.groups.set([Group.objects.get(name=rol)])
            self.assertEqual(self.client.get(url).status_code, 403)
        self.usuario.groups.set([Group.objects.get(name='Cocina')])
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post(reverse('analisis:solicitar', args=[self.servicio.pk])).status_code, 403)
        cliente.logout()
        self.assertEqual(cliente.get(url).status_code, 302)

    def test_gateway_no_permite_foto_ajena_y_bloquea_vencimiento(self):
        intento = self.en_proceso()
        _, ajena, _ = self.crear_par()
        url = reverse('analisis:foto', args=[intento.analisis_id, self.servido.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get(reverse('analisis:foto', args=[intento.analisis_id, ajena.pk])).status_code, 404)
        FotografiaServicio.objects.filter(pk=self.servido.pk).update(fecha=timezone.now() - timedelta(days=91))
        self.assertEqual(self.client.get(url).status_code, 410)

    def test_mascara_transparente_color_estable_y_lista_conectada(self):
        intento = self.ejecutar()
        art = ArtefactoAnalisis.objects.first()
        respuesta = self.client.get(reverse('analisis:mascara', args=[intento.analisis_id, art.pk]))
        self.assertEqual(respuesta.status_code, 200)
        imagen = Image.open(BytesIO(respuesta.content))
        self.assertEqual(imagen.mode, 'RGBA')
        self.assertIn(0, imagen.getchannel('A').getextrema())
        self.assertEqual(self.client.get(reverse('analisis:lista')).status_code, 200)
        self.assertContains(self.client.get(reverse('analisis:detalle', args=[intento.analisis_id])), '50.00 %')

    def test_sin_motor_o_checklist_no_se_encola(self):
        with override_settings(EVA_VISUAL_ENDPOINT=''):
            self.assertEqual(self.client.post(reverse('analisis:solicitar', args=[self.servicio.pk])).status_code, 400)
        FotografiaServicio.objects.filter(pk=self.servido.pk).update(checklist={})
        self.assertEqual(self.client.post(reverse('analisis:solicitar', args=[self.servicio.pk])).status_code, 400)
        self.assertFalse(IntentoAnalisis.objects.exists())
