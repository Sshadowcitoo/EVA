"""Retira maduro del piloto sin alterar instantáneas de servicios anteriores."""
from django.db import migrations


def retirar(apps, schema_editor):
    relacion = apps.get_model('catalogo', 'PlatoComponente')
    componente = apps.get_model('catalogo', 'Componente')
    alias = schema_editor.connection.alias
    relacion.objects.using(alias).filter(plato__codigo='seco_de_pollo', componente__codigo='maduro').update(activo=False)
    # No desactivar un componente que otro plato personalizado siga utilizando.
    if not relacion.objects.using(alias).filter(componente__codigo='maduro', activo=True).exists():
        componente.objects.using(alias).filter(codigo='maduro').update(activo=False)


class Migration(migrations.Migration):
    dependencies = [('catalogo', '0001_initial')]
    operations = [migrations.RunPython(retirar, migrations.RunPython.noop)]
