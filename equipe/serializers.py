from Curso_Django.api import ModelSerializerValidado
from rest_framework import serializers

from .models import Aluno, Curso, Professor


class AlunoSerializer(ModelSerializerValidado):
    curso_nome = serializers.CharField(source='curso.nome', read_only=True)
    orientador_nome = serializers.CharField(source='orientador_atual.nome', read_only=True, default=None)

    class Meta:
        model = Aluno
        fields = ['id', 'usuario', 'nome', 'matricula', 'email', 'curso', 'orientador_atual', 'curso_nome', 'orientador_nome']


class ProfessorSerializer(ModelSerializerValidado):
    class Meta:
        model = Professor
        fields = ['id', 'usuario', 'nome', 'email', 'departamento', 'area_pesquisa']


class CursoSerializer(ModelSerializerValidado):
    coordenador_nome = serializers.CharField(source='coordenador.nome', read_only=True, default=None)

    class Meta:
        model = Curso
        fields = ['id', 'nome', 'codigo', 'coordenador', 'coordenador_nome']
