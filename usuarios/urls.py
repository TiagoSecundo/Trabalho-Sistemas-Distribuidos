from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('painel/', views.painel, name='painel'),
    path('painel/<slug:perfil>/', views.painel, name='perfil'),
    path('trabalhos/<int:pk>/', views.trabalho, name='trabalho'),
    path('rascunhos/novo/', views.rascunho, name='novo-rascunho'),
    path('rascunhos/<int:pk>/editar/', views.rascunho, name='editar-rascunho'),
    path('rascunhos/<int:pk>/excluir/', views.excluir, name='excluir-rascunho'),
    path('bancas/<int:pk>/realizar/', views.realizar_defesa, name='realizar-defesa'),
    path('bancas/<int:pk>/finalizar/', views.finalizar_banca, name='finalizar-banca'),
    path('participacoes/<int:pk>/avaliar/', views.avaliar_participacao, name='avaliar-participacao'),
    path('convites/<int:pk>/emitir/', views.emitir_convite, name='emitir-convite'),
    path('convites/<int:pk>/', views.confirmar_convite, name='confirmar-convite'),
]
