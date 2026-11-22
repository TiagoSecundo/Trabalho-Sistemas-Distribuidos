from django.urls import path
from . import views

app_name = 'repositorio'
urlpatterns = [path('', views.catalogo, name='catalogo'), path('<int:pk>/', views.detalhe, name='detalhe')]
