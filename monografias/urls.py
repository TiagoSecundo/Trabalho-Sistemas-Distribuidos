from django.urls import path
from . import views

app_name = 'monografias'

urlpatterns = [
    path('', views.index, name='index'),
    path('adicionar/', views.adicionar, name='adicionar'),
    path("detalhes/<int:pk>/", views.detalhes, name='detalhes'),
    path('editar/<int:pk>/', views.editar, name='editar'),
    path('excluir/<int:pk>/', views.excluir, name='excluir'),
    path('<str:tipo>/', views.index, name='recurso-lista'),
    path('<str:tipo>/adicionar/', views.adicionar, name='recurso-adicionar'),
    path('<str:tipo>/<int:pk>/', views.detalhes, name='recurso-detalhes'),
    path('<str:tipo>/<int:pk>/editar/', views.editar, name='recurso-editar'),
    path('<str:tipo>/<int:pk>/excluir/', views.excluir, name='recurso-excluir'),
]
