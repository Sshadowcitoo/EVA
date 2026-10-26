import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction

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

    def __str__(self):
        return f"{self.id} - {self.get_plato_display()}"

    def get_plato_display(self):
        return self.plato_nombre or self.plato

    def get_tipo_porcion_display(self):
        return self.porcion_nombre or self.tipo_porcion

    @classmethod
    def registrar(cls, *, plato, porcion, usuario=None):
        """Crea un servicio con su instantánea de catálogo en una sola transacción."""
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