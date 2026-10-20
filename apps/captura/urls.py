from django.urls import path

from . import views

app_name = "captura"

urlpatterns = [
    path("nueva/", views.nueva_bandeja, name="nueva_bandeja"),
    # cualquier otro formato termina en 404 automáticamente.
    path("<uuid:pk/confirmacion/",views.confirmacion, name="confirmacion"),
]
