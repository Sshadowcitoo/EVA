from django import forms
from .models import RevisionAnalisis


class RevisionForm(forms.Form):
    decision = forms.ChoiceField(choices=RevisionAnalisis.Decision.choices)
    motivo = forms.CharField(max_length=1000, required=False, strip=True)
    version_esperada = forms.IntegerField(min_value=0, max_value=2**31 - 1)

    def __init__(self, *args, rectificar=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.rectificar = rectificar

    def clean(self):
        datos = super().clean()
        decision = datos.get('decision')
        if decision and (self.rectificar or decision != 'CONFIRMADO') and not datos.get('motivo'):
            self.add_error('motivo', 'Esta decisión requiere un motivo.')
        return datos
