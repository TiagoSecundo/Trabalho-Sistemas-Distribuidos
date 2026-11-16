from rest_framework.routers import DefaultRouter

from equipe.api import AlunoViewSet, CursoViewSet, ProfessorViewSet
from monografias.api import MonografiaViewSet

router = DefaultRouter()
router.register('alunos', AlunoViewSet)
router.register('professores', ProfessorViewSet)
router.register('cursos', CursoViewSet)
router.register('monografias', MonografiaViewSet)

urlpatterns = router.urls
