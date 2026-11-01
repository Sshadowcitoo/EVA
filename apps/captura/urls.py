from django.urls import path

from . import gestion_views, views

app_name = "captura"

urlpatterns = [
    path("gestion/", gestion_views.gestion, name="gestion"),
    path("gestion/servicio/<uuid:pk>/anular/", gestion_views.anular, name="anular_servicio"),
    path("gestion/bandeja/<uuid:pk>/reemplazar/", gestion_views.reemplazar, name="reemplazar_etiqueta"),
    path("gestion/etiqueta/<int:pk>/qr/", gestion_views.qr_etiqueta, name="qr_etiqueta"),
    path("nueva/", views.nueva_bandeja, name="nueva_bandeja"),
    path("<uuid:pk>/confirmacion/", views.confirmacion, name="confirmacion"),

    # Bloque 2: bandejas y captura de fotografías.
    path("bandeja/", views.resolver_bandeja, name="resolver_bandeja"),
    path("retorno/", views.buscar_retorno, name="buscar_retorno"),
    path("<uuid:pk>/foto-servido/", views.foto_servido, name="foto_servido"),
    path("<uuid:pk>/foto-retorno/", views.foto_retorno, name="foto_retorno"),
    path("imagen/<uuid:pk>/", views.imagen, name="imagen"),
]
