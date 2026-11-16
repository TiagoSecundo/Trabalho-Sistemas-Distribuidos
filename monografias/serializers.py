from rest_framework import serializers

from Curso_Django.api import ModelSerializerValidado

from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca
from .services import MonografiaService, BancaService


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


class BancaSerializer(ModelSerializerValidado):
    service_class = BancaService
    monografia_titulo = serializers.CharField(source='monografia.titulo', read_only=True)
    modalidade_descricao = serializers.CharField(source='get_modalidade_display', read_only=True)
    status_descricao = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Banca
        fields = ['id', 'monografia', 'inicio', 'fim', 'local', 'link', 'modalidade', 'status', 'monografia_titulo', 'modalidade_descricao', 'status_descricao']
        read_only_fields = ['status']


class MembroExternoSerializer(ModelSerializerValidado):
    class Meta:
        model = MembroExterno
        fields = ['id', 'nome', 'email', 'instituicao']


class ParticipacaoBancaSerializer(ModelSerializerValidado):
    monografia_titulo = serializers.CharField(source='banca.monografia.titulo', read_only=True)
    participante_nome = serializers.SerializerMethodField()
    papel_descricao = serializers.CharField(source='get_papel_display', read_only=True)
    convite_descricao = serializers.CharField(source='get_convite_status_display', read_only=True)

    def get_participante_nome(self, instance):
        return str(instance.professor or instance.membro_externo)

    class Meta:
        model = ParticipacaoBanca
        fields = ['id', 'banca', 'professor', 'membro_externo', 'papel', 'convite_status', 'confirmado_em', 'monografia_titulo', 'participante_nome', 'papel_descricao', 'convite_descricao']
        read_only_fields = ['convite_status', 'confirmado_em']
