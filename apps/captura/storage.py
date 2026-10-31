
import logging
import uuid
from pathlib import Path, PureWindowsPath

from django.conf import settings

logger = logging.getLogger(__name__)


class ErrorAlmacenamiento(Exception):
    """Fallo al guardar, leer o eliminar un archivo."""


class ArchivoNoEncontrado(ErrorAlmacenamiento):
    """La clave no corresponde a ningún archivo guardado."""


def generar_clave(servicio_id, etapa, extension):
    """Clave opaca: servicio/etapa/uuid. Sin nombres de archivo ni datos personales."""
    return f"servicios/{servicio_id}/{etapa.lower()}/{uuid.uuid4().hex}.{extension}"


def _ruta(clave):
    if settings.EVA_STORAGE_BACKEND != "local":
        raise ErrorAlmacenamiento("El adaptador solicitado todavía no está disponible.")
    # La clave debe ser relativa. PureWindowsPath detecta "/x", "\\x" y "C:\\x".
    if not clave or PureWindowsPath(clave).anchor:
        raise ErrorAlmacenamiento("Clave de almacenamiento no válida.")
    raiz = Path(settings.EVA_CAPTURE_PRIVATE_ROOT).resolve()
    ruta = (raiz / clave).resolve()
    # Impide claves como "../../config/settings.py" que escapen de la carpeta.
    if raiz not in ruta.parents:
        raise ErrorAlmacenamiento("Clave de almacenamiento no válida.")
    return ruta


def guardar(contenido, clave):
    """Guarda bytes en la clave indicada. Nunca sobrescribe un archivo existente."""
    ruta = _ruta(clave)
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "xb") as destino:
            destino.write(contenido)
    except FileExistsError as error:
        raise ErrorAlmacenamiento("Ya existe un archivo con esa clave.") from error
    except OSError as error:
        try:
            ruta.unlink(missing_ok=True)
        except OSError:
            logger.error("EVA_CAPTURE_ORPHAN backend=local clave=%s", clave)
        raise ErrorAlmacenamiento("No se pudo guardar el archivo.") from error


def abrir(clave):
    """Devuelve el archivo abierto en modo binario. Quien lo usa debe cerrarlo."""
    try:
        return open(_ruta(clave), "rb")
    except FileNotFoundError as error:
        raise ArchivoNoEncontrado("El archivo no existe.") from error
    except OSError as error:
        raise ErrorAlmacenamiento("No se pudo leer el archivo.") from error


def eliminar(clave):
    """Elimina el archivo. Si ya no existe, no es un error (permite reintentar)."""
    try:
        _ruta(clave).unlink(missing_ok=True)
    except OSError as error:
        raise ErrorAlmacenamiento("No se pudo eliminar el archivo.") from error
