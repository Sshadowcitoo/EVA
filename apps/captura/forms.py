from django import forms

from apps.catalogo.models import Plato, TipoPorcion

class ServicioForm(forms.Form):

    plato = forms.ModelChoiceField(
        queryset=Plato.objects.filter(activo=true),
        label= "Plato",
        empty_label="Selecciona un plato",
    )
    tipo_porcion = forms.ModelChoiceField(
        queryset=TipoPorcion.objects.filter(activo=true),
        label= "Tipo de porcion",
        empty_label="Selecciona una porcion",
    )