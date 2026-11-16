from rest_framework import serializers

from Curso_Django.api import ModelSerializerValidado

from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca
from .services import MonografiaService


class MonografiaSerializer(ModelSerializerValidado):
    service_class = MonografiaService
    aluno_nome = serializers.CharField(source='aluno.nome', read_only=True)
    curso_nome = serializers.CharField(source='curso.nome', read_only=True)
    orientador_nome = serializers.CharField(source='orientador.nome', read_only=True)
    coorientador_nome = serializers.CharField(source='coorientador.nome', read_only=True, default=None)
    status_descricao = serializers.CharField(source='get_status_fluxo_display', read_only=True)
    palavras_chave = serializers.ListField(child=serializers.CharField(max_length=100), required=False)

    class Meta:
        model = Monografia
        fields = ['id', 'titulo', 'resumo', 'palavras_chave', 'aluno', 'curso', 'orientador', 'coorientador', 'status_fluxo', 'data_submissao', 'data_publicacao', 'sha256', 'aluno_nome', 'curso_nome', 'orientador_nome', 'coorientador_nome', 'status_descricao']
        read_only_fields = ['status_fluxo', 'data_submissao', 'data_publicacao', 'sha256']
