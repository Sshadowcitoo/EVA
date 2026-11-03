"""Worker aislado: el proceso supervisor limita lectura, red, validación y guardado."""
import logging
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import URLError

from django.conf import settings
from django.utils import timezone

from apps.captura import limpieza, storage
from apps.captura.models import CargaFotografia
from . import motor, services
from .models import IntentoAnalisis

logger = logging.getLogger(__name__)


def disponible(intento):
    restante = (intento.limite_en - timezone.now()).total_seconds()
    if restante <= 0:
        raise TimeoutError()
    return restante


def procesar(intento_id):
    intento = IntentoAnalisis.objects.select_related(
        'analisis__servicio', 'analisis__foto_servido', 'analisis__foto_retorno').get(pk=intento_id)
    if intento.estado != IntentoAnalisis.Estado.EN_PROCESO:
        return
    cargas = []
    try:
        plazo = time.monotonic() + disponible(intento)
        resultados, archivos = motor.llamar(intento, plazo)
        artefactos = []
        for archivo in archivos:
            disponible(intento)
            clave = f'analisis/{intento.pk}/{uuid.uuid4().hex}.png'
            carga = limpieza.registrar_carga(clave)
            cargas.append(carga)
            try:
                guardado = storage.guardar(archivo['datos'], clave, tipo_contenido='image/png')
            except storage.ArchivoExistente:
                # Una colisión no nos autoriza a borrar un objeto previo.
                CargaFotografia.objects.filter(pk=carga.pk).update(resuelta_en=timezone.now(), resultado='colision')
                raise
            CargaFotografia.objects.filter(pk=carga.pk).update(version_id=guardado.version_id)
            artefactos.append(dict(servicio_componente=archivo['servicio_componente'], etapa=archivo['etapa'],
                                   clave_archivo=guardado.clave, backend=guardado.backend,
                                   version_id=guardado.version_id, hash_sha256=guardado.hash_sha256,
                                   ancho=archivo['ancho'], alto=archivo['alto']))
        disponible(intento)
        services.completar_intento(intento=intento, request_id=str(intento.pk),
                                  version_modelo=intento.analisis.version_modelo,
                                  version_configuracion=intento.analisis.version_configuracion,
                                  origen=intento.analisis.origen, resultados=resultados, artefactos=artefactos)
        CargaFotografia.objects.filter(pk__in=[c.pk for c in cargas]).update(
            resuelta_en=timezone.now(), resultado='vinculada', error='')
    except Exception as error:
        # No registrar cuerpo del motor, credenciales ni URLs internas.
        logger.warning('EVA_ANALISIS_FALLO intento=%s clase=%s', intento.pk, type(error).__name__)
        actual = IntentoAnalisis.objects.get(pk=intento.pk)
        if actual.estado == IntentoAnalisis.Estado.EN_PROCESO:
            if isinstance(error, TimeoutError) or actual.limite_en <= timezone.now():
                services.agotar_tiempo(intento=actual)
            else:
                tipo = (IntentoAnalisis.TipoError.ERROR_ALMACENAMIENTO if isinstance(error, storage.ErrorAlmacenamiento)
                        else IntentoAnalisis.TipoError.SIN_CONEXION if isinstance(error, URLError)
                        else IntentoAnalisis.TipoError.RESPUESTA_INVALIDA)
                services.fallar_intento(intento=actual, tipo_error=tipo,
                                       mensaje='No se pudo completar el análisis; revisa la conexión o respuesta del motor.')
        # Cargas sin referencias quedan persistidas para reconciliación, incluso si el proceso muere.


def ejecutar_uno():
    motor.configuracion()  # Sin configuración no consumir pendientes ni producir simulaciones.
    services.cerrar_intentos_vencidos()
    intento = services.reclamar_siguiente_intento()
    if intento is None:
        return False
    logger.info('EVA_ANALISIS_RECLAMADO intento=%s fecha=%s', intento.pk, intento.comenzado_en.isoformat())
    proceso = None
    try:
        proceso = subprocess.Popen(
            [sys.executable, str(Path(settings.BASE_DIR) / 'manage.py'), 'analisis_ejecutar_intento', str(intento.pk)],
            cwd=settings.BASE_DIR, stdout=subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        proceso.wait(timeout=disponible(intento))
    except (subprocess.TimeoutExpired, TimeoutError):
        if proceso is not None:
            proceso.kill()
            proceso.wait(timeout=5)
        actual = IntentoAnalisis.objects.get(pk=intento.pk)
        if actual.estado == IntentoAnalisis.Estado.EN_PROCESO:
            services.agotar_tiempo(intento=actual)
    except OSError:
        services.fallar_intento(intento=intento, tipo_error=IntentoAnalisis.TipoError.OTRO,
                               mensaje='No se pudo iniciar el proceso de análisis.')
    except BaseException:
        if proceso is not None and proceso.poll() is None:
            proceso.kill()
            proceso.wait(timeout=5)
        raise
    finally:
        actual = IntentoAnalisis.objects.get(pk=intento.pk)
        if actual.estado == IntentoAnalisis.Estado.EN_PROCESO:
            services.fallar_intento(intento=actual, tipo_error=IntentoAnalisis.TipoError.OTRO,
                                   mensaje='El proceso terminó sin publicar un resultado.')
    return True
