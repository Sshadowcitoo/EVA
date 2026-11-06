from dataclasses import dataclass
from io import BytesIO
import re

from django import forms
from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from apps.catalogo.models import Plato, TipoPorcion

from .models import Bandeja, Servicio

class ServicioForm(forms.Form):
    sede = forms.ChoiceField(label="Sede", required=False)
    modalidad = forms.ChoiceField(label="Modalidad de servicio", required=False)
    lote_preparacion = forms.CharField(label="Lote de preparación", max_length=64, required=False,
        help_text="Usa el mismo código para platos de una misma preparación; no es el número de bandeja.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .contexto import configuracion
        config = configuracion()
        self.establecimiento_nombre = config['establecimiento']['nombre']
        self.datos_contexto = None
        for campo, plural in [('sede', 'sedes'), ('modalidad', 'modalidades')]:
            opciones = config[plural]
            self.fields[campo].choices = [('', 'Sin especificar')] + [(o['codigo'], o['nombre']) for o in opciones]
            if len(opciones) == 1:
                self.fields[campo].initial = opciones[0]['codigo']
        self.order_fields(['plato', 'tipo_porcion', 'sede', 'modalidad', 'lote_preparacion'])

    def clean(self):
        datos = super().clean()
        campos = ('sede', 'modalidad', 'lote_preparacion')
        if not any(datos.get(c) for c in campos):
            return datos  # Compatibilidad: sin contexto no podrá fundamentar comparaciones.
        if not all(datos.get(c) for c in campos):
            raise forms.ValidationError('Completa sede, modalidad y lote juntos, o déjalos todos sin especificar.')
        from .contexto import preparar
        self.datos_contexto = {c: datos[c] for c in campos}
        try:
            preparar(self.datos_contexto)
        except forms.ValidationError as exc:
            self.datos_contexto = None
            raise forms.ValidationError(exc.messages) from None
        return datos

    plato = forms.ModelChoiceField(
        queryset=Plato.objects.filter(activo=True),
        label= "Plato",
        empty_label="Selecciona un plato",
    )
    tipo_porcion = forms.ModelChoiceField(
        queryset=TipoPorcion.objects.filter(activo=True),
        label="Tipo de porción",
        empty_label="Selecciona una porción",
    )

#--------- Validación de fotografías ----------

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
    if archivo.size > settings.EVA_CAPTURE_MAX_BYTES:
        raise forms.ValidationError("La foto supera el tamaño permitido.", code="tamano")

    try:
        # Primera lectura: identificar formato y tamaño SIN decodificar los píxeles.
        archivo.seek(0)
        with Image.open(archivo) as imagen:
            formato = imagen.format
            ancho, alto = imagen.size
            if formato not in FORMATOS or FORMATOS[formato][0] not in settings.EVA_CAPTURE_ALLOWED_TYPES:
                raise forms.ValidationError("Solo se aceptan fotos JPEG o PNG.", code="formato")
            if ancho * alto > settings.EVA_CAPTURE_MAX_PIXELS:
                raise forms.ValidationError(
                    "La foto supera los 20 millones de píxeles.", code="pixeles"
                )
            imagen.verify()

        # Segunda lectura: corregir orientación y re-codificar sin metadatos.
        archivo.seek(0)
        with Image.open(archivo) as imagen:
            imagen.load()
            imagen = ImageOps.exif_transpose(imagen)
            # PNG puede volver a guardar EXIF desde image.info aunque no se pase
            # exif= a save(). Copiar solo píxeles elimina también metadatos privados.
            modo = "RGBA" if "A" in imagen.getbands() or "transparency" in imagen.info else "RGB"
            pixeles = imagen.convert(modo)
            limpia = Image.new(modo, pixeles.size)
            limpia.paste(pixeles)
            salida = BytesIO()
            if formato == "JPEG":
                limpia.convert("RGB").save(salida, "JPEG", quality=95, subsampling=0)
            else:
                limpia.save(salida, "PNG", optimize=True)
            ancho, alto = limpia.size
    except forms.ValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as error:
        raise forms.ValidationError(
            "El archivo no es una imagen válida o está dañado.", code="corrupto"
        ) from error

    tipo, extension = FORMATOS[formato]
    if salida.tell() > settings.EVA_CAPTURE_MAX_BYTES:
        raise forms.ValidationError("La imagen procesada supera el tamaño permitido.", code="tamano")
    return ImagenProcesada(salida.getvalue(), tipo, extension, ancho, alto)


class FotoForm(forms.Form):
    foto = forms.FileField(label="Fotografía")
    plato_visible = forms.BooleanField(label="El plato completo está dentro del encuadre.")
    vista_superior = forms.BooleanField(label="La fotografía está tomada desde arriba.")
    luz_adecuada = forms.BooleanField(label="Hay luz suficiente y la imagen se distingue con claridad.")

    def confirmaciones(self):
        from .protocolo import CRITERIOS
        return {campo: self.cleaned_data[campo] for campo in CRITERIOS}

    def clean_foto(self):
        # Al validar, el campo deja de ser el archivo subido
        # y pasa a ser la imagen ya procesada y limpia.
        return procesar_imagen(self.cleaned_data["foto"])


class ConfirmarRetornoForm(forms.Form):
    confirmar = forms.BooleanField(
        label="Confirmo que la bandeja y el plato corresponden al servicio mostrado.",
        required=True,
    )


class NumeroBandejaField(forms.IntegerField):
    def __init__(self, **kwargs):
        super().__init__(
            label="Número de bandeja", required=False, min_value=1, max_value=2_147_483_647,
            widget=forms.TextInput(attrs={"inputmode": "numeric", "maxlength": 10, "autocomplete": "off",
                                          "placeholder": "Ejemplo: 001"}),
            **kwargs,
        )

    def to_python(self, value):
        if value not in self.empty_values and not re.fullmatch(r"[0-9]{1,10}", str(value).strip()):
            raise forms.ValidationError("Escribe un número de bandeja de hasta 10 dígitos (0–9).")
        return super().to_python(value)


class BuscarBandejaForm(forms.Form):
    numero = NumeroBandejaField()
    etiqueta = forms.CharField(
        label="Código de etiqueta", max_length=32, required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "data-qr-value": ""}),
    )

    def clean(self):
        data = super().clean()
        if not self.errors and bool(data.get("numero")) == bool(data.get("etiqueta")):
            raise forms.ValidationError("Escribe el número de bandeja o escanea su etiqueta, solo uno.")
        return data


class BuscarGestionForm(forms.Form):
    numero = NumeroBandejaField()
    servicio = forms.UUIDField(label="ID del servicio", required=False)

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        numero, servicio = data.get("numero"), data.get("servicio")
        if bool(numero) == bool(servicio):
            raise forms.ValidationError("Indica el número de bandeja o el ID del servicio, solo uno.")
        if numero and not Bandeja.objects.filter(numero=numero).exists():
            self.add_error("numero", "No se encontró una bandeja con ese número.")
        if servicio and not Servicio.objects.filter(pk=servicio).exists():
            self.add_error("servicio", "No se encontró un servicio con ese ID.")
        return data


class MotivoOperacionForm(forms.Form):
    motivo = forms.CharField(label="Motivo", max_length=1000, widget=forms.Textarea(attrs={"rows": 3}))
    confirmar = forms.BooleanField(label="Confirmo esta operación y sus efectos.")


class ReemplazarEtiquetaForm(MotivoOperacionForm):
    etiqueta_actual = forms.CharField(max_length=32, widget=forms.HiddenInput)
