from Curso_Django.api import ModelSerializerValidado
from rest_framework import serializers

from .models import Aluno, Curso, Professor


class AlunoSerializer(ModelSerializerValidado):
    usuario_nome = serializers.CharField(source='usuario.username', read_only=True, default=None)
    curso_nome = serializers.CharField(source='curso.nome', read_only=True)
    orientador_nome = serializers.CharField(source='orientador_atual.nome', read_only=True, default=None)

    class Meta:
        model = Aluno
        fields = ['id', 'usuario', 'usuario_nome', 'nome', 'matricula', 'email', 'curso', 'orientador_atual', 'curso_nome', 'orientador_nome']


class ProfessorSerializer(ModelSerializerValidado):
    usuario_nome = serializers.CharField(source='usuario.username', read_only=True, default=None)
    class Meta:
        model = Professor
        fields = ['id', 'usuario', 'usuario_nome', 'nome', 'email', 'departamento', 'area_pesquisa']


class CursoSerializer(ModelSerializerValidado):
    coordenador_nome = serializers.CharField(source='coordenador.nome', read_only=True, default=None)

    class Meta:
        model = Curso
        fields = ['id', 'nome', 'codigo', 'coordenador', 'coordenador_nome']
