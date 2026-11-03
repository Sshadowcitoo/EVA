from django.urls import path
from . import views

app_name = 'analisis'
urlpatterns = [
    path('', views.lista, name='lista'),
    path('servicio/<uuid:servicio_id>/', views.par, name='par'),
    path('servicio/<uuid:servicio_id>/solicitar/', views.solicitar, name='solicitar'),
    path('<uuid:analisis_id>/', views.detalle, name='detalle'),
    path('<uuid:analisis_id>/estado/', views.estado, name='estado'),
    path('<uuid:analisis_id>/reintentar/', views.reintentar, name='reintentar'),
    path('<uuid:analisis_id>/foto/<uuid:foto_id>/', views.foto, name='foto'),
    path('<uuid:analisis_id>/mascara/<uuid:mascara_id>/', views.mascara, name='mascara'),
]
