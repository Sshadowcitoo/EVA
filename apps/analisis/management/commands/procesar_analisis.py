import time
from django.core.management.base import BaseCommand, CommandError
from apps.analisis.jobs import ejecutar_uno
from apps.analisis.motor import SinMotor


class Command(BaseCommand):
    help = 'Procesa la cola de análisis fuera de la web, con límite total por intento.'

    def add_arguments(self, parser):
        parser.add_argument('--una-vez', action='store_true')

    def handle(self, *args, **options):
        try:
            while True:
                procesado = ejecutar_uno()
                if options['una_vez']:
                    self.stdout.write('Intento procesado.' if procesado else 'Sin pendientes.')
                    return
                if not procesado:
                    time.sleep(2)
        except SinMotor as error:
            raise CommandError(' '.join(error.messages)) from None
        except KeyboardInterrupt:
            return
