from django.http import Http404
from django.urls import reverse

from .forms import AlunoForm, CursoForm, ProfessorForm
from .models import Aluno, Curso, Professor
from .serializers import AlunoSerializer, CursoSerializer, ProfessorSerializer


RECURSOS = {
    'aluno': {
        'titulo': 'Alunos', 'singular': 'aluno', 'form': AlunoForm,
        'serializer': AlunoSerializer, 'queryset': Aluno.objects.select_related('usuario', 'curso', 'orientador_atual'),
        'api': 'aluno', 'descricao': 'Cadastre os autores e vincule cada aluno ao seu curso.',
        'colunas': [('nome', 'Nome'), ('matricula', 'Matrícula'), ('curso_nome', 'Curso'), ('email', 'E-mail')],
        'campos': [('nome', 'Nome'), ('usuario_nome', 'Conta de acesso'), ('matricula', 'Matrícula'), ('email', 'E-mail'), ('curso_nome', 'Curso'), ('orientador_nome', 'Orientador atual')],
    },
    'professor': {
        'titulo': 'Professores', 'singular': 'professor', 'form': ProfessorForm,
        'serializer': ProfessorSerializer, 'queryset': Professor.objects.select_related('usuario'),
        'api': 'professor', 'descricao': 'Organize orientadores, coordenadores e avaliadores internos.',
        'colunas': [('nome', 'Nome'), ('email', 'E-mail'), ('departamento', 'Departamento'), ('area_pesquisa', 'Área de pesquisa')],
        'campos': [('nome', 'Nome'), ('usuario_nome', 'Conta de acesso'), ('email', 'E-mail'), ('departamento', 'Departamento'), ('area_pesquisa', 'Área de pesquisa')],
    },
    'curso': {
        'titulo': 'Cursos', 'singular': 'curso', 'form': CursoForm,
        'serializer': CursoSerializer, 'queryset': Curso.objects.select_related('coordenador'),
        'api': 'curso', 'descricao': 'Mantenha os cursos e seus professores coordenadores.',
        'colunas': [('nome', 'Nome'), ('codigo', 'Código'), ('coordenador_nome', 'Coordenador')],
    },
}


def recurso(tipo):
    if tipo not in RECURSOS:
        raise Http404('Cadastro acadêmico inexistente.')
    config = dict(RECURSOS[tipo])
    config.update({
        'lista_url': reverse('equipe:index') + f'?tipo={tipo}',
        'adicionar_url': reverse('equipe:adicionar') + f'?tipo={tipo}',
        'detalhes_url': reverse('equipe:detalhes', args=[tipo, 0]),
        'editar_url': reverse('equipe:editar', args=[tipo, 0]),
        'excluir_url': reverse('equipe:excluir', args=[tipo, 0]),
        'navegacao': [{'titulo': item['titulo'], 'url': reverse('equipe:index') + f'?tipo={chave}', 'ativo': chave == tipo} for chave, item in RECURSOS.items()],
    })
    return config
