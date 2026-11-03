"""Formularios web; los normalizadores públicos conservan las reglas del contrato."""
from django import forms
from . import services
from .contracts import CATEGORIAS, DECISIONES, SUFICIENCIA, MAX_TEXTO, ParametrosInvalidos


def errores_formulario(form, errores):
    for campo, valores in errores.items():
        for valor in valores if isinstance(valores, (list, tuple)) else [valores]:
            form.add_error(campo if campo in form.fields else None, valor)



def conservar_seleccion(form, campo, opciones):
    # Solo representa el borrador cuando no se pudieron cargar opciones; las
    # vistas no ejecutan operaciones con este estado (503).
    if opciones is None and form.is_bound and form.data.get(campo):
        valor = form.data[campo]
        form.fields[campo].choices = list(form.fields[campo].choices) + [(valor, 'Selección enviada: '+valor)]


def fecha(etiqueta, requerida=False):
    return forms.DateField(label=etiqueta, required=requerida, input_formats=['%Y-%m-%d'], widget=forms.DateInput(format='%Y-%m-%d', attrs={'type':'date'}))


class HistoricoForm(forms.Form):
    plato = forms.ChoiceField(label='Plato', required=False)
    componente = forms.ChoiceField(label='Componente', required=False)
    porcion = forms.ChoiceField(label='Porción', required=False)
    desde = fecha('Desde')
    hasta = fecha('Hasta (incluido)')
    hora_desde = forms.TimeField(label='Hora desde', required=False, input_formats=['%H:%M'], widget=forms.TimeInput(format='%H:%M', attrs={'type':'time'}))
    hora_hasta = forms.TimeField(label='Hora hasta (excluida)', required=False, input_formats=['%H:%M'], widget=forms.TimeInput(format='%H:%M', attrs={'type':'time'}))

    def __init__(self, *args, opciones=None, **kwargs):
        super().__init__(*args, **kwargs)
        for campo, plural in [('plato','platos'), ('componente','componentes'), ('porcion','porciones')]:
            self.fields[campo].choices = [('', 'Todos')] + [(x['codigo'],x['nombre']) for x in (opciones or {}).get('historico',{}).get(plural,[])]
            conservar_seleccion(self, campo, opciones)

    def entrada(self):
        return {**self.cleaned_data, 'origen': self.data.get('origen')}


class FiltrosForm(HistoricoForm):
    categoria = forms.ChoiceField(label='Categoría', choices=[('', 'Todas')]+list(CATEGORIAS), required=False)
    decision = forms.ChoiceField(label='Decisión', choices=[('', 'Todas')]+list(DECISIONES), required=False)
    suficiencia = forms.ChoiceField(label='Evidencia', choices=[('', 'Todas')]+list(SUFICIENCIA), required=False)
    page = forms.IntegerField(label='Página', required=False, min_value=1, widget=forms.HiddenInput)

    def clean(self):
        datos = super().clean()
        if not self.errors:
            try:
                self.normalizado = services.normalizar_filtros(self.entrada())
            except ParametrosInvalidos as exc:
                errores_formulario(self, exc.errores)
        return datos


class EvaluacionForm(HistoricoForm):
    desde = fecha('Desde', True)
    hasta = fecha('Hasta (incluido)', True)
    version_criterios = forms.ChoiceField(label='Versión de criterios', required=False)

    def __init__(self, *args, opciones=None, **kwargs):
        kwargs.setdefault('auto_id', 'evaluar_%s')
        super().__init__(*args, opciones=opciones, **kwargs)
        self.fields['version_criterios'].choices = [('', 'Sin versión seleccionada' if (opciones or {}).get('versiones_criterios') else 'No hay versiones disponibles')] + [(x['version'], x['version']+' · '+x['descripcion']) for x in (opciones or {}).get('versiones_criterios',[])]
        conservar_seleccion(self, 'version_criterios', opciones)

    def clean(self):
        datos = super().clean()
        if not self.errors:
            try:
                self.normalizado = services.normalizar_periodo_evaluacion(self.entrada())
            except ParametrosInvalidos as exc:
                errores_formulario(self, exc.errores)
        return datos


class VersionForm(forms.Form):
    version_esperada = forms.IntegerField(min_value=0, max_value=2**31-1, widget=forms.HiddenInput)


class DecisionForm(VersionForm):
    decision = forms.ChoiceField(label='Decisión', choices=DECISIONES)
    justificacion = forms.CharField(label='Justificación', max_length=MAX_TEXTO, widget=forms.Textarea(attrs={'rows':3}))

    def clean(self):
        datos = super().clean()
        if not self.errors:
            try:
                self.normalizado = services.normalizar_decision(datos)
            except ParametrosInvalidos as exc:
                errores_formulario(self, exc.errores)
        return datos


class PruebaForm(forms.Form):
    cambio = forms.CharField(label='Cambio propuesto', max_length=MAX_TEXTO, widget=forms.Textarea(attrs={'rows':3}))
    responsable_id = forms.TypedChoiceField(label='Responsable', coerce=int, empty_value=None)
    referencia_desde = fecha('Referencia: desde', True)
    referencia_hasta = fecha('Referencia: hasta (incluido)', True)
    intervencion_desde = fecha('Intervención: desde', True)
    intervencion_hasta = fecha('Intervención: hasta (incluido)', True)

    def __init__(self, *args, opciones=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable_id'].choices = [('', 'Selecciona un responsable')] + [(x['id'],x['nombre']) for x in (opciones or {}).get('responsables',[])]
        conservar_seleccion(self, 'responsable_id', opciones)

    def clean(self):
        datos = super().clean()
        if not self.errors:
            try:
                self.normalizado = services.normalizar_prueba(datos)
            except ParametrosInvalidos as exc:
                errores_formulario(self, exc.errores)
        return datos
