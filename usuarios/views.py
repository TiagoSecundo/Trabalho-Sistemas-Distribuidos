from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe

from Curso_Django.interface import preparar_formulario
from Curso_Django.services import OperacaoNaoPermitida
from equipe.models import Aluno, Curso, Professor
from monografias.models import Banca, Monografia, ParticipacaoBanca
from monografias.services import MonografiaService
from .consultas import monografias_visiveis
from .forms import ConfirmarConviteForm, RascunhoAlunoForm
from .roles import obter_papeis
from .services import confirmar_convite_externo, emitir_convite_externo, excluir_rascunho, exigir_aluno, salvar_rascunho


PERFIS = {
    'aluno': {'papel': 'Aluno', 'titulo': 'Meu percurso acadêmico', 'descricao': 'Organize seus rascunhos e acompanhe seus trabalhos.', 'lista': 'Meus trabalhos'},
    'professor': {'papel': 'Professor', 'titulo': 'Orientações e coorientações', 'descricao': 'Acompanhe os trabalhos vinculados à sua orientação.', 'lista': 'Trabalhos orientados'},
    'coordenador': {'papel': 'Coordenador', 'titulo': 'Coordenação acadêmica', 'descricao': 'Acompanhe os trabalhos e as bancas dos seus cursos.', 'lista': 'Trabalhos dos meus cursos'},
    'administrador': {'papel': 'Administrador', 'titulo': 'Gestão acadêmica', 'descricao': 'Gerencie os cadastros e acompanhe o panorama da instituição.', 'lista': 'Todos os trabalhos'},
}


def contexto_perfil(request, perfil=None):
    papeis = obter_papeis(request.user)
    disponiveis = [dict(dados, slug=slug, url=reverse('usuarios:perfil', args=[slug]))
                   for slug, dados in PERFIS.items() if dados['papel'] in papeis]
    if perfil is not None and (perfil not in PERFIS or PERFIS[perfil]['papel'] not in papeis):
        raise PermissionDenied('Seu cadastro não permite acessar este perfil.')
    ativo = next((item for item in disponiveis if item['slug'] == perfil), None)
    if ativo is None and disponiveis:
        ativo = disponiveis[-1]
    return {'usuario': request.user, 'papeis': papeis, 'perfis': disponiveis, 'perfil': ativo}


@never_cache
@login_required
@require_safe
def painel(request, perfil=None):
    context = contexto_perfil(request, perfil)
    ativo = context['perfil']
    if ativo is None:
        return render(request, 'usuarios/painel.html', context)
    trabalhos = monografias_visiveis(request.user, ativo['papel'])
    context['resumo'] = trabalhos.aggregate(
        total=Count('pk'), rascunhos=Count('pk', filter=Q(status_fluxo='RASCUNHO')),
        publicados=Count('pk', filter=Q(status_fluxo='PUBLICADA')),
    )
    bancas = Banca.objects.filter(monografia__in=trabalhos, status='AGENDADA', fim__gte=timezone.now())
    context['total_bancas'] = bancas.count()
    context['proximas_bancas'] = bancas.select_related('monografia').order_by('inicio', 'pk')[:5]
    busca = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    if busca:
        trabalhos = trabalhos.filter(Q(titulo__icontains=busca) | Q(aluno__nome__icontains=busca) | Q(curso__nome__icontains=busca))
    if estado in dict(Monografia.STATUS):
        trabalhos = trabalhos.filter(status_fluxo=estado)
    else:
        estado = ''
    context.update({
        'pagina': Paginator(trabalhos.order_by('-pk'), 10).get_page(request.GET.get('page')),
        'busca': busca, 'estado': estado, 'estados': Monografia.STATUS,
    })
    if ativo['papel'] == 'Aluno':
        context['aluno'] = Aluno.objects.select_related('curso').get(usuario=request.user)
    elif ativo['papel'] == 'Professor':
        context['professor'] = Professor.objects.get(usuario=request.user)
    elif ativo['papel'] == 'Coordenador':
        context['cursos'] = Curso.objects.filter(coordenador__usuario=request.user).order_by('nome')
    else:
        context['cadastros'] = {'alunos': Aluno.objects.count(), 'professores': Professor.objects.count(), 'cursos': Curso.objects.count()}
    return render(request, 'usuarios/painel.html', context)


@never_cache
@login_required
@require_safe
def trabalho(request, pk):
    context = contexto_perfil(request, request.GET.get('perfil'))
    monografia = get_object_or_404(monografias_visiveis(request.user), pk=pk)
    bancas = monografia.bancas.prefetch_related('participacoes__professor', 'participacoes__membro_externo').order_by('-inicio')
    context.update({
        'monografia': monografia, 'bancas': bancas,
        'pode_editar': 'Aluno' in context['papeis'] and monografia.aluno.usuario_id == request.user.pk and monografia.status_fluxo == 'RASCUNHO',
        'pode_convidar': request.user.is_staff or ('Coordenador' in context['papeis'] and Curso.objects.filter(pk=monografia.curso_id, coordenador__usuario=request.user).exists()),
        'convite_liberado': monografia.status_fluxo in ('APROVADA_ORIENTADOR', 'BANCA_AGENDADA'),
    })
    return render(request, 'usuarios/trabalho.html', context)


def config_rascunho(pk=None):
    return {
        'endpoint': reverse('meus-rascunhos'), 'id': pk,
        'lista': reverse('usuarios:perfil', args=['aluno']),
        'detalhes': reverse('usuarios:trabalho', args=[0]),
        'login': reverse('account_login'),
    }


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def rascunho(request, pk=None):
    context = contexto_perfil(request, 'aluno')
    aluno = exigir_aluno(request.user)
    instance = get_object_or_404(monografias_visiveis(request.user, 'Aluno'), pk=pk) if pk else Monografia(aluno=aluno, curso=aluno.curso)
    form = RascunhoAlunoForm(request.POST if request.method == 'POST' else None, instance=instance)
    codigo = 200
    try:
        if pk:
            MonografiaService.validar_alteracao(instance)
        if request.method == 'POST' and form.is_valid():
            salvo = salvar_rascunho(request.user, form.cleaned_data, instance if pk else None)
            messages.success(request, 'Rascunho salvo com sucesso.')
            return redirect('usuarios:trabalho', pk=salvo.pk)
    except OperacaoNaoPermitida as exc:
        context['erro'] = str(exc)
        codigo = 409
    except ValidationError as exc:
        form.add_error(None, ' '.join(exc.messages))
    except IntegrityError:
        form.add_error(None, 'Os vínculos foram alterados. Atualize a página e tente novamente.')
        codigo = 409
    preparar_formulario(form)
    context.update({'form': form, 'editando': bool(pk), 'api_config': config_rascunho(pk)})
    return render(request, 'usuarios/rascunho.html', context, status=codigo)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def excluir(request, pk):
    context = contexto_perfil(request, 'aluno')
    instance = get_object_or_404(monografias_visiveis(request.user, 'Aluno'), pk=pk)
    codigo = 200
    try:
        MonografiaService.validar_alteracao(instance)
        if request.method == 'POST':
            excluir_rascunho(request.user, instance)
            messages.success(request, 'Rascunho excluído com sucesso.')
            return redirect('usuarios:perfil', perfil='aluno')
    except (OperacaoNaoPermitida, ProtectedError):
        context['erro'] = 'Este trabalho não pode ser excluído: confira o estado e os vínculos com bancas.'
        codigo = 409
    context.update({'monografia': instance, 'api_config': config_rascunho(pk)})
    return render(request, 'usuarios/excluir.html', context, status=codigo)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def emitir_convite(request, pk):
    context = contexto_perfil(request)
    if not {'Coordenador', 'Administrador'}.intersection(context['papeis']):
        raise PermissionDenied
    # Coordenação fica limitada ao curso, mesmo que também tenha outro papel.
    participacoes = ParticipacaoBanca.objects.select_related('banca__monografia', 'membro_externo')
    if not request.user.is_staff:
        participacoes = participacoes.filter(banca__monografia__curso__coordenador__usuario=request.user)
    participacao = get_object_or_404(participacoes, pk=pk, membro_externo__isnull=False)
    context.update({'participacao': participacao, 'url_confirmacao': request.build_absolute_uri(reverse('usuarios:confirmar-convite', args=[pk]))})
    codigo = 200
    if request.method == 'POST':
        try:
            participacao, token = emitir_convite_externo(request.user, pk)
            context.update({'token': token, 'expira_em': participacao.expira_em})
        except ValidationError as exc:
            context['erro'] = ' '.join(exc.messages)
            codigo = 400
    return render(request, 'usuarios/emitir_convite.html', context, status=codigo)


@never_cache
@require_http_methods(['GET', 'POST'])
def confirmar_convite(request, pk):
    # Não consulta nem expõe dados acadêmicos antes de validar a posse do token.
    form = ConfirmarConviteForm(request.POST if request.method == 'POST' else None)
    confirmado = False
    codigo = 200
    if request.method == 'POST' and form.is_valid():
        try:
            confirmar_convite_externo(pk, form.cleaned_data['token'])
            confirmado = True
        except (PermissionDenied, Http404):
            form.add_error(None, 'Convite inválido, expirado ou já confirmado. Solicite um novo código à coordenação.')
            codigo = 403
    return render(request, 'usuarios/confirmar_convite.html', {'form': form, 'confirmado': confirmado}, status=codigo)
