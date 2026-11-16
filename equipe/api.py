from Curso_Django.api import CRUDViewSet

from .models import Aluno, Curso, Professor
from .serializers import AlunoSerializer, CursoSerializer, ProfessorSerializer


class AlunoViewSet(CRUDViewSet):
    queryset = Aluno.objects.select_related('usuario', 'curso', 'orientador_atual')
    serializer_class = AlunoSerializer
    search_fields = ['nome', 'matricula', 'email']
    ordering_fields = ['id', 'nome', 'matricula']


class ProfessorViewSet(CRUDViewSet):
    queryset = Professor.objects.select_related('usuario')
    serializer_class = ProfessorSerializer
    search_fields = ['nome', 'email', 'departamento', 'area_pesquisa']
    ordering_fields = ['id', 'nome']


class CursoViewSet(CRUDViewSet):
    queryset = Curso.objects.select_related('coordenador')
    serializer_class = CursoSerializer
    search_fields = ['nome', 'codigo']
    ordering_fields = ['id', 'nome', 'codigo']
