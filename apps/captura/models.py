import uuid

from django.db import models


class Servicio(models.Model):
    class Plato(models.TextChoices):
        ARROZ_CON_POLLO = "arroz_con_pollo", "Arroz con pollo"
        LENTEJAS = "lentejas", "Lentejas"

    class TipoPorcion(models.TextChoices):
        PEQUENA = "pequena", "Pequeña"
        REGULAR = "regular", "Regular"
        GRANDE = "grande", "Grande"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plato = models.CharField(max_length=50, choices=Plato.choices)
    tipo_porcion = models.CharField(max_length=20, choices=TipoPorcion.choices)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.get_plato_display()}"
