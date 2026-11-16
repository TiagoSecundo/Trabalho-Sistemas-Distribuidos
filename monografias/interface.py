from django.http import Http404
from django.urls import reverse

from .forms import AvaliacaoForm, BancaForm, MembroExternoForm, MonografiaForm, ParticipacaoBancaForm
from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca
from .serializers import AvaliacaoSerializer, BancaSerializer, MembroExternoSerializer, MonografiaSerializer, ParticipacaoBancaSerializer


RECURSOS = {
    'monografias': {
        'titulo': 'Monografias', 'singular': 'monografia', 'api': 'monografia',
        'form': MonografiaForm, 'serializer': MonografiaSerializer,
        'queryset': Monografia.objects.select_related('aluno', 'curso', 'orientador', 'coorientador'),
        'descricao': 'Organize trabalhos, autores e orientações em um só lugar.',
        'ajuda': 'Cadastre professores, cursos e alunos antes de adicionar um trabalho. O curso deve ser o mesmo do aluno.',
        'colunas': [('titulo', 'Título'), ('aluno_nome', 'Aluno'), ('curso_nome', 'Curso'), ('orientador_nome', 'Orientador'), ('status_descricao', 'Situação')],
        'campos': [('titulo', 'Título'), ('aluno_nome', 'Aluno'), ('curso_nome', 'Curso'), ('orientador_nome', 'Orientador'), ('coorientador_nome', 'Coorientador'), ('status_descricao', 'Situação'), ('palavras_chave', 'Palavras-chave'), ('resumo', 'Resumo'), ('data_publicacao', 'Data de publicação')],
    },
    'bancas': {
        'titulo': 'Bancas', 'singular': 'banca', 'api': 'banca',
        'form': BancaForm, 'serializer': BancaSerializer, 'queryset': Banca.objects.select_related('monografia'),
        'descricao': 'Organize os horários, locais e modalidades das defesas.',
        'ajuda': 'Após cadastrar a banca, inclua seus participantes. Este cadastro ainda não verifica disponibilidade nem confirma convites.',
        'colunas': [('monografia_titulo', 'Monografia'), ('inicio', 'Início'), ('modalidade_descricao', 'Modalidade'), ('status_descricao', 'Situação')],
        'campos': [('monografia_titulo', 'Monografia'), ('inicio', 'Início'), ('fim', 'Término'), ('modalidade_descricao', 'Modalidade'), ('local', 'Local'), ('link', 'Link da reunião'), ('status_descricao', 'Situação')],
    },
    'participacoes-banca': {
        'titulo': 'Participantes de bancas', 'singular': 'participação', 'api': 'participacaobanca',
        'form': ParticipacaoBancaForm, 'serializer': ParticipacaoBancaSerializer,
        'queryset': ParticipacaoBanca.objects.select_related('banca__monografia', 'professor', 'membro_externo'),
        'descricao': 'Vincule professores e membros externos às bancas de monografia.',
        'ajuda': 'Escolha exatamente um professor ou um membro externo para cada participação.',
        'colunas': [('participante_nome', 'Participante'), ('monografia_titulo', 'Monografia'), ('papel_descricao', 'Papel'), ('convite_descricao', 'Convite')],
    },
    'membros-externos': {
        'titulo': 'Membros externos', 'singular': 'membro externo', 'api': 'membroexterno',
        'form': MembroExternoForm, 'serializer': MembroExternoSerializer, 'queryset': MembroExterno.objects.all(),
        'descricao': 'Cadastre avaliadores de outras instituições para compor as bancas.',
        'colunas': [('nome', 'Nome'), ('email', 'E-mail'), ('instituicao', 'Instituição')],
    },
    'avaliacoes': {
        'titulo': 'Avaliações', 'singular': 'avaliação', 'api': 'avaliacao',
        'form': AvaliacaoForm, 'serializer': AvaliacaoSerializer,
        'queryset': Avaliacao.objects.select_related('participacao__banca__monografia', 'participacao__professor', 'participacao__membro_externo'),
        'descricao': 'Registre notas, pareceres e recomendações por participante.',
        'ajuda': 'Cada participante recebe uma avaliação. O cadastro administrativo não fecha o resultado da defesa.',
        'colunas': [('monografia_titulo', 'Monografia'), ('participante_nome', 'Avaliador'), ('nota', 'Nota'), ('recomendacao_descricao', 'Recomendação')],
        'campos': [('monografia_titulo', 'Monografia'), ('participante_nome', 'Avaliador'), ('nota', 'Nota'), ('parecer', 'Parecer'), ('recomendacao_descricao', 'Recomendação'), ('registrada_em', 'Registrada em'), ('finalizada_em', 'Finalizada em')],
    },
}


def url_lista(tipo):
    return reverse('monografias:index') if tipo == 'monografias' else reverse('monografias:recurso-lista', args=[tipo])


def recurso(tipo='monografias'):
    if tipo not in RECURSOS:
        raise Http404('Recurso inexistente.')
    config = dict(RECURSOS[tipo])
    config['lista_url'] = url_lista(tipo)
    for acao in ('adicionar', 'detalhes', 'editar', 'excluir'):
        args = [] if tipo == 'monografias' else [tipo]
        if acao != 'adicionar':
            args.append(0)
        nome = acao if tipo == 'monografias' else f'recurso-{acao}'
        config[f'{acao}_url'] = reverse(f'monografias:{nome}', args=args)
    config['navegacao'] = [{'titulo': item['titulo'], 'url': url_lista(chave), 'ativo': chave == tipo} for chave, item in RECURSOS.items()]
    return config
