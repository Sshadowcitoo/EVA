from django import forms
from django.db import transaction

from .models import Componente, Plato, PlatoComponente, TipoPorcion


class CodigoEstableMixin:
    """El código se elige al crear y no se puede cambiar después."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["codigo"].disabled = True
            self.fields["codigo"].help_text = "El código no se modifica después de crearlo."


class PlatoForm(CodigoEstableMixin, forms.ModelForm):
    composicion = forms.ModelMultipleChoiceField(
        queryset=Componente.objects.filter(activo=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Componentes del plato",
    )

    class Meta:
        model = Plato
        fields = ["codigo", "nombre"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Al editar, marca los componentes que el plato ya tiene activos.
            self.fields["composicion"].initial = Componente.objects.filter(
                relaciones__plato=self.instance, relaciones__activo=True
            )

    @transaction.atomic
    def save(self, commit=True):
        plato = super().save()
        elegidos = set(self.cleaned_data["composicion"])

        # Relaciones que ya existen: se activan o desactivan, nunca se borran.
        for relacion in plato.relaciones.select_related("componente"):
            if not relacion.componente.activo:
                continue
            debe_estar_activa = relacion.componente in elegidos
            if relacion.activo != debe_estar_activa:
                relacion.activo = debe_estar_activa
                relacion.save(update_fields=["activo"])
            elegidos.discard(relacion.componente)

        # Los que quedan en "elegidos" son componentes nuevos para este plato.
        PlatoComponente.objects.bulk_create(
            PlatoComponente(plato=plato, componente=componente)
            for componente in elegidos
        )
        return plato


class ComponenteForm(CodigoEstableMixin, forms.ModelForm):
    class Meta:
        model = Componente
        fields = ["codigo", "nombre"]


class TipoPorcionForm(CodigoEstableMixin, forms.ModelForm):
    class Meta:
        model = TipoPorcion
        fields = ["codigo", "nombre"]