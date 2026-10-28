from django.db import migrations

# Etiquetas del primer avance. No se remapean a platos del catálogo:
# solo se conserva el nombre con el que se registró cada servicio.
PLATOS_HISTORICOS = {
    "arroz_con_pollo": "Arroz con pollo",
    "lentejas": "Lentejas",
}
PORCIONES_HISTORICAS = {
    "pequena": "Pequeña",
    "regular": "Regular",
    "grande": "Grande",
}


def conservar_etiquetas(apps, schema_editor):
    Servicio = apps.get_model("captura", "Servicio")
    for servicio in Servicio.objects.filter(plato_catalogo__isnull=True):
        if not servicio.plato_nombre:
            servicio.plato_nombre = PLATOS_HISTORICOS.get(
                servicio.plato, servicio.plato
            )
        if not servicio.porcion_nombre:
            servicio.porcion_nombre = PORCIONES_HISTORICAS.get(
                servicio.tipo_porcion, servicio.tipo_porcion
            )
        servicio.save(update_fields=["plato_nombre", "porcion_nombre"])


class Migration(migrations.Migration):

    dependencies = [
        ("captura", "0002_catalogo_instantaneas"),
    ]

    operations = [
        migrations.RunPython(conservar_etiquetas, migrations.RunPython.noop),
    ]
