from django.urls import path
from . import views

app_name = 'historico'
urlpatterns = [
    path('', views.lista, name='lista'),
    path('demostracion/', views.demostracion, name='demostracion'),
    path('comparar/', views.comparar, name='comparar'),
    path('servicios/<uuid:servicio_id>/percepcion/', views.percepcion, name='percepcion'),
]
