from Curso_Django.api import CRUDViewSet

from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca
from .serializers import MonografiaSerializer


class MonografiaViewSet(CRUDViewSet):
    queryset = Monografia.objects.select_related('aluno', 'curso', 'orientador', 'coorientador')
    serializer_class = MonografiaSerializer
    search_fields = ['titulo', 'resumo', 'aluno__nome', 'curso__nome', 'orientador__nome']
    ordering_fields = ['id', 'titulo', 'data_publicacao']
