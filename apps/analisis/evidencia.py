"""Lectura privada y validación de bytes; ningún UUID autoriza por sí solo."""
import hashlib
from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from apps.captura import storage
from apps.captura.protocolo import CRITERIOS, VERSION

MAX_FOTO = 10 * 1024 * 1024
MAX_MASCARA = 8 * 1024 * 1024
MAX_PIXELES = 20_000_000
COLORES = ('#1768b0', '#2f8a3c', '#c97a00', '#8a3fb0', '#b0392f', '#00796b', '#6d4c41', '#546e7a')


def color_clave(codigo):
    return int(hashlib.sha256(codigo.encode()).hexdigest()[:8], 16) % 8 + 1


def leer(registro, limite):
    with storage.abrir(registro.clave_archivo, backend=registro.backend,
                       version_id=registro.version_id) as archivo:
        datos = archivo.read(limite + 1)
    if len(datos) > limite or not datos:
        raise ValidationError('Archivo vacío o demasiado grande.')
    if registro.hash_sha256 and hashlib.sha256(datos).hexdigest() != registro.hash_sha256:
        raise ValidationError('El archivo no coincide con su huella registrada.')
    return datos


def imagen(datos, dimensiones, formatos):
    try:
        with Image.open(BytesIO(datos)) as foto:
            if (foto.format not in formatos or foto.size != dimensiones
                    or foto.width * foto.height > MAX_PIXELES
                    or getattr(foto, 'n_frames', 1) != 1):
                raise ValidationError('Formato o geometría de imagen no válidos.')
            foto.verify()
        with Image.open(BytesIO(datos)) as foto:
            foto.load()
            return foto.copy()
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValidationError('La imagen no se puede validar.') from error


def foto_bytes(foto):
    if not foto.disponible or not foto.vigente:
        raise ValidationError('La fotografía no está disponible.')
    if foto.tipo_contenido not in ('image/jpeg', 'image/png'):
        raise ValidationError('Tipo de fotografía no admitido.')
    datos = leer(foto, MAX_FOTO)
    imagen(datos, (foto.ancho, foto.alto), ('JPEG', 'PNG'))
    return datos


def protocolo_completo(foto):
    return (foto.protocolo_version == VERSION and isinstance(foto.checklist, dict)
            and set(foto.checklist) == set(CRITERIOS)
            and all(valor is True for valor in foto.checklist.values()))


def mascara(datos, foto):
    if len(datos) > MAX_MASCARA:
        raise ValidationError('Máscara demasiado grande.')
    original = imagen(datos, (foto.ancho, foto.alto), ('PNG',))
    if original.mode not in ('1', 'L'):
        raise ValidationError('La máscara debe ser binaria, de un solo canal.')
    gris = original.convert('L')
    histograma = gris.histogram()
    if sum(histograma[1:255]):
        raise ValidationError('La máscara solo puede contener 0 y 255.')
    return gris, histograma[255]


def superposicion(datos, foto, codigo):
    gris, _ = mascara(datos, foto)
    salida = Image.new('RGBA', gris.size, COLORES[color_clave(codigo) - 1])
    salida.putalpha(gris)
    buffer = BytesIO()
    salida.save(buffer, format='PNG')
    return buffer.getvalue()
