from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('adicionar/', views.adicionar, name='adicionar'),
    path("detalhes/<int:pk>/", views.detalhes, name='detalhes'),
]
