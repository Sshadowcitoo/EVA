"""Factory WSGI y comprobación privada; no descarga pesos ni activa criterios."""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

from .inference import EntradaInvalida, PredictorYOLO
from .server import aplicacion


def configuracion():
    token = os.environ.get('EVA_VISUAL_TOKEN', '')
    pesos = Path(os.environ.get('EVA_VISUAL_PESOS', ''))
    version = os.environ.get('EVA_VISUAL_VERSION_MODELO', '')
    if (len(token) < 24 or not pesos.is_absolute() or not pesos.is_file() or pesos.suffix.lower() != '.pt'
            or os.environ.get('EVA_VISUAL_ENDPOINT') != 'http://127.0.0.1:8765/v1/analizar-par'):
        raise EntradaInvalida('Configura token interno y ruta absoluta a pesos .pt locales.')
    digest = hashlib.sha256()
    with pesos.open('rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    if version != 'sha256-' + digest.hexdigest()[:40]:
        raise EntradaInvalida('La versión configurada no corresponde a los pesos locales.')
    return pesos, token, version


def create_app():
    pesos, token, version = configuracion()
    # Comparabilidad requiere validación explícita del montaje; no se activa aquí.
    return aplicacion(PredictorYOLO(pesos, device='cpu'), token, version)


def comprobar():
    _, token, version = configuracion()
    peticion = Request('http://127.0.0.1:8765/v1/salud', headers={'Authorization': 'Bearer ' + token})
    class SinRedireccion(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    with build_opener(ProxyHandler({}), SinRedireccion()).open(peticion, timeout=3) as respuesta:
        datos = respuesta.read(4097)
        if len(datos) > 4096 or json.loads(datos) != {'estado': 'LISTO', 'version_modelo': version}:
            raise EntradaInvalida('El motor no confirma la versión esperada.')
    print('EVA_MOTOR_LISTO')


if __name__ == '__main__':
    # Errores genéricos: no imprimir tokens, URL, respuesta o trazas del entorno.
    try:
        comprobar()
    except Exception:
        raise SystemExit('EVA_MOTOR_NO_DISPONIBLE: revisa configuración y servicio privado.') from None
