from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogo.models import Componente, Plato, PlatoComponente, TipoPorcion

COMPONENTES = {
    "yuca": "Yuca",
    "pescado": "Pescado",
    "arroz": "Arroz",
    "pollo": "Pollo",
    "maduro": "Maduro",
    "menestra": "Menestra",
    "carne": "Carne",
    "ensalada": "Ensalada",
}

PLATOS = [
    ("encebollado", "Encebollado", ["yuca", "pescado"]),
    ("seco_de_pollo", "Seco de pollo", ["arroz", "pollo", "maduro"]),
    (
        "arroz_menestra_carne",
        "Arroz con menestra y carne",
        ["arroz", "menestra", "carne", "ensalada"],
    ),
]

PORCIONES = [("estandar", "Estándar")]


class Command(BaseCommand):
    help = (
        "Carga el catálogo inicial del piloto. Es repetible: no sobrescribe "
        "lo que ya existe salvo que se use --restablecer."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--restablecer",
            action="store_true",
            help="Restaura nombre y estado activo de los elementos de demostración.",
        )

    @staticmethod
    def _obtener(modelo, codigo, nombre, restablecer):
        if restablecer:
            return modelo.objects.update_or_create(
                codigo=codigo, defaults={"nombre": nombre, "activo": True}
            )
        return modelo.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre}
        )

    @transaction.atomic
    def handle(self, *args, **options):
        restablecer = options["restablecer"]
        creados = 0

        componentes = {}
        for codigo, nombre in COMPONENTES.items():
            obj, creado = self._obtener(Componente, codigo, nombre, restablecer)
            componentes[codigo] = obj
            creados += creado

        for codigo, nombre in PORCIONES:
            _, creado = self._obtener(TipoPorcion, codigo, nombre, restablecer)
            creados += creado

        for codigo, nombre, codigos_componentes in PLATOS:
            plato, creado = self._obtener(Plato, codigo, nombre, restablecer)
            creados += creado
            # La composición solo se toca si el plato es nuevo o se pidió
            # restablecer; así no se pisan cambios hechos desde Administración.
            if creado or restablecer:
                for cod in codigos_componentes:
                    PlatoComponente.objects.update_or_create(
                        plato=plato,
                        componente=componentes[cod],
                        defaults={"activo": True},
                    )

        if options["verbosity"] > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Catálogo listo. Elementos nuevos creados: {creados}."
                )
            )
