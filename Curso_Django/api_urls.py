from rest_framework.routers import DefaultRouter

from equipe.api import AlunoViewSet, CursoViewSet, ProfessorViewSet
from monografias.api import MonografiaViewSet, BancaViewSet, MembroExternoViewSet, ParticipacaoBancaViewSet

router = DefaultRouter()
router.register('alunos', AlunoViewSet)
router.register('professores', ProfessorViewSet)
router.register('cursos', CursoViewSet)
router.register('monografias', MonografiaViewSet)
router.register('bancas', BancaViewSet)
router.register('membros-externos', MembroExternoViewSet)
router.register('participacoes-banca', ParticipacaoBancaViewSet)

urlpatterns = router.urls
