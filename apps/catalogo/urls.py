from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("platos/", views.PlatoLista.as_view(), name="platos"),
    path("platos/nuevo/", views.PlatoCrear.as_view(), name="plato_crear"),
    path("platos/<int:pk>/editar/", views.PlatoEditar.as_view(), name="plato_editar"),
    path("platos/<int:pk>/estado/", views.PlatoEstado.as_view(), name="plato_estado"),

    path("componentes/", views.ComponenteLista.as_view(), name="componentes"),
    path("componentes/nuevo/", views.ComponenteCrear.as_view(), name="componente_crear"),
    path("componentes/<int:pk>/editar/", views.ComponenteEditar.as_view(), name="componente_editar"),
    path("componentes/<int:pk>/estado/", views.ComponenteEstado.as_view(), name="componente_estado"),

    path("porciones/", views.PorcionLista.as_view(), name="porciones"),
    path("porciones/nuevo/", views.PorcionCrear.as_view(), name="porcion_crear"),
    path("porciones/<int:pk>/editar/", views.PorcionEditar.as_view(), name="porcion_editar"),
    path("porciones/<int:pk>/estado/", views.PorcionEstado.as_view(), name="porcion_estado"),
]
