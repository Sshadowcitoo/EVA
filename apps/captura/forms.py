from dataclasses import dataclass
from io import BytesIO

from django import forms
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.catalogo.models import Plato, TipoPorcion

class ServicioForm(forms.Form):

    plato = forms.ModelChoiceField(
        queryset=Plato.objects.filter(activo=True),
        label= "Plato",
        empty_label="Selecciona un plato",
    )
    tipo_porcion = forms.ModelChoiceField(
        queryset=TipoPorcion.objects.filter(activo=True),
        label= "Tipo de porcion",
        empty_label="Selecciona una porcion",
    )

#--------- Validación de fotografías ----------

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELES = 20_000_000
FORMATOS = {"JPEG": ("image/jpeg", "jpg"), "PNG": ("image/png", "png")}


@dataclass(frozen=True)
class ImagenProcesada:
    contenido: bytes
    tipo: str
    extension: str
    ancho: int
    alto: int

    @property
    def tamano(self):
        return len(self.contenido)


def procesar_imagen(archivo):
    """Valida el contenido real y devuelve una copia sin metadatos."""
    if archivo.size == 0:
        raise forms.ValidationError("El archivo está vacío.", code="vacio")
    if archivo.size > MAX_BYTES:
        raise forms.ValidationError("La foto supera el máximo de 10 MiB.", code="tamano")

    try:
        # Primera lectura: identificar formato y tamaño SIN decodificar los píxeles.
        archivo.seek(0)
        with Image.open(archivo) as imagen:
            formato = imagen.format
            ancho, alto = imagen.size
            if formato not in FORMATOS:
                raise forms.ValidationError("Solo se aceptan fotos JPEG o PNG.", code="formato")
            if ancho * alto > MAX_PIXELES:
                raise forms.ValidationError(
                    "La foto supera los 20 millones de píxeles.", code="pixeles"
                )
            imagen.verify()

        # Segunda lectura: corregir orientación y re-codificar sin metadatos.
        archivo.seek(0)
        with Image.open(archivo) as imagen:
            imagen.load()
            imagen = ImageOps.exif_transpose(imagen)
            salida = BytesIO()
            if formato == "JPEG":
                if imagen.mode not in ("RGB", "L"):
                    imagen = imagen.convert("RGB")
                imagen.save(salida, "JPEG", quality=95, subsampling=0)
            else:
                imagen.save(salida, "PNG", optimize=True)
            ancho, alto = imagen.size
    except forms.ValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise forms.ValidationError(
            "El archivo no es una imagen válida o está dañado.", code="corrupto"
        ) from error

    tipo, extension = FORMATOS[formato]
    return ImagenProcesada(salida.getvalue(), tipo, extension, ancho, alto)


class FotoForm(forms.Form):
    foto = forms.FileField(label="Fotografía")

    def clean_foto(self):
        # Al validar, el campo deja de ser el archivo subido
        # y pasa a ser la imagen ya procesada y limpia.
        return procesar_imagen(self.cleaned_data["foto"])