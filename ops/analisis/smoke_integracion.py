"""Ensayo aislado B4/B5 con motor HTTP SIMULADO y worker Django real.

Ejecutar con el Python del proyecto. Solo usa SQLite y archivos temporales,
no toca bases, cuentas, fotos o servicios de producción.
"""
import base64
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import threading
import uuid

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def imagen(modo='RGB', rectangulo=None):
    foto = Image.new(modo, (8, 8), 'white' if modo == 'RGB' else 0)
    if rectangulo:
        foto.paste(255, rectangulo)
    buffer = BytesIO()
    foto.save(buffer, format='PNG')
    return buffer.getvalue()


def hijo(etapa):
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.core.management import call_command
    from django.test import Client
    from django.urls import reverse
    from apps.captura import storage
    from apps.captura.models import Servicio, FotografiaServicio
    from apps.captura.protocolo import CRITERIOS, VERSION
    from apps.catalogo.models import Plato, TipoPorcion
    from apps.analisis.models import IntentoAnalisis, RevisionAnalisis
    cliente = Client(HTTP_HOST='testserver')
    if etapa == 'preparar':
        call_command('migrate', verbosity=0, interactive=False)
        call_command('cargar_catalogo_demo', verbosity=0)
        call_command('configurar_roles', stdout=StringIO())
        usuario = get_user_model().objects.create_user('fixture_cocina')
        usuario.groups.add(Group.objects.get(name='Cocina'))
        servicio = Servicio.registrar(plato=Plato.objects.get(codigo='seco_de_pollo'),
            porcion=TipoPorcion.objects.get(codigo='estandar'), usuario=usuario)
        for etapa_foto in ('SERVIDO', 'RETORNO'):
            datos = imagen()
            g = storage.guardar(datos, f'fixture/{etapa_foto}.png')
            FotografiaServicio.objects.create(servicio=servicio, etapa=etapa_foto, backend=g.backend,
                clave_archivo=g.clave, hash_sha256=g.hash_sha256, tipo_contenido='image/png',
                tamano_bytes=len(datos), ancho=8, alto=8, autor=usuario,
                protocolo_version=VERSION, checklist=dict.fromkeys(CRITERIOS, True))
        Servicio.objects.filter(pk=servicio.pk).update(estado_captura='PAR_COMPLETO')
        cliente.force_login(usuario)
        assert cliente.post(reverse('analisis:solicitar', args=[servicio.pk])).status_code == 302
        assert IntentoAnalisis.objects.get().estado == 'PENDIENTE'
    else:
        intento = IntentoAnalisis.objects.get()
        assert intento.estado == 'COMPLETADO', intento.estado
        assert intento.analisis.origen == 'SIMULADO'
        assert intento.resultados.count() == 3
        cliente.force_login(get_user_model().objects.get(username='fixture_cocina'))
        detalle = cliente.get(reverse('analisis:revision_detalle', args=[intento.analisis_id]))
        assert detalle.status_code == 200 and b'SIMULADO' in detalle.content
        foto = intento.analisis.foto_servido
        assert cliente.get(reverse('analisis:foto', args=[intento.analisis_id, foto.pk])).status_code == 200
        art = intento.resultados.first().artefactos.first()
        assert cliente.get(reverse('analisis:mascara', args=[intento.analisis_id, art.pk])).status_code == 200
        decidir = reverse('analisis:revisar', args=[intento.analisis_id, intento.pk])
        assert cliente.post(decidir, dict(decision='CONFIRMADO', version_esperada=0)).status_code == 400
        assert cliente.post(decidir, dict(decision='RECHAZADO', motivo='Ensayo sintético', version_esperada=0)).status_code == 302
        assert RevisionAnalisis.objects.get().decision == 'RECHAZADO'
        print(json.dumps(dict(origen='SIMULADO', worker_real=True, motor_http_fixture=True,
                              estado=intento.estado, resultados=3, revision='RECHAZADO',
                              confirmacion_simulada_bloqueada=True, gateway_privado=True)))


class MotorFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        cuerpo = self.rfile.read(int(self.headers['Content-Length']))
        mensaje = BytesParser(policy=policy.default).parsebytes(
            ('Content-Type: ' + self.headers['Content-Type'] + '\r\nMIME-Version: 1.0\r\n\r\n').encode() + cuerpo)
        metadata = next(json.loads(p.get_payload(decode=True)) for p in mensaje.iter_parts()
                        if p.get_param('name', header='Content-Disposition') == 'metadata')
        assert self.headers.get('Authorization') == 'Bearer ' + os.environ['EVA_FIXTURE_TOKEN']
        respuesta = {k: metadata[k] for k in ('schema_version', 'request_id', 'version_modelo', 'version_configuracion', 'origen')}
        respuesta.update(transformacion={'tipo': 'IDENTIDAD', 'escala_comun': True}, componentes=[])
        for i, comp in enumerate(metadata['componentes']):
            mascaras = [dict(etapa=e, ancho=8, alto=8,
                png_base64=base64.b64encode(imagen('L', (i * 2, 0, i * 2 + 2, alto))).decode())
                for e, alto in [('SERVIDO', 4), ('RETORNO', 2)]]
            respuesta['componentes'].append(dict(id=comp['id'], confianza=.9, comparable=True, oculto=False, mascaras=mascaras))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(respuesta).encode())


def principal():
    with TemporaryDirectory(prefix='eva-smoke-') as carpeta:
        temporal = Path(carpeta)
        servidor = ThreadingHTTPServer(('127.0.0.1', 0), MotorFixture)
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        token = uuid.uuid4().hex
        os.environ['EVA_FIXTURE_TOKEN'] = token
        entorno = dict(os.environ, DJANGO_SETTINGS_MODULE='eva_smoke_settings',
                       PYTHONPATH=str(temporal) + os.pathsep + str(ROOT),
                       EVA_VISUAL_ENDPOINT=f'http://127.0.0.1:{servidor.server_port}/v1/analizar-par',
                       EVA_VISUAL_VERSION_MODELO='fixture-smoke', EVA_VISUAL_TOKEN=token,
                       EVA_VISUAL_ORIGEN='SIMULADO')
        (temporal / 'eva_smoke_settings.py').write_text(
            'from config.settings import *\n'
            f'DATABASES = {{"default": {{"ENGINE":"django.db.backends.sqlite3", "NAME":{str(temporal / "fixture.sqlite3")!r}}}}}\n'
            f'EVA_CAPTURE_PRIVATE_ROOT = {str(temporal / "privado")!r}\n'
            'EVA_STORAGE_BACKEND="local"\nALLOWED_HOSTS=["testserver"]\n'
            'EVA_ANALISIS_CRITERIOS={"version":"fixture-smoke", "aprobada":False, "umbrales":{}}\n', encoding='utf-8')
        hilo.start()
        try:
            subprocess.run([sys.executable, str(Path(__file__).resolve()), '--hijo', 'preparar'], env=entorno, cwd=ROOT, check=True, timeout=30)
            subprocess.run([sys.executable, str(ROOT / 'manage.py'), 'procesar_analisis', '--una-vez'], env=entorno, cwd=ROOT, check=True, timeout=40)
            subprocess.run([sys.executable, str(Path(__file__).resolve()), '--hijo', 'verificar'], env=entorno, cwd=ROOT, check=True, timeout=30)
        finally:
            servidor.shutdown()
            servidor.server_close()
            hilo.join()
            os.environ.pop('EVA_FIXTURE_TOKEN', None)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--hijo':
        hijo(sys.argv[2])
    else:
        principal()
