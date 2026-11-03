"""Endpoint WSGI interno del motor. El servidor incorporado es solo para desarrollo."""
import argparse
from email import policy
from email.parser import BytesParser
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

from .inference import PredictorYOLO, EntradaInvalida, analizar

MAX_SOLICITUD = 21 * 1024 * 1024
MAX_RESPUESTA = 64 * 1024 * 1024
logger = logging.getLogger(__name__)


def _partes(environ):
    try:
        longitud = int(environ.get('CONTENT_LENGTH', ''))
    except (ValueError, TypeError):
        raise EntradaInvalida('Falta Content-Length válido.') from None
    if not 0 < longitud <= MAX_SOLICITUD:
        raise EntradaInvalida('Solicitud fuera del límite del motor.')
    tipo = environ.get('CONTENT_TYPE', '')
    if not isinstance(tipo, str) or len(tipo) > 300 or '\r' in tipo or '\n' in tipo or not tipo.startswith('multipart/form-data;'):
        raise EntradaInvalida('Usa multipart/form-data.')
    cuerpo = environ['wsgi.input'].read(longitud)
    if len(cuerpo) != longitud:
        raise EntradaInvalida('Cuerpo incompleto.')
    mensaje = BytesParser(policy=policy.default).parsebytes(b'Content-Type: ' + tipo.encode('ascii') + b'\r\nMIME-Version: 1.0\r\n\r\n' + cuerpo)
    if not mensaje.is_multipart() or mensaje.defects:
        raise EntradaInvalida('Multipart inválido.')
    partes = {}
    for parte in mensaje.iter_parts():
        nombre = parte.get_param('name', header='content-disposition')
        if nombre not in ('metadata','servido','retorno') or nombre in partes or parte.is_multipart() or parte.defects:
            raise EntradaInvalida('Campos multipart ajenos, duplicados o inválidos.')
        partes[nombre] = parte.get_payload(decode=True)
    if set(partes) != {'metadata','servido','retorno'} or len(partes['metadata']) > 64 * 1024:
        raise EntradaInvalida('Falta metadata o alguna fotografía.')
    try:
        def invalido(_):
            raise ValueError('Valor no finito')
        metadata = json.loads(partes['metadata'], parse_constant=invalido)
    except (ValueError, UnicodeError, TypeError):
        raise EntradaInvalida('Metadata no es JSON válido.') from None
    return metadata, partes['servido'], partes['retorno']


def aplicacion(predictor, token, version_modelo, *, identidad_verificada=False):
    if not isinstance(token, str) or len(token) < 24:
        raise EntradaInvalida('Configura un token interno de al menos 24 caracteres.')

    def wsgi(environ, start_response):
        def responder(estado, contenido):
            datos = json.dumps(contenido, allow_nan=False).encode()
            if len(datos) > MAX_RESPUESTA:
                estado, datos = '422 Unprocessable Entity', b'{"error":"Respuesta demasiado grande"}'
            start_response(estado, [('Content-Type','application/json'), ('Content-Length',str(len(datos))),
                                     ('Cache-Control','no-store')])
            return [datos]
        auth = environ.get('HTTP_AUTHORIZATION', '')
        if not isinstance(auth, str) or not hmac.compare_digest(auth.encode('utf-8'), ('Bearer ' + token).encode('utf-8')):
            return responder('401 Unauthorized', dict(error='Autenticación interna requerida.'))
        if environ.get('PATH_INFO') != '/v1/analizar-par':
            return responder('404 Not Found', dict(error='Ruta no disponible.'))
        if environ.get('REQUEST_METHOD') != 'POST':
            return responder('405 Method Not Allowed', dict(error='Usa POST.'))
        try:
            metadata, servido, retorno = _partes(environ)
            resultado = analizar(metadata, servido, retorno, predictor, version_modelo=version_modelo,
                                  identidad_verificada=identidad_verificada)
            return responder('200 OK', resultado)
        except (EntradaInvalida, UnicodeError) as exc:
            return responder('422 Unprocessable Entity', dict(error=str(exc)))
        except Exception as exc:
            # Sin imágenes, token ni payload en logs/respuesta.
            logger.error('EVA_INFERENCIA_FALLO clase=%s', type(exc).__name__)
            return responder('503 Service Unavailable', dict(error='La inferencia no pudo completarse.'))
    return wsgi


class SinLogAcceso(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description='Motor visual local con pesos entrenados del catálogo.')
    parser.add_argument('--pesos', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--identidad-verificada', action='store_true', help='Solo tras validar el montaje fijo y geometría de ambas fotos.')
    args = parser.parse_args()
    token = os.environ.get('EVA_VISUAL_TOKEN', '')
    if len(token) < 24:
        parser.error('Configura EVA_VISUAL_TOKEN; no lo pases como argumento.')
    if not args.pesos.is_file():
        parser.error('No existe el archivo de pesos locales.')
    digest = hashlib.sha256()
    with args.pesos.open('rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    version = 'sha256-' + digest.hexdigest()[:40]
    predictor = PredictorYOLO(args.pesos, device=args.device)
    app = aplicacion(predictor, token, version, identidad_verificada=args.identidad_verificada)
    print(f'EVA_VISUAL_VERSION_MODELO={version}', flush=True)
    print(f'Endpoint local: http://127.0.0.1:{args.port}/v1/analizar-par', flush=True)
    with make_server('127.0.0.1', args.port, app, handler_class=SinLogAcceso) as servidor:
        servidor.serve_forever()


if __name__ == '__main__':
    main()
