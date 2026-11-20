from django.urls import path
from .api import (
    MinhaContaView, MinhasMonografiasView, RascunhoAlunoViewSet,
    EmitirConviteExternoView, ConfirmarConviteExternoView,
)

urlpatterns = [
    path('me/', MinhaContaView.as_view(), name='me'),
    path('monografias/', MinhasMonografiasView.as_view(), name='minhas-monografias'),
    path('rascunhos/', RascunhoAlunoViewSet.as_view({'get': 'list', 'post': 'create'}), name='meus-rascunhos'),
    path('rascunhos/<int:pk>/', RascunhoAlunoViewSet.as_view({
        'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy',
    }), name='meu-rascunho-detalhe'),
    path('convites/<int:pk>/emitir/', EmitirConviteExternoView.as_view(), name='emitir-convite-externo'),
    path('convites/<int:pk>/confirmar/', ConfirmarConviteExternoView.as_view(), name='confirmar-convite-externo'),
]
