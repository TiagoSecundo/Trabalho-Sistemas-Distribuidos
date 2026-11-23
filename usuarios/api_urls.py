from django.urls import path
from . import estatisticas
from .estatisticas_api import EstatisticasView
from .submissao_api import SubmeterPdfView, ParecerOrientadorView, SincronizarSubmissaoView
from .api import (
    MinhaContaView, MinhasMonografiasView, RascunhoAlunoViewSet,
    EmitirConviteExternoView, ConfirmarConviteExternoView,
)
from .jwt_api import TokenMicroservicoView
from .publicacao_api import DocumentosView, ConferirDocumentoView, DocumentoArquivoView
from .avaliacoes_api import RegistrarDefesaView, MinhaAvaliacaoView, FinalizarBancaView
from .avaliacao_externa_api import EmitirCodigoAvaliacaoExternaView, RegistrarAvaliacaoExternaView
from .agendamento_api import (
    ProporBancaView, AdicionarParticipanteView,
    ResponderConviteInternoView, RemoverParticipanteView, CancelarPropostaView,
)

urlpatterns = [
    path('estatisticas/por-curso/', EstatisticasView.as_view(indicador=estatisticas.por_curso),
         name='api-estatisticas-por-curso'),
    path('estatisticas/por-orientador/', EstatisticasView.as_view(indicador=estatisticas.por_orientador),
         name='api-estatisticas-por-orientador'),
    path('estatisticas/por-ano-defesa/', EstatisticasView.as_view(indicador=estatisticas.por_ano_defesa),
         name='api-estatisticas-por-ano-defesa'),
    path('estatisticas/taxa-aprovacao/', EstatisticasView.as_view(indicador=estatisticas.taxa_aprovacao),
         name='api-estatisticas-taxa-aprovacao'),
    path('estatisticas/tempo-medio/', EstatisticasView.as_view(indicador=estatisticas.tempo_medio),
         name='api-estatisticas-tempo-medio'),
    path('monografias/<int:pk>/documentos/', DocumentosView.as_view(), name='api-documentos'),
    path('monografias/<int:pk>/documentos/<int:documento_id>/conferir/', ConferirDocumentoView.as_view(), name='api-conferir-documento'),
    path('monografias/<int:pk>/documentos/<int:documento_id>/arquivo/', DocumentoArquivoView.as_view(), name='api-documento-arquivo'),
    path('monografias/<int:pk>/submeter-pdf/', SubmeterPdfView.as_view(), name='api-submeter-pdf'),
    path('monografias/<int:pk>/orientacao/aprovar/', ParecerOrientadorView.as_view(), {'decisao': 'aprovar'}, name='api-aprovar-orientador'),
    path('monografias/<int:pk>/orientacao/ajustes/', ParecerOrientadorView.as_view(), {'decisao': 'ajustes'}, name='api-solicitar-ajustes'),
    path('monografias/<int:pk>/sincronizar/', SincronizarSubmissaoView.as_view(), name='api-sincronizar-submissao'),
    path('monografias/<int:pk>/propor-banca/', ProporBancaView.as_view(), name='api-propor-banca'),
    path('bancas/<int:pk>/participantes/', AdicionarParticipanteView.as_view(), name='api-adicionar-participante'),
    path('bancas/<int:pk>/cancelar-proposta/', CancelarPropostaView.as_view(), name='api-cancelar-proposta'),
    path('participacoes/<int:pk>/responder/', ResponderConviteInternoView.as_view(), name='api-responder-convite-interno'),
    path('participacoes/<int:pk>/retirar/', RemoverParticipanteView.as_view(), name='api-retirar-participante'),
    path('bancas/<int:pk>/realizar/', RegistrarDefesaView.as_view(), name='api-realizar-banca'),
    path('bancas/<int:pk>/finalizar/', FinalizarBancaView.as_view(), name='api-finalizar-banca'),
    path('participacoes/<int:pk>/avaliacao/', MinhaAvaliacaoView.as_view(), name='api-minha-avaliacao'),
    path('participacoes/<int:pk>/avaliacao-externa/emitir/', EmitirCodigoAvaliacaoExternaView.as_view(), name='api-emitir-avaliacao-externa'),
    path('participacoes/<int:pk>/avaliacao-externa/', RegistrarAvaliacaoExternaView.as_view(), name='api-avaliacao-externa'),
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
