from Curso_Django.api import CRUDViewSet

from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca
from .serializers import AvaliacaoSerializer, BancaSerializer, MembroExternoSerializer, MonografiaSerializer, ParticipacaoBancaSerializer


class MonografiaViewSet(CRUDViewSet):
    queryset = Monografia.objects.select_related('aluno', 'curso', 'orientador', 'coorientador')
    serializer_class = MonografiaSerializer
    search_fields = ['titulo', 'resumo', 'aluno__nome', 'curso__nome', 'orientador__nome']
    ordering_fields = ['id', 'titulo', 'data_publicacao']


class BancaViewSet(CRUDViewSet):
    queryset = Banca.objects.select_related('monografia')
    serializer_class = BancaSerializer
    search_fields = ['monografia__titulo', 'local']
    ordering_fields = ['id', 'inicio', 'fim']


class MembroExternoViewSet(CRUDViewSet):
    queryset = MembroExterno.objects.all()
    serializer_class = MembroExternoSerializer
    search_fields = ['nome', 'email', 'instituicao']
    ordering_fields = ['id', 'nome']


class ParticipacaoBancaViewSet(CRUDViewSet):
    queryset = ParticipacaoBanca.objects.select_related('banca__monografia', 'professor', 'membro_externo')
    serializer_class = ParticipacaoBancaSerializer
    search_fields = ['professor__nome', 'membro_externo__nome']
    ordering_fields = ['id', 'banca']


class AvaliacaoViewSet(CRUDViewSet):
    queryset = Avaliacao.objects.select_related('participacao__banca__monografia', 'participacao__professor', 'participacao__membro_externo')
    serializer_class = AvaliacaoSerializer
    search_fields = ['parecer', 'participacao__banca__monografia__titulo']
    ordering_fields = ['id', 'nota', 'registrada_em']
