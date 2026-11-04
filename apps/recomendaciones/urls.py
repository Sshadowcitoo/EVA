from django.urls import path
from . import views, demo_views

app_name = 'recomendaciones'
urlpatterns = [
    path('', views.lista, name='lista'),
    path('demostracion/', demo_views.demostracion, name='demo'),
    path('demostracion/foto/', demo_views.foto, name='demo_foto'),
    path('evaluar/', views.evaluar, name='evaluar'),
    path('evaluaciones/<uuid:evaluacion_id>/', views.evaluacion, name='evaluacion'),
    path('evaluaciones/<uuid:evaluacion_id>/generar/', views.generar, name='generar'),
    path('<uuid:recomendacion_id>/', views.detalle, name='detalle'),
    path('<uuid:recomendacion_id>/decidir/', views.decidir, name='decidir'),
    path('<uuid:recomendacion_id>/pruebas/', views.registrar_prueba, name='registrar_prueba'),
    path('pruebas/<uuid:prueba_id>/', views.prueba, name='prueba'),
    path('pruebas/<uuid:prueba_id>/evaluar/', views.evaluar_prueba, name='evaluar_prueba'),
]
