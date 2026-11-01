import json

from django.core.management.base import BaseCommand, CommandError
from apps.captura.limpieza import ejecutar


class Command(BaseCommand):
    help = "Simula la retención de 90 días y reconciliación de cargas. Solo --aplicar elimina bytes."

    def add_arguments(self, parser):
        parser.add_argument("--aplicar", action="store_true")
        parser.add_argument("--limite", type=int, default=500)

    def handle(self, *args, **options):
        if not 1 <= options["limite"] <= 10000:
            raise CommandError("El límite debe estar entre 1 y 10000 por grupo.")
        informe = ejecutar(aplicar=options["aplicar"], limite=options["limite"])
        self.stdout.write(json.dumps(informe, ensure_ascii=False))
        if informe["errores"]:
            raise CommandError("Hay borrados pendientes; revisar almacenamiento y volver a ejecutar.")
