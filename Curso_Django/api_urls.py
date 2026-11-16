from rest_framework.routers import DefaultRouter

from equipe.api import AlunoViewSet, CursoViewSet, ProfessorViewSet

router = DefaultRouter()
router.register('alunos', AlunoViewSet)
router.register('professores', ProfessorViewSet)
router.register('cursos', CursoViewSet)

urlpatterns = router.urls
