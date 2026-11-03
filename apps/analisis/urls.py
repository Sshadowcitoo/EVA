from django.urls import path
from . import views, revision_views

app_name = 'analisis'
urlpatterns = [
    path('revision/', revision_views.pendientes_revision, name='pendientes_revision'),
    path('revision/<uuid:analisis_id>/', revision_views.revision_detalle, name='revision_detalle'),
    path('revision/<uuid:analisis_id>/<uuid:intento_id>/decidir/', revision_views.revisar, name='revisar'),
    path('', views.lista, name='lista'),
    path('servicio/<uuid:servicio_id>/', views.par, name='par'),
    path('servicio/<uuid:servicio_id>/solicitar/', views.solicitar, name='solicitar'),
    path('<uuid:analisis_id>/', views.detalle, name='detalle'),
    path('<uuid:analisis_id>/estado/', views.estado, name='estado'),
    path('<uuid:analisis_id>/reintentar/', views.reintentar, name='reintentar'),
    path('<uuid:analisis_id>/foto/<uuid:foto_id>/', views.foto, name='foto'),
    path('<uuid:analisis_id>/mascara/<uuid:mascara_id>/', views.mascara, name='mascara'),
]
