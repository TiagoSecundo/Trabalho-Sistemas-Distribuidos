from django.urls import path
from .api import (
    MinhaContaView, MinhasMonografiasView, RascunhoAlunoViewSet,
    EmitirConviteExternoView, ConfirmarConviteExternoView,
)
from .jwt_api import TokenMicroservicoView
from .avaliacoes_api import RegistrarDefesaView, MinhaAvaliacaoView, FinalizarBancaView
from .agendamento_api import (
    ProporBancaView, AdicionarParticipanteView,
    ResponderConviteInternoView, RemoverParticipanteView, CancelarPropostaView,
)

urlpatterns = [
    path('monografias/<int:pk>/propor-banca/', ProporBancaView.as_view(), name='api-propor-banca'),
    path('bancas/<int:pk>/participantes/', AdicionarParticipanteView.as_view(), name='api-adicionar-participante'),
    path('bancas/<int:pk>/cancelar-proposta/', CancelarPropostaView.as_view(), name='api-cancelar-proposta'),
    path('participacoes/<int:pk>/responder/', ResponderConviteInternoView.as_view(), name='api-responder-convite-interno'),
    path('participacoes/<int:pk>/retirar/', RemoverParticipanteView.as_view(), name='api-retirar-participante'),
    path('bancas/<int:pk>/realizar/', RegistrarDefesaView.as_view(), name='api-realizar-banca'),
    path('bancas/<int:pk>/finalizar/', FinalizarBancaView.as_view(), name='api-finalizar-banca'),
    path('participacoes/<int:pk>/avaliacao/', MinhaAvaliacaoView.as_view(), name='api-minha-avaliacao'),
    path('token-microservico/', TokenMicroservicoView.as_view(), name='token-microservico'),
    path('me/', MinhaContaView.as_view(), name='me'),
    path('monografias/', MinhasMonografiasView.as_view(), name='minhas-monografias'),
    path('rascunhos/', RascunhoAlunoViewSet.as_view({'get': 'list', 'post': 'create'}), name='meus-rascunhos'),
    path('rascunhos/<int:pk>/', RascunhoAlunoViewSet.as_view({
        'get': 'retrieve', 'patch': 'partial_update', 'delete': 'destroy',
    }), name='meu-rascunho-detalhe'),
    path('convites/<int:pk>/emitir/', EmitirConviteExternoView.as_view(), name='emitir-convite-externo'),
    path('convites/<int:pk>/confirmar/', ConfirmarConviteExternoView.as_view(), name='confirmar-convite-externo'),
]
