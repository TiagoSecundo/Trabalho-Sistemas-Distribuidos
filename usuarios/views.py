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
from django.views.decorators.http import require_http_methods, require_safe, require_POST

from Curso_Django.interface import preparar_formulario
from Curso_Django.services import OperacaoNaoPermitida
from equipe.models import Aluno, Curso, Professor
from monografias.models import Avaliacao, Banca, Monografia, ParticipacaoBanca
from monografias.services import MonografiaService
from .consultas import monografias_visiveis
from .forms import AvaliacaoExternaForm, AvaliacaoPropriaForm, ConfirmarConviteForm, RascunhoAlunoForm, PropostaBancaForm, ParticipantePropostaForm
from .roles import obter_papeis, pode_convidar_para_banca
from .agendamento import (
    adicionar_participante, cancelar_proposta, propor_banca, responder_convite_interno, retirar_participante,
)
from .avaliacao_externa import emitir_codigo_avaliacao_externa, registrar_avaliacao_externa
from .services import (
    calcular_resultado_banca, confirmar_convite_externo, emitir_convite_externo,
    excluir_rascunho, exigir_aluno, finalizar_resultado_banca,
    registrar_avaliacao_propria, registrar_defesa_realizada, salvar_rascunho,
)


PERFIS = {
    'aluno': {'papel': 'Aluno', 'titulo': 'Meu percurso acadêmico', 'descricao': 'Organize seus rascunhos e acompanhe seus trabalhos.', 'lista': 'Meus trabalhos'},
    'professor': {'papel': 'Professor', 'titulo': 'Orientações e bancas', 'descricao': 'Acompanhe suas orientações, coorientações e participações como avaliador.', 'lista': 'Meus trabalhos acadêmicos'},
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
    if ativo['papel'] == 'Professor':
        context['participacoes'] = ParticipacaoBanca.objects.filter(
            professor__usuario=request.user, banca__status__in=['PENDENTE', 'AGENDADA', 'REALIZADA'],
        ).select_related('banca__monografia').order_by('-banca__inicio', '-pk')[:5]
        vinculo = request.GET.get('vinculo', '')
        if vinculo == 'orientacoes':
            trabalhos = trabalhos.filter(Q(orientador__usuario=request.user) | Q(coorientador__usuario=request.user))
        elif vinculo == 'bancas':
            trabalhos = trabalhos.filter(bancas__participacoes__professor__usuario=request.user,
                                         bancas__status__in=['PENDENTE', 'AGENDADA', 'REALIZADA']).distinct()
        else:
            vinculo = ''
        context['vinculo'] = vinculo
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
    papel = context['perfil']['papel'] if request.GET.get('perfil') else None
    monografia = get_object_or_404(monografias_visiveis(request.user, papel), pk=pk)
    bancas = list(monografia.bancas.prefetch_related(
        'participacoes__professor', 'participacoes__membro_externo', 'participacoes__avaliacao',
    ).order_by('-inicio'))
    if monografia.status_fluxo in ('APROVADA', 'APROVADA_COM_RESSALVAS', 'REPROVADA'):
        for banca in bancas:
            if banca.status == 'REALIZADA':
                try:
                    banca.media_final, _ = calcular_resultado_banca(banca)
                except ValidationError:
                    banca.media_final = None
    context.update({
        'monografia': monografia, 'bancas': bancas,
        'pode_editar': 'Aluno' in context['papeis'] and monografia.aluno.usuario_id == request.user.pk and monografia.status_fluxo == 'RASCUNHO',
        'pode_convidar': pode_convidar_para_banca(request.user, monografia),
        'convite_liberado': monografia.status_fluxo in ('APROVADA_ORIENTADOR', 'BANCA_AGENDADA'),
        'pode_propor_banca': (
            pode_convidar_para_banca(request.user, monografia)
            and monografia.status_fluxo == 'APROVADA_ORIENTADOR'
            and not monografia.bancas.filter(status__in=['PENDENTE', 'AGENDADA']).exists()
        ),
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
    if not {'Professor', 'Coordenador', 'Administrador'}.intersection(context['papeis']):
        raise PermissionDenied
    participacoes = ParticipacaoBanca.objects.select_related(
        'banca__monografia__orientador', 'banca__monografia__curso__coordenador', 'membro_externo',
    )
    participacao = get_object_or_404(participacoes, pk=pk, membro_externo__isnull=False)
    if not pode_convidar_para_banca(request.user, participacao.banca.monografia):
        raise Http404
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
    recusado = False
    if request.method == 'POST' and form.is_valid():
        try:
            acao = request.POST.get('acao', 'confirmar')
            if acao not in ('confirmar', 'recusar'):
                raise ValidationError('Escolha uma resposta válida.')
            confirmar_convite_externo(pk, form.cleaned_data['token'], aceitar=acao == 'confirmar')
            confirmado = acao == 'confirmar'
            recusado = acao == 'recusar'
        except (PermissionDenied, Http404):
            form.add_error(None, 'Convite inválido, expirado ou já respondido. Solicite um novo código à coordenação.')
            codigo = 403
        except ValidationError as exc:
            form.add_error(None, ' '.join(exc.messages))
            codigo = 400
        except OperacaoNaoPermitida as exc:
            form.add_error(None, str(exc))
            codigo = 409
    return render(request, 'usuarios/confirmar_convite.html', {'form': form, 'confirmado': confirmado, 'recusado': recusado}, status=codigo)


@never_cache
@login_required
@require_POST
def realizar_defesa(request, pk):
    banca = get_object_or_404(Banca, pk=pk)
    try:
        registrar_defesa_realizada(request.user, pk)
        messages.success(request, 'Defesa registrada como realizada. Os titulares já podem avaliar.')
    except (OperacaoNaoPermitida, ValidationError) as exc:
        messages.error(request, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    return redirect('usuarios:trabalho', pk=banca.monografia_id)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def avaliar_participacao(request, pk):
    participacao = get_object_or_404(
        ParticipacaoBanca.objects.select_related('banca__monografia', 'professor'),
        pk=pk, professor__usuario=request.user,
    )
    context = contexto_perfil(request, 'professor')
    avaliacao = Avaliacao.objects.filter(participacao=participacao).first()
    if avaliacao and avaliacao.finalizada_em:
        messages.error(request, 'Esta avaliação já está finalizada.')
        return redirect('usuarios:trabalho', pk=participacao.banca.monografia_id)
    form = AvaliacaoPropriaForm(request.POST if request.method == 'POST' else None, instance=avaliacao)
    if request.method == 'POST' and form.is_valid():
        try:
            registrar_avaliacao_propria(request.user, pk, form.cleaned_data)
            messages.success(request, 'Avaliação registrada com sucesso.')
            return redirect('usuarios:trabalho', pk=participacao.banca.monografia_id)
        except (OperacaoNaoPermitida, ValidationError) as exc:
            form.add_error(None, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    context.update({'participacao': participacao, 'form': form})
    return render(request, 'usuarios/avaliar.html', context)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def emitir_codigo_avaliacao_externa_view(request, pk):
    participacao = get_object_or_404(
        ParticipacaoBanca.objects.select_related('banca__monografia'),
        pk=pk, membro_externo__isnull=False,
    )
    if not pode_convidar_para_banca(request.user, participacao.banca.monografia):
        raise Http404
    context = contexto_perfil(request)
    context.update({
        'participacao': participacao,
        'url_avaliacao': request.build_absolute_uri(reverse('usuarios:avaliacao-externa', args=[pk])),
    })
    codigo_http = 200
    if request.method == 'POST':
        try:
            participacao, codigo = emitir_codigo_avaliacao_externa(request.user, pk)
            context.update({'codigo_avaliacao': codigo, 'expira_em': participacao.avaliacao_expira_em})
        except (OperacaoNaoPermitida, ValidationError) as exc:
            context['erro'] = ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
            codigo_http = 409
    return render(request, 'usuarios/emitir_avaliacao_externa.html', context, status=codigo_http)


@never_cache
@require_http_methods(['GET', 'POST'])
def avaliacao_externa_view(request, pk):
    # A página pública não identifica o trabalho nem o participante sem código válido.
    form = AvaliacaoExternaForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            registrar_avaliacao_externa(pk, form.cleaned_data['codigo'], form.cleaned_data)
            return render(request, 'usuarios/avaliacao_externa.html', {'enviada': True})
        except (PermissionDenied, Http404):
            form.add_error('codigo', 'Código inválido ou expirado. Solicite um novo código à coordenação.')
            return render(request, 'usuarios/avaliacao_externa.html', {'form': form}, status=403)
        except (OperacaoNaoPermitida, ValidationError) as exc:
            form.add_error(None, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
            return render(request, 'usuarios/avaliacao_externa.html', {'form': form}, status=409)
    return render(request, 'usuarios/avaliacao_externa.html', {'form': form})


@never_cache
@login_required
@require_POST
def finalizar_banca(request, pk):
    banca = get_object_or_404(Banca, pk=pk)
    try:
        media, resultado = finalizar_resultado_banca(request.user, pk)
        messages.success(request, f'Resultado finalizado: média {media} — {dict(Monografia.STATUS)[resultado]}.')
    except (OperacaoNaoPermitida, ValidationError) as exc:
        messages.error(request, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    return redirect('usuarios:trabalho', pk=banca.monografia_id)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def propor_banca_view(request, pk):
    monografia = get_object_or_404(Monografia, pk=pk)
    if not pode_convidar_para_banca(request.user, monografia):
        raise PermissionDenied
    context = contexto_perfil(request)
    form = PropostaBancaForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            banca = propor_banca(request.user, pk, form.cleaned_data)
            messages.success(request, 'Proposta criada. Adicione os participantes e aguarde as confirmações.')
            return redirect('usuarios:adicionar-participante', pk=banca.pk)
        except (OperacaoNaoPermitida, ValidationError, IntegrityError) as exc:
            form.add_error(None, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    context.update({'form': form, 'monografia': monografia})
    return render(request, 'usuarios/propor_banca.html', context)


@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def adicionar_participante_view(request, pk):
    banca = get_object_or_404(Banca.objects.select_related('monografia'), pk=pk)
    if not pode_convidar_para_banca(request.user, banca.monografia):
        raise PermissionDenied
    if banca.status != 'PENDENTE':
        return redirect('usuarios:trabalho', pk=banca.monografia_id)
    context = contexto_perfil(request)
    form = ParticipantePropostaForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            adicionar_participante(request.user, pk, form.cleaned_data)
            messages.success(request, 'Participante incluído na proposta.')
            return redirect('usuarios:trabalho', pk=banca.monografia_id)
        except (OperacaoNaoPermitida, ValidationError, IntegrityError) as exc:
            form.add_error(None, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    context.update({'form': form, 'banca': banca})
    return render(request, 'usuarios/adicionar_participante.html', context)


@never_cache
@login_required
@require_POST
def responder_convite_interno_view(request, pk):
    participacao = get_object_or_404(ParticipacaoBanca, pk=pk)
    acao = request.POST.get('acao')
    if acao not in ('confirmar', 'recusar'):
        messages.error(request, 'Resposta inválida.')
        return redirect('usuarios:trabalho', pk=participacao.banca.monografia_id)
    try:
        agendada = responder_convite_interno(request.user, pk, acao == 'confirmar')
        messages.success(request, 'Banca agendada após todas as confirmações.' if agendada else 'Resposta registrada.')
    except (OperacaoNaoPermitida, ValidationError) as exc:
        messages.error(request, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    return redirect('usuarios:trabalho', pk=participacao.banca.monografia_id)


@never_cache
@login_required
@require_POST
def retirar_participante_view(request, pk):
    participacao = get_object_or_404(ParticipacaoBanca, pk=pk)
    trabalho_pk = participacao.banca.monografia_id
    try:
        retirar_participante(request.user, pk)
        messages.success(request, 'Participante retirado. É possível convidar um substituto.')
    except (OperacaoNaoPermitida, ValidationError) as exc:
        messages.error(request, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    return redirect('usuarios:trabalho', pk=trabalho_pk)


@never_cache
@login_required
@require_POST
def cancelar_proposta_view(request, pk):
    banca = get_object_or_404(Banca, pk=pk)
    try:
        cancelar_proposta(request.user, pk)
        messages.success(request, 'Proposta cancelada. Você já pode criar outra proposta.')
    except (OperacaoNaoPermitida, ValidationError) as exc:
        messages.error(request, ' '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc))
    return redirect('usuarios:trabalho', pk=banca.monografia_id)
