from django.urls import path
from . import estatisticas_views, views
from . import publicacao_views

app_name = 'usuarios'

urlpatterns = [
    path('estatisticas/', estatisticas_views.dashboard, name='estatisticas'),
    path('trabalhos/<int:pk>/documentos/', publicacao_views.documentos, name='documentos'),
    path('trabalhos/<int:pk>/documentos/<int:documento_id>/conferir/', publicacao_views.conferir, name='conferir-documento'),
    path('trabalhos/<int:pk>/documentos/<int:documento_id>/arquivo/', publicacao_views.arquivo, name='documento-arquivo'),
    path('painel/', views.painel, name='painel'),
    path('painel/<slug:perfil>/', views.painel, name='perfil'),
    path('trabalhos/<int:pk>/', views.trabalho, name='trabalho'),
    path('trabalhos/<int:pk>/submeter-pdf/', views.submeter_pdf_view, name='submeter-pdf'),
    path('trabalhos/<int:pk>/pdf/', views.baixar_pdf_view, name='visualizar-pdf'),
    path('trabalhos/<int:pk>/orientacao/aprovar/', views.aprovar_submissao_view, name='aprovar-orientacao'),
    path('trabalhos/<int:pk>/orientacao/ajustes/', views.solicitar_ajustes_view, name='solicitar-ajustes'),
    path('trabalhos/<int:pk>/sincronizar/', views.sincronizar_submissao_view, name='sincronizar-submissao'),
    path('rascunhos/novo/', views.rascunho, name='novo-rascunho'),
    path('rascunhos/<int:pk>/editar/', views.rascunho, name='editar-rascunho'),
    path('rascunhos/<int:pk>/excluir/', views.excluir, name='excluir-rascunho'),
    path('trabalhos/<int:pk>/propor-banca/', views.propor_banca_view, name='propor-banca'),
    path('bancas/<int:pk>/participantes/novo/', views.adicionar_participante_view, name='adicionar-participante'),
    path('bancas/<int:pk>/cancelar-proposta/', views.cancelar_proposta_view, name='cancelar-proposta'),
    path('participacoes/<int:pk>/responder/', views.responder_convite_interno_view, name='responder-convite-interno'),
    path('participacoes/<int:pk>/retirar/', views.retirar_participante_view, name='retirar-participante'),
    path('bancas/<int:pk>/realizar/', views.realizar_defesa, name='realizar-defesa'),
    path('bancas/<int:pk>/finalizar/', views.finalizar_banca, name='finalizar-banca'),
    path('participacoes/<int:pk>/avaliar/', views.avaliar_participacao, name='avaliar-participacao'),
    path('participacoes/<int:pk>/avaliacao-externa/emitir/', views.emitir_codigo_avaliacao_externa_view, name='emitir-avaliacao-externa'),
    path('participacoes/<int:pk>/avaliacao-externa/', views.avaliacao_externa_view, name='avaliacao-externa'),
    path('convites/<int:pk>/emitir/', views.emitir_convite, name='emitir-convite'),
    path('convites/<int:pk>/', views.confirmar_convite, name='confirmar-convite'),
]
