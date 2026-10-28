from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogo.permissions import PERMISOS_POR_ROL


class Command(BaseCommand):
    help = "Crea roles EVA y sincroniza sus permisos de captura y catálogo."

    @transaction.atomic
    def handle(self, *args, **options):
        permisos = list(
            Permission.objects.filter(
                content_type__app_label__in=("captura", "catalogo")
            ).select_related("content_type")
        )
        disponibles = {
            f"{permiso.content_type.app_label}.{permiso.codename}": permiso
            for permiso in permisos
        }
        gestionados = {permiso.pk for permiso in permisos}

        for nombre, esperados in PERMISOS_POR_ROL.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            deseados = {disponibles[codigo].pk for codigo in esperados if codigo in disponibles}
            actuales = set(grupo.permissions.values_list("pk", flat=True))
            # Conserva membresías y permisos de aplicaciones ajenas a este bloque.
            grupo.permissions.remove(*((actuales & gestionados) - deseados))
            grupo.permissions.add(*(deseados - actuales))
            self.stdout.write(f"{nombre}: {len(deseados)} permisos del bloque disponibles.")

            pendientes = sorted(set(esperados) - disponibles.keys())
            if pendientes:
                self.stdout.write(
                    self.style.WARNING(
                        "Pendientes de modelos/migraciones: " + ", ".join(pendientes)
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Roles configurados. No se crearon usuarios ni se asignaron membresías."
            )
        )
