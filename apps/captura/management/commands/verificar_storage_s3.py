"""Prueba explícita contra el bucket autorizado; nunca usa fotos del piloto."""
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.captura import storage


class Command(BaseCommand):
    help = 'Verifica escritura, lectura y limpieza S3 con un archivo técnico propio.'

    def add_arguments(self, parser):
        parser.add_argument('--confirmar-prueba', action='store_true')

    def handle(self, *args, **options):
        if not options['confirmar_prueba'] or settings.EVA_STORAGE_BACKEND != 's3':
            raise CommandError('Requiere backend s3 y --confirmar-prueba; usa el bucket/prefijo configurados.')
        content = b'EVA: prueba tecnica de almacenamiento privado\n'
        stored = None
        try:
            stored = storage.guardar(content, f'healthchecks/{uuid.uuid4()}.txt', tipo_contenido='text/plain')
            with storage.abrir(stored.clave, backend=stored.backend, version_id=stored.version_id) as body:
                if body.read() != content:
                    raise CommandError('La lectura no coincide con la prueba escrita.')
        except storage.ErrorAlmacenamiento as error:
            raise CommandError('La prueba S3 falló; revisar rol, bucket y red sin publicar credenciales.') from error
        finally:
            if stored:
                try:
                    storage.eliminar(stored.clave, backend=stored.backend, version_id=stored.version_id)
                except storage.ErrorAlmacenamiento as error:
                    raise CommandError(f'La limpieza requiere reintento: {stored.clave}') from error
        self.stdout.write(self.style.SUCCESS('S3: escritura, lectura y limpieza verificadas con datos técnicos.'))
