from django.core.management.base import BaseCommand
from apps.analisis.jobs import procesar


class Command(BaseCommand):
    help = 'Proceso hijo interno del worker; recibe un intento ya reclamado.'

    def add_arguments(self, parser):
        parser.add_argument('intento_id')

    def handle(self, *args, **options):
        procesar(options['intento_id'])
