from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import APIRootView, DefaultRouter

from equipe.api import AlunoViewSet, CursoViewSet, ProfessorViewSet
from monografias.api import AvaliacaoViewSet, BancaViewSet, MembroExternoViewSet, MonografiaViewSet, ParticipacaoBancaViewSet
from usuarios.roles import obter_papeis


class RaizAPIPorPerfil(APIRootView):
    """Recursos disponíveis para a conta autenticada no sistema principal."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        papeis = obter_papeis(request.user)
        dados = {'papeis': papeis, 'me': reverse('me', request=request)}
        if papeis:
            dados['minhas-monografias'] = reverse('minhas-monografias', request=request)
        if 'Aluno' in papeis:
            dados['meus-rascunhos'] = reverse('meus-rascunhos', request=request)
        if 'Administrador' in papeis:
            dados.update(super().get(request, *args, **kwargs).data)
        return Response(dados)


class RouterPorPerfil(DefaultRouter):
    APIRootView = RaizAPIPorPerfil


router = RouterPorPerfil()
router.register('alunos', AlunoViewSet)
router.register('professores', ProfessorViewSet)
router.register('cursos', CursoViewSet)
router.register('monografias', MonografiaViewSet)
router.register('bancas', BancaViewSet)
router.register('avaliacoes', AvaliacaoViewSet)
router.register('membros-externos', MembroExternoViewSet)
router.register('participacoes-banca', ParticipacaoBancaViewSet)

urlpatterns = router.urls
