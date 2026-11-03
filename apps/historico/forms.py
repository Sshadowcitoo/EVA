"""Formularios web del contrato v1, sin cálculos ni consultas ORM."""
from django import forms
from . import services
from .contracts import CATEGORIAS_PERCEPCION, MAX_MOTIVO, FiltrosInvalidos


def agregar_errores(form, errores):
    for campo, mensajes in errores.items():
        for mensaje in mensajes if isinstance(mensajes, (list, tuple)) else [mensajes]:
            form.add_error(campo if campo in form.fields else None, mensaje)


class FiltrosForm(forms.Form):
    plato = forms.ChoiceField(label='Plato', required=False)
    componente = forms.ChoiceField(label='Componente', required=False)
    porcion = forms.ChoiceField(label='Porción', required=False)
    desde = forms.DateField(label='Desde', required=False, input_formats=['%Y-%m-%d'], widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    hasta = forms.DateField(label='Hasta (incluido)', required=False, input_formats=['%Y-%m-%d'], widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    hora_desde = forms.TimeField(label='Hora desde', required=False, input_formats=['%H:%M'], widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time'}))
    hora_hasta = forms.TimeField(label='Hora hasta (excluida)', required=False, input_formats=['%H:%M'], widget=forms.TimeInput(format='%H:%M', attrs={'type': 'time'}))
    page = forms.IntegerField(label='Página', required=False, min_value=1, initial=1, widget=forms.HiddenInput)

    def __init__(self, *args, opciones=None, **kwargs):
        super().__init__(*args, **kwargs)
        for campo, clave in [('plato', 'platos'), ('componente', 'componentes'), ('porcion', 'porciones')]:
            self.fields[campo].choices = [('', 'Todos')] + [(x['codigo'], x['nombre']) for x in (opciones or {}).get(clave, [])]

    def clean(self):
        datos = super().clean()
        if not self.errors:
            try:
                self.filtros = services.normalizar_filtros({**datos, 'origen': self.data.get('origen')})
            except FiltrosInvalidos as exc:
                agregar_errores(self, exc.errores)
        return datos


class ComparacionForm(FiltrosForm):
    desde = None
    hasta = None
    page = None
    referencia_desde = forms.DateField(label='Referencia: desde', input_formats=['%Y-%m-%d'], widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    referencia_hasta = forms.DateField(label='Referencia: hasta (incluido)', input_formats=['%Y-%m-%d'], widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    comparado_desde = forms.DateField(label='Comparado: desde', input_formats=['%Y-%m-%d'], widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))
    comparado_hasta = forms.DateField(label='Comparado: hasta (incluido)', input_formats=['%Y-%m-%d'], widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'))

    def clean(self):
        datos = forms.Form.clean(self)
        if self.errors:
            return datos
        filtros = []
        for prefijo in ('referencia', 'comparado'):
            entrada = {k: datos.get(k) for k in ('plato', 'componente', 'porcion', 'hora_desde', 'hora_hasta')}
            entrada.update(desde=datos[prefijo+'_desde'], hasta=datos[prefijo+'_hasta'], origen=self.data.get('origen'))
            try:
                filtros.append(services.normalizar_filtros(entrada))
            except FiltrosInvalidos as exc:
                agregar_errores(self, {(prefijo+'_'+k if k in ('desde', 'hasta') else k): v for k, v in exc.errores.items()})
        if not self.errors:
            self.referencia, self.comparado = filtros
            if self.referencia['inicio'] < self.comparado['fin'] and self.comparado['inicio'] < self.referencia['fin']:
                self.add_error('comparado_desde', 'Los periodos no pueden superponerse.')
        return datos


class PercepcionForm(forms.Form):
    categoria = forms.ChoiceField(label='Porción percibida', choices=CATEGORIAS_PERCEPCION, required=False)
    motivo = forms.CharField(label='Motivo declarado (opcional)', max_length=MAX_MOTIVO, required=False, widget=forms.Textarea(attrs={'rows': 3, 'aria-describedby': 'privacidad-percepcion'}))
    version_esperada = forms.IntegerField(min_value=0, widget=forms.HiddenInput)

    def clean(self):
        datos = super().clean()
        datos['categoria'] = datos.get('categoria') or 'NO_INFORMADO'
        if datos['categoria'] == 'NO_INFORMADO' and datos.get('motivo'):
            self.add_error('motivo', 'Deja el motivo vacío cuando no hay respuesta.')
        return datos
