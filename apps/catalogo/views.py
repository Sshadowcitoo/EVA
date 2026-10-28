from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from .forms import ComponenteForm, PlatoForm, TipoPorcionForm
from .models import Componente, Plato, TipoPorcion
from .permissions import ADMINISTRACION, RolesRequiredMixin


class SoloAdministracion(RolesRequiredMixin):
    allowed_roles = (ADMINISTRACION,)


#  Vistas base compartidas

class CatalogoLista(SoloAdministracion, ListView):
    template_name = "catalogo/lista.html"
    context_object_name = "objetos"
    titulo = ""
    prefijo = ""

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(
            titulo=self.titulo,
            ruta_crear=f"catalogo:{self.prefijo}_crear",
            ruta_editar=f"catalogo:{self.prefijo}_editar",
            ruta_estado=f"catalogo:{self.prefijo}_estado",
        )
        return contexto


class CatalogoFormulario(SoloAdministracion):
    template_name = "catalogo/formulario.html"
    titulo = ""
    ruta_lista = ""

    def get_success_url(self):
        return reverse(self.ruta_lista)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(titulo=self.titulo, ruta_lista=self.ruta_lista)
        return contexto


class CambiarEstado(SoloAdministracion, View):
    model = None
    ruta_lista = ""

    def post(self, request, pk):
        objeto = get_object_or_404(self.model, pk=pk)
        objeto.activo = not objeto.activo
        objeto.save(update_fields=["activo"])
        return redirect(self.ruta_lista)


#  Platos

class PlatoLista(CatalogoLista):
    model = Plato
    template_name = "catalogo/platos.html"
    context_object_name = "platos"
    titulo = "Platos"
    prefijo = "plato"


class PlatoCrear(CatalogoFormulario, CreateView):
    model = Plato
    template_name = "catalogo/plato_form.html"
    form_class = PlatoForm
    titulo = "Nuevo plato"
    ruta_lista = "catalogo:platos"


class PlatoEditar(CatalogoFormulario, UpdateView):
    model = Plato
    template_name = "catalogo/plato_form.html"
    form_class = PlatoForm
    titulo = "Editar plato"
    ruta_lista = "catalogo:platos"


class PlatoEstado(CambiarEstado):
    model = Plato
    ruta_lista = "catalogo:platos"


#  Componentes

class ComponenteLista(CatalogoLista):
    model = Componente
    template_name = "catalogo/componentes.html"
    context_object_name = "componentes"
    titulo = "Componentes"
    prefijo = "componente"


class ComponenteCrear(CatalogoFormulario, CreateView):
    model = Componente
    form_class = ComponenteForm
    titulo = "Nuevo componente"
    ruta_lista = "catalogo:componentes"


class ComponenteEditar(CatalogoFormulario, UpdateView):
    model = Componente
    form_class = ComponenteForm
    titulo = "Editar componente"
    ruta_lista = "catalogo:componentes"


class ComponenteEstado(CambiarEstado):
    model = Componente
    ruta_lista = "catalogo:componentes"


#  Tipos de porción

class PorcionLista(CatalogoLista):
    model = TipoPorcion
    template_name = "catalogo/porciones.html"
    context_object_name = "porciones"
    titulo = "Tipos de porción"
    prefijo = "porcion"


class PorcionCrear(CatalogoFormulario, CreateView):
    model = TipoPorcion
    form_class = TipoPorcionForm
    titulo = "Nuevo tipo de porción"
    ruta_lista = "catalogo:porciones"


class PorcionEditar(CatalogoFormulario, UpdateView):
    model = TipoPorcion
    form_class = TipoPorcionForm
    titulo = "Editar tipo de porción"
    ruta_lista = "catalogo:porciones"


class PorcionEstado(CambiarEstado):
    model = TipoPorcion
    ruta_lista = "catalogo:porciones"
