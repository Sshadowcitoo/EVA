"""Cliente interno v1: endpoint fijo, sin redirecciones ni URLs del motor."""
import base64
import binascii
import json
import logging
import math
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import ImageChops

from .configuration import criterios_componente
from .evidencia import foto_bytes, mascara, protocolo_completo

logger = logging.getLogger(__name__)
MAX_RESPUESTA = 64 * 1024 * 1024


class SinMotor(ValidationError):
    pass


def configuracion():
    endpoint = settings.EVA_VISUAL_ENDPOINT
    token = settings.EVA_VISUAL_TOKEN
    url = urlsplit(endpoint)
    local = url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1')
    if (not endpoint or not settings.EVA_VISUAL_VERSION_MODELO or not token
            or not (url.scheme == 'https' or local) or not url.hostname
            or url.username or url.password or url.query or url.fragment
            or settings.EVA_VISUAL_ORIGEN not in ('REAL', 'SIMULADO')):
        raise SinMotor('El motor no está configurado: falta endpoint, versión o autenticación interna válida.')
    return endpoint, token


class SinRedireccion(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _multipart(metadata, fotos):
    boundary = uuid.uuid4().hex
    partes = [(f'--{boundary}\r\nContent-Disposition: form-data; name="metadata"\r\n'
               'Content-Type: application/json\r\n\r\n').encode() + json.dumps(metadata).encode() + b'\r\n']
    for etapa, (foto, datos) in fotos.items():
        partes.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{etapa.lower()}"; '
                       f'filename="{etapa.lower()}.bin"\r\nContent-Type: {foto.tipo_contenido}\r\n\r\n').encode()
                      + datos + b'\r\n')
    partes.append(f'--{boundary}--\r\n'.encode())
    return b''.join(partes), boundary


def llamar(intento, plazo):
    endpoint, token = configuracion()
    analisis = intento.analisis
    fotos = {etapa: (foto, foto_bytes(foto)) for etapa, foto in (
        ('SERVIDO', analisis.foto_servido), ('RETORNO', analisis.foto_retorno))}
    componentes = list(analisis.servicio.composicion.all())
    if not componentes or len(componentes) > 32:
        raise ValidationError('Composición fuera del límite del motor.')
    metadata = dict(schema_version=1, request_id=str(intento.pk), servicio_id=str(analisis.servicio_id),
                    version_modelo=analisis.version_modelo, version_configuracion=analisis.version_configuracion,
                    origen=analisis.origen,
                    componentes=[dict(id=str(c.pk), codigo=c.componente_codigo) for c in componentes])
    cuerpo, boundary = _multipart(metadata, fotos)
    restante = plazo - time.monotonic()
    if restante <= 0:
        raise TimeoutError()
    request = Request(endpoint, data=cuerpo, method='POST', headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/json',
        'Content-Type': 'multipart/form-data; boundary=' + boundary})
    logger.info('EVA_MOTOR_INICIO intento=%s fecha=%s', intento.pk, datetime.now(timezone.utc).isoformat())
    # El supervisor del proceso impone el presupuesto TOTAL, incluido el cuerpo JSON.
    with build_opener(ProxyHandler({}), SinRedireccion()).open(request, timeout=min(restante, 25)) as response:
        if response.headers.get_content_type() != 'application/json' or response.headers.get('Content-Encoding'):
            raise ValidationError('El motor no devolvió JSON sin comprimir.')
        datos = response.read(MAX_RESPUESTA + 1)
    logger.info('EVA_MOTOR_FIN intento=%s fecha=%s', intento.pk, datetime.now(timezone.utc).isoformat())
    if len(datos) > MAX_RESPUESTA or time.monotonic() > plazo:
        raise ValidationError('Respuesta demasiado grande o fuera de plazo.')
    def invalido(_):
        raise ValueError('Número no finito')
    try:
        respuesta = json.loads(datos, parse_constant=invalido)
    except (ValueError, UnicodeError) as error:
        raise ValidationError('JSON del motor no válido.') from error
    return validar(respuesta, intento, componentes)


def validar(respuesta, intento, componentes):
    a = intento.analisis
    esperados = dict(schema_version=1, request_id=str(intento.pk), version_modelo=a.version_modelo,
                     version_configuracion=a.version_configuracion, origen=a.origen)
    if not isinstance(respuesta, dict) or any(respuesta.get(k) != v for k, v in esperados.items()):
        raise ValidationError('Respuesta de otro intento, modelo, configuración u origen.')
    lista = respuesta.get('componentes')
    if not isinstance(lista, list) or len(lista) > len(componentes):
        raise ValidationError('Lista de componentes no válida.')
    por_id = {str(c.pk): c for c in componentes}
    vistos, resultados, archivos = set(), [], []
    ocupadas = {}
    fotos = {'SERVIDO': a.foto_servido, 'RETORNO': a.foto_retorno}
    for item in lista:
        if not isinstance(item, dict) or str(item.get('id')) not in por_id or str(item['id']) in vistos:
            raise ValidationError('Componente ajeno o duplicado.')
        clave = str(item['id'])
        vistos.add(clave)
        comp = por_id[clave]
        if type(item.get('comparable')) is not bool or type(item.get('oculto')) is not bool:
            raise ValidationError('Comparabilidad y ocultación deben ser booleanos explícitos.')
        confianza = item.get('confianza')
        if confianza is not None and (type(confianza) not in (int, float)
                or not math.isfinite(confianza) or not 0 <= confianza <= 1):
            raise ValidationError('Confianza no válida.')
        mascaras = item.get('mascaras', [])
        if not isinstance(mascaras, list) or len(mascaras) > 2:
            raise ValidationError('Máscaras no válidas.')
        areas = {}
        for art in mascaras:
            if not isinstance(art, dict) or art.get('etapa') not in fotos or art['etapa'] in areas:
                raise ValidationError('Etapa de máscara inválida o repetida.')
            etapa = art['etapa']
            foto = fotos[etapa]
            codificado = art.get('png_base64')
            if not isinstance(codificado, str) or len(codificado) > 12 * 1024 * 1024:
                raise ValidationError('Máscara codificada inválida.')
            try:
                datos = base64.b64decode(codificado, validate=True)
            except (ValueError, binascii.Error) as error:
                raise ValidationError('La máscara no es base64 válido.') from error
            if (art.get('ancho'), art.get('alto')) != (foto.ancho, foto.alto):
                raise ValidationError('Geometría declarada incoherente.')
            gris, area = mascara(datos, foto)
            if etapa in ocupadas and ImageChops.darker(ocupadas[etapa], gris).getbbox():
                raise ValidationError('Las máscaras de componentes se solapan.')
            ocupadas[etapa] = ImageChops.lighter(ocupadas[etapa], gris) if etapa in ocupadas else gris
            areas[etapa] = area
            archivos.append(dict(servicio_componente=comp, etapa=etapa, datos=datos,
                                 ancho=foto.ancho, alto=foto.alto))
        for etapa, campo in [('SERVIDO', 'area_inicial'), ('RETORNO', 'area_residual')]:
            declarado = item.get(campo)
            if declarado is not None and (type(declarado) not in (int, float)
                    or not math.isfinite(declarado) or declarado != areas.get(etapa)):
                raise ValidationError('El área declarada no coincide con los píxeles de la máscara.')
        criterios = criterios_componente(comp.componente_codigo)
        # v1 solo acepta identidad sobre dos fotos del mismo tamaño. Otras ROI no se certifican.
        geometria = (respuesta.get('transformacion') == {'tipo': 'IDENTIDAD', 'escala_comun': True}
                     and (a.foto_servido.ancho, a.foto_servido.alto) == (a.foto_retorno.ancho, a.foto_retorno.alto))
        comparable = (item['comparable'] and geometria and criterios['comparabilidad_aprobada']
                      and criterios['version_configuracion'] == a.version_configuracion
                      and all(protocolo_completo(f) for f in fotos.values()))
        umbral = criterios['umbral_confianza'] if criterios['version_configuracion'] == a.version_configuracion else None
        resultados.append(dict(servicio_componente=comp, area_inicial=areas.get('SERVIDO'),
                               area_residual=areas.get('RETORNO'), confianza=confianza,
                               umbral_confianza=umbral, criterio=a.version_configuracion,
                               comparable=bool(comparable), oculto=item['oculto']))
    return resultados, archivos
