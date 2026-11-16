from django.urls import path
from . import views

app_name = 'equipe'

urlpatterns = [
    path('', views.index, name='index'),
    path('adicionar/', views.adicionar, name='adicionar'),
    path('<str:tipo>/<int:pk>/', views.detalhes, name='detalhes'),
    path('<str:tipo>/<int:pk>/editar/', views.editar, name='editar'),
    path('<str:tipo>/<int:pk>/excluir/', views.excluir, name='excluir'),
]
