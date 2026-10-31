import secrets
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

from apps.catalogo import models as catalogo


class Servicio(models.Model):
    # Etiquetas del primer avance. Solo sirven para leer registros históricos;
    # las nuevas altas usan el catálogo.
    class Plato(models.TextChoices):
        ARROZ_CON_POLLO = "arroz_con_pollo", "Arroz con pollo"
        LENTEJAS = "lentejas", "Lentejas"

    class TipoPorcion(models.TextChoices):
        PEQUENA = "pequena", "Pequeña"
        REGULAR = "regular", "Regular"
        GRANDE = "grande", "Grande"

    class EstadoCaptura(models.TextChoices):
        PENDIENTE_SERVIDO = "PENDIENTE_SERVIDO", "Pendiente de servido"
        EN_ESPERA_RETORNO = "EN_ESPERA_RETORNO", "En espera de retorno"
        PAR_COMPLETO = "PAR_COMPLETO", "Par completo"
        ANULADO = "ANULADO", "Anulado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Instantánea: código y nombre tal como estaban al crear el servicio.
    plato = models.CharField(max_length=50)
    tipo_porcion = models.CharField(max_length=20)
    plato_nombre = models.CharField(max_length=100, blank=True, default="")
    porcion_nombre = models.CharField(max_length=100, blank=True, default="")

    # Referencias al catálogo. Nulas en los registros anteriores al catálogo.
    plato_catalogo = models.ForeignKey(
        "catalogo.Plato",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="servicios",
    )
    porcion_catalogo = models.ForeignKey(
        "catalogo.TipoPorcion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="servicios",
    )

    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="servicios_creados",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Estado de captura (fotos). Vacío en los servicios históricos, que no
    # tienen captura. No indica análisis, revisión ni aprobación.
    estado_captura = models.CharField(
        max_length=20, choices=EstadoCaptura.choices, blank=True, default=""
    )
    anulado_motivo = models.TextField(blank=True, default="")
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="servicios_anulados",
    )
    anulado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        permissions = [("anular_servicio", "Puede anular servicios")]

    def __str__(self):
        return f"{self.id} - {self.get_plato_display()}"

    def get_plato_display(self):
        return self.plato_nombre or self.plato

    def get_tipo_porcion_display(self):
        return self.porcion_nombre or self.tipo_porcion

    @classmethod
    def registrar(cls, *, plato, porcion, usuario=None, bandeja=None):
        """Crea un servicio con su instantánea de catálogo en una sola transacción.

        Sin bandeja se comporta como antes (servicio sin captura). Con bandeja
        también la asigna y deja el servicio pendiente de servido; si algo falla
        no queda ninguna fila.
        """
        with transaction.atomic():
            try:
                plato_actual = catalogo.Plato.objects.get(pk=plato.pk, activo=True)
            except catalogo.Plato.DoesNotExist:
                raise ValidationError("El plato no está activo en el catálogo.")
            try:
                porcion_actual = catalogo.TipoPorcion.objects.get(
                    pk=porcion.pk, activo=True
                )
            except catalogo.TipoPorcion.DoesNotExist:
                raise ValidationError(
                    "El tipo de porción no está activo en el catálogo."
                )

            servicio = cls.objects.create(
                plato=plato_actual.codigo,
                plato_nombre=plato_actual.nombre,
                tipo_porcion=porcion_actual.codigo,
                porcion_nombre=porcion_actual.nombre,
                plato_catalogo=plato_actual,
                porcion_catalogo=porcion_actual,
                creado_por=usuario,
                estado_captura=(
                    cls.EstadoCaptura.PENDIENTE_SERVIDO if bandeja is not None else ""
                ),
            )

            relaciones = catalogo.PlatoComponente.objects.filter(
                plato=plato_actual, activo=True, componente__activo=True
            ).select_related("componente")
            ServicioComponente.objects.bulk_create(
                ServicioComponente(
                    servicio=servicio,
                    componente_codigo=rel.componente.codigo,
                    componente_nombre=rel.componente.nombre,
                )
                for rel in relaciones
            )
            if bandeja is not None:
                from apps.captura import services

                services.asignar_bandeja(servicio=servicio, bandeja=bandeja)
            return servicio


class ServicioComponente(models.Model):
    """Composición del plato tal como era al crear el servicio."""

    servicio = models.ForeignKey(
        Servicio, on_delete=models.CASCADE, related_name="composicion"
    )
    componente_codigo = models.CharField(max_length=50)
    componente_nombre = models.CharField(max_length=100)

    class Meta:
        ordering = ["componente_nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["servicio", "componente_codigo"],
                name="servicio_componente_unico",
            )
        ]

    def __str__(self):
        return f"{self.servicio_id} - {self.componente_nombre}"


def generar_codigo_etiqueta():
    return secrets.token_urlsafe(16)


class Bandeja(models.Model):
    """Soporte físico reutilizable. No representa una comida."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.PositiveIntegerField(unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"Bandeja {self.numero}"


class EtiquetaBandeja(models.Model):
    """Código del QR físico. Solo una vigente por bandeja; se revoca, no se borra."""

    codigo = models.CharField(
        max_length=32, unique=True, default=generar_codigo_etiqueta, editable=False
    )
    bandeja = models.ForeignKey(
        Bandeja, on_delete=models.PROTECT, related_name="etiquetas"
    )
    emitida_en = models.DateTimeField(default=timezone.now)
    revocada_en = models.DateTimeField(null=True, blank=True)
    revocada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="etiquetas_revocadas",
    )
    motivo_revocacion = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-emitida_en"]
        permissions = [
            (
                "reemplazar_etiquetabandeja",
                "Puede reemplazar la etiqueta de una bandeja",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["bandeja"],
                condition=Q(revocada_en__isnull=True),
                name="etiqueta_vigente_unica_por_bandeja",
            )
        ]

    @property
    def vigente(self):
        return self.revocada_en is None

    def __str__(self):
        return f"{self.bandeja} ({'vigente' if self.vigente else 'revocada'})"


class AsignacionBandeja(models.Model):
    """Uso de una bandeja por un servicio. Abierta mientras fin es nulo."""

    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="asignaciones"
    )
    bandeja = models.ForeignKey(
        Bandeja, on_delete=models.PROTECT, related_name="asignaciones"
    )
    inicio = models.DateTimeField(default=timezone.now)
    fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["bandeja"],
                condition=Q(fin__isnull=True),
                name="una_asignacion_abierta_por_bandeja",
            ),
            models.UniqueConstraint(
                fields=["servicio"],
                condition=Q(fin__isnull=True),
                name="una_asignacion_abierta_por_servicio",
            ),
        ]

    def __str__(self):
        return f"{self.servicio_id} -> {self.bandeja}"


class FotografiaServicio(models.Model):
    """Fotografía aceptada de una etapa. Guarda metadatos; el archivo vive en storage."""

    class Etapa(models.TextChoices):
        SERVIDO = "SERVIDO", "Servido"
        RETORNO = "RETORNO", "Retorno"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="fotografias"
    )
    etapa = models.CharField(max_length=10, choices=Etapa.choices)
    backend = models.CharField(max_length=20, default="local")
    clave_archivo = models.CharField(max_length=255)
    tipo_contenido = models.CharField(max_length=50)
    tamano_bytes = models.PositiveIntegerField()
    hash_sha256 = models.CharField(max_length=64, blank=True, default="")
    version_id = models.CharField(max_length=255, blank=True, default="")
    ancho = models.PositiveIntegerField()
    alto = models.PositiveIntegerField()
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fotografias_servicio",
    )
    fecha = models.DateTimeField(auto_now_add=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        ordering = ["fecha"]
        constraints = [
            models.UniqueConstraint(
                fields=["servicio", "etapa"],
                condition=Q(vigente=True),
                name="fotografia_vigente_unica_por_servicio_etapa",
            )
        ]

    def __str__(self):
        return f"{self.servicio_id} - {self.etapa}"


class SesionCaptura(models.Model):
    """Solicitud temporal para capturar desde otro dispositivo (QR temporal).

    Solo se guarda el digest del token; el token en claro se entrega una vez.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"
        EXPIRADA = "EXPIRADA", "Expirada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="sesiones_captura"
    )
    etapa = models.CharField(max_length=10, choices=FotografiaServicio.Etapa.choices)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sesiones_captura",
    )
    token_digest = models.CharField(max_length=64, unique=True, editable=False)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )
    creada_en = models.DateTimeField(default=timezone.now)
    expira_en = models.DateTimeField()
    completada_en = models.DateTimeField(null=True, blank=True)
    fotografia = models.ForeignKey(
        FotografiaServicio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sesion_captura",
    )

    class Meta:
        ordering = ["-creada_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["servicio", "etapa"],
                condition=Q(estado="PENDIENTE"),
                name="una_sesion_pendiente_por_servicio_etapa",
            )
        ]

    def __str__(self):
        return f"{self.servicio_id} - {self.etapa} ({self.estado})"