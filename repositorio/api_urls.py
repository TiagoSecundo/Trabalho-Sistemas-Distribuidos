from django.urls import path
from . import api

app_name = 'repositorio-api'
urlpatterns = [
    path('monografias/', api.MonografiasPublicas.as_view(), name='monografias'),
    path('monografias/<int:pk>/', api.MonografiaPublica.as_view(), name='monografia'),
    path('monografias/<int:pk>/arquivo/', api.ArquivoPublico.as_view(), name='arquivo'),
    path('cursos/', api.CursosPublicos.as_view(), name='cursos'),
    path('orientadores/', api.OrientadoresPublicos.as_view(), name='orientadores'),
]
