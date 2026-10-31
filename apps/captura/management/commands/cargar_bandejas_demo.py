from django.core.management.base import BaseCommand
from django.db import transaction

from apps.captura import services
from apps.captura.models import Bandeja

CANTIDAD = 10


class Command(BaseCommand):
    help = (
        "Carga 10 bandejas de demostración con su etiqueta. Es repetible: no "
        "modifica bandejas ni etiquetas existentes y no crea usuarios."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        nuevas = 0
        for numero in range(1, CANTIDAD + 1):
            bandeja, creada = Bandeja.objects.get_or_create(numero=numero)
            if creada:
                services.emitir_etiqueta(bandeja=bandeja)
                nuevas += 1
        if options["verbosity"] > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Bandejas de demostración listas. Nuevas: {nuevas}.")
            )