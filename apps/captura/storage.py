
import logging
import base64
import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class ErrorAlmacenamiento(Exception):
    """Fallo al guardar, leer o eliminar un archivo."""


class ArchivoNoEncontrado(ErrorAlmacenamiento):
    """La clave no corresponde a ningún archivo guardado."""


@dataclass(frozen=True)
class Guardado:
    backend: str
    clave: str
    hash_sha256: str
    version_id: str = ""


def _backend(backend):
    selected = backend or settings.EVA_STORAGE_BACKEND
    if selected not in ("local", "s3"):
        raise ErrorAlmacenamiento("Almacenamiento no disponible.")
    return selected


def _validar_clave(clave):
    if (not isinstance(clave, str) or not clave or PureWindowsPath(clave).anchor
            or "\\" in clave or "\x00" in clave
            or any(part in ("", ".", "..") for part in clave.split("/"))):
        raise ErrorAlmacenamiento("Clave de almacenamiento no válida.")
    return clave


def _prefijo():
    prefix = settings.EVA_S3_PREFIX.rstrip("/")
    _validar_clave(prefix)
    if not settings.EVA_S3_BUCKET or not settings.EVA_S3_REGION:
        raise ErrorAlmacenamiento("S3 no está configurado.")
    return prefix + "/"


def _clave_s3(clave):
    _validar_clave(clave)
    if not clave.startswith(_prefijo()):
        raise ErrorAlmacenamiento("La clave no pertenece al prefijo autorizado.")
    return clave


def _cliente_s3():
    # Cadena estándar del SDK: en EC2 se usa el rol, sin access keys en el código.
    return boto3.client("s3", region_name=settings.EVA_S3_REGION, config=Config(
        connect_timeout=5, read_timeout=15, retries={"max_attempts": 2},
    ))


def generar_clave(servicio_id, etapa, extension):
    """Clave opaca: servicio/etapa/uuid. Sin nombres de archivo ni datos personales."""
    return f"servicios/{servicio_id}/{etapa.lower()}/{uuid.uuid4().hex}.{extension}"


def _ruta(clave):
    _validar_clave(clave)
    # La clave debe ser relativa. PureWindowsPath detecta "/x", "\\x" y "C:\\x".
    if not clave or PureWindowsPath(clave).anchor:
        raise ErrorAlmacenamiento("Clave de almacenamiento no válida.")
    raiz = Path(settings.EVA_CAPTURE_PRIVATE_ROOT).resolve()
    ruta = (raiz / clave).resolve()
    # Impide claves como "../../config/settings.py" que escapen de la carpeta.
    if raiz not in ruta.parents:
        raise ErrorAlmacenamiento("Clave de almacenamiento no válida.")
    return ruta


def guardar(contenido, clave, *, tipo_contenido="application/octet-stream", backend=None):
    """Guarda bytes en la clave indicada. Nunca sobrescribe un archivo existente."""
    selected = _backend(backend)
    digest = hashlib.sha256(contenido).hexdigest()
    if selected == "s3":
        key = _prefijo() + _validar_clave(clave)
        try:
            result = _cliente_s3().put_object(
                Bucket=settings.EVA_S3_BUCKET, Key=key, Body=contenido,
                ContentType=tipo_contenido, ServerSideEncryption="AES256",
                IfNoneMatch="*", Metadata={"sha256": digest},
                ChecksumSHA256=base64.b64encode(bytes.fromhex(digest)).decode(),
            )
        except (BotoCoreError, ClientError, OSError) as error:
            if not isinstance(error, ClientError):
                # Un timeout puede ocurrir después de que S3 reciba los bytes.
                # Registrar la clave propia para reconciliar, sin borrar a ciegas.
                logger.error("EVA_CAPTURE_S3_UNCONFIRMED clave=%s", key)
            raise ErrorAlmacenamiento("No se pudo guardar la fotografía en S3.") from error
        return Guardado("s3", key, digest, result.get("VersionId") or "")
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
    return Guardado("local", clave, digest)


def abrir(clave, *, backend=None, version_id=""):
    """Devuelve el archivo abierto en modo binario. Quien lo usa debe cerrarlo."""
    if _backend(backend) == "s3":
        key = _clave_s3(clave)
        arguments = {"Bucket": settings.EVA_S3_BUCKET, "Key": key}
        if version_id:
            arguments["VersionId"] = version_id
        try:
            return _cliente_s3().get_object(**arguments)["Body"]
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "NoSuchVersion", "404"):
                raise ArchivoNoEncontrado("La fotografía no está disponible.") from error
            raise ErrorAlmacenamiento("No se pudo abrir la fotografía en S3.") from error
        except (BotoCoreError, OSError) as error:
            raise ErrorAlmacenamiento("No se pudo abrir la fotografía en S3.") from error
    try:
        return open(_ruta(clave), "rb")
    except FileNotFoundError as error:
        raise ArchivoNoEncontrado("El archivo no existe.") from error
    except OSError as error:
        raise ErrorAlmacenamiento("No se pudo leer el archivo.") from error


def eliminar(clave, *, backend=None, version_id=""):
    """Elimina el archivo. Si ya no existe, no es un error (permite reintentar)."""
    if _backend(backend) == "s3":
        key = _clave_s3(clave)
        arguments = {"Bucket": settings.EVA_S3_BUCKET, "Key": key}
        if version_id:
            arguments["VersionId"] = version_id
        try:
            _cliente_s3().delete_object(**arguments)
        except (BotoCoreError, ClientError, OSError) as error:
            raise ErrorAlmacenamiento("No se pudo eliminar la fotografía en S3.") from error
        return
    try:
        _ruta(clave).unlink(missing_ok=True)
    except OSError as error:
        raise ErrorAlmacenamiento("No se pudo eliminar el archivo.") from error
