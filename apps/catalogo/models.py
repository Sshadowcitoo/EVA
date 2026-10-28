from django.db import models


class Plato(models.Model):
    codigo = models.SlugField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    componentes = models.ManyToManyField(
        "Componente", through="PlatoComponente", related_name="platos"
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Componente(models.Model):
    codigo = models.SlugField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class PlatoComponente(models.Model):
    plato = models.ForeignKey(
        Plato, on_delete=models.PROTECT, related_name="relaciones"
    )
    componente = models.ForeignKey(
        Componente, on_delete=models.PROTECT, related_name="relaciones"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plato", "componente"], name="plato_componente_unico"
            )
        ]

    def __str__(self):
        return f"{self.plato} - {self.componente}"


class TipoPorcion(models.Model):
    codigo = models.SlugField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "tipo de porción"
        verbose_name_plural = "tipos de porción"

    def __str__(self):
        return self.nombre
