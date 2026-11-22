"""Escritas acadêmicas compartilhadas entre HTML e API."""
from decimal import Decimal, ROUND_HALF_UP

from Curso_Django.services import OperacaoNaoPermitida
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from equipe.models import Aluno
from monografias.models import Avaliacao, Banca, HistoricoAcao, Monografia, ParticipacaoBanca
from monografias.services import MonografiaService
from .convites import emitir_token, validar_token
from .agendamento import responder_convite_externo
from .roles import obter_papeis, pode_convidar_para_banca


def exigir_aluno(usuario):
    if 'Aluno' not in obter_papeis(usuario):
        raise PermissionDenied('Esta operação exige um perfil de aluno vinculado.')
    return get_object_or_404(Aluno.objects.select_related('curso'), usuario=usuario)


@transaction.atomic
def salvar_rascunho(usuario, dados, instance=None):
    aluno = exigir_aluno(usuario)
    dados = dict(dados)
    # A identidade nunca é escolhida pelo formulário ou pelo cliente JSON.
    dados['aluno'] = aluno
    dados['curso'] = aluno.curso
    if instance is None:
        instance = MonografiaService.criar(Monografia, dados)
        acao = 'RASCUNHO_CRIADO'
    else:
        instance = get_object_or_404(
            Monografia.objects.select_for_update(of=('self',)),
            pk=instance.pk, aluno__usuario=usuario,
        )
        instance = MonografiaService.atualizar(instance, dados)
        acao = 'RASCUNHO_ALTERADO'
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'Monografia:{instance.pk}', acao=acao,
        detalhes={'monografia_id': instance.pk},
    )
    return instance


@transaction.atomic
def excluir_rascunho(usuario, instance):
    exigir_aluno(usuario)
    instance = get_object_or_404(
        Monografia.objects.select_for_update(of=('self',)),
        pk=instance.pk, aluno__usuario=usuario,
    )
    pk = instance.pk
    MonografiaService.excluir(instance)
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'Monografia:{pk}', acao='RASCUNHO_EXCLUIDO',
        detalhes={'monografia_id': pk},
    )


@transaction.atomic
def emitir_convite_externo(usuario, pk):
    participacao = get_object_or_404(
        ParticipacaoBanca.objects.select_for_update(of=('self',)).select_related(
            'banca__monografia__curso__coordenador', 'banca__monografia__orientador', 'membro_externo',
        ), pk=pk,
    )
    if not pode_convidar_para_banca(usuario, participacao.banca.monografia):
        raise PermissionDenied('Apenas o orientador, a coordenação deste curso ou a administração pode emitir o convite.')
    if participacao.membro_externo_id is None:
        raise ValidationError({'participacao': 'Esta participação não é de membro externo.'})
    if participacao.banca.monografia.status_fluxo not in ('APROVADA_ORIENTADOR', 'BANCA_AGENDADA'):
        raise ValidationError({'monografia': 'A submissão precisa ser aprovada pelo orientador.'})
    if participacao.banca.status not in ('PENDENTE', 'AGENDADA') or participacao.convite_status != 'CONVIDADO':
        raise ValidationError({'convite': 'Esta participação não está aguardando convite.'})
    token = emitir_token(participacao)
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'ParticipacaoBanca:{participacao.pk}',
        acao='CONVITE_EXTERNO_EMITIDO', detalhes={'participacao_id': participacao.pk},
    )
    return participacao, token


def confirmar_convite_externo(pk, token, aceitar=True):
    """O token autoriza apenas responder a um convite específico."""
    return responder_convite_externo(pk, token, aceitar, validar_token)


# B11 — decisões acadêmicas: média simples, nota mínima 6,00 e ressalvas
# quando houver pelo menos uma recomendação APROVADA_COM_RESSALVAS.
PAPEIS_AVALIADORES = ('PRESIDENTE', 'AVALIADOR')
MEDIA_MINIMA_APROVACAO = Decimal('6.00')


def _avaliacoes_titulares(banca):
    """Não conta suplentes e não permite encerrar com um titular recusado."""
    participacoes = list(ParticipacaoBanca.objects.filter(
        banca=banca, papel__in=PAPEIS_AVALIADORES,
    ).order_by('pk'))
    if not participacoes:
        raise ValidationError('A banca precisa de pelo menos um avaliador titular.')
    if any(p.convite_status == 'RECUSADO' for p in participacoes):
        raise ValidationError('Substitua os participantes que recusaram a banca antes de finalizá-la.')
    avaliacoes = list(Avaliacao.objects.filter(
        participacao_id__in=[p.pk for p in participacoes],
    ))
    if len(avaliacoes) != len(participacoes):
        raise ValidationError('Todas as avaliações dos titulares precisam ser registradas antes do fechamento.')
    return avaliacoes


def calcular_resultado_banca(banca):
    """Recalcula a média a partir das avaliações persistidas; não altera dados."""
    avaliacoes = _avaliacoes_titulares(banca)
    media = (sum((a.nota for a in avaliacoes), Decimal('0.00')) / Decimal(len(avaliacoes))).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP,
    )
    if media < MEDIA_MINIMA_APROVACAO:
        resultado = 'REPROVADA'
    elif any(a.recomendacao == 'APROVADA_COM_RESSALVAS' for a in avaliacoes):
        resultado = 'APROVADA_COM_RESSALVAS'
    else:
        # Uma recomendação individual de reprovação não funciona como veto.
        resultado = 'APROVADA'
    return media, resultado


@transaction.atomic
def registrar_defesa_realizada(usuario, banca_id):
    """Orientador, coordenador do curso ou administrador registra a defesa."""
    banca = get_object_or_404(
        Banca.objects.select_for_update(of=('self',)).select_related('monografia'),
        pk=banca_id,
    )
    monografia = Monografia.objects.select_for_update(of=('self',)).get(pk=banca.monografia_id)
    if not pode_convidar_para_banca(usuario, monografia):
        raise PermissionDenied('Você não pode registrar a defesa desta banca.')
    if banca.status != 'AGENDADA' or monografia.status_fluxo not in ('APROVADA_ORIENTADOR', 'BANCA_AGENDADA'):
        raise OperacaoNaoPermitida('A banca deve estar agendada e a monografia aprovada pelo orientador.')
    if banca.fim > timezone.now():
        raise ValidationError('A defesa não pode ser marcada como realizada antes do horário de término.')
    if not ParticipacaoBanca.objects.filter(banca=banca, papel__in=PAPEIS_AVALIADORES).exists():
        raise ValidationError('Adicione pelo menos um avaliador titular antes de registrar a defesa.')
    banca.status = 'REALIZADA'
    banca.save(update_fields=['status'])
    monografia.status_fluxo = 'DEFESA_REALIZADA'
    monografia.save(update_fields=['status_fluxo'])
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'Banca:{banca.pk}', acao='DEFESA_REALIZADA',
        detalhes={'banca_id': banca.pk, 'monografia_id': monografia.pk},
    )
    return banca


@transaction.atomic
def registrar_avaliacao_propria(usuario, participacao_id, dados):
    """Somente o professor titular desta participação registra sua avaliação."""
    # Lock na banca primeiro: serializa registro e fechamento das avaliações.
    referencia = get_object_or_404(ParticipacaoBanca, pk=participacao_id)
    banca = Banca.objects.select_for_update(of=('self',)).get(pk=referencia.banca_id)
    participacao = ParticipacaoBanca.objects.select_for_update(of=('self',)).select_related(
        'professor',
    ).get(pk=participacao_id, banca=banca)
    if (
        not usuario.is_authenticated or not usuario.is_active or
        participacao.professor_id is None or participacao.professor.usuario_id != usuario.pk
    ):
        raise PermissionDenied('Somente o professor participante pode registrar a própria avaliação.')
    if participacao.papel not in PAPEIS_AVALIADORES or participacao.convite_status == 'RECUSADO':
        raise PermissionDenied('Esta participação não está habilitada para avaliar.')
    if banca.status != 'REALIZADA' or banca.monografia.status_fluxo != 'DEFESA_REALIZADA':
        raise OperacaoNaoPermitida('A avaliação só pode ser registrada após a defesa e antes do fechamento.')
    avaliacao = Avaliacao.objects.filter(participacao=participacao).first()
    criado = avaliacao is None
    if criado:
        avaliacao = Avaliacao(participacao=participacao)
    elif avaliacao.finalizada_em is not None:
        raise OperacaoNaoPermitida('Esta avaliação já foi finalizada.')
    for campo in ('nota', 'parecer', 'recomendacao'):
        setattr(avaliacao, campo, dados.get(campo))
    avaliacao.full_clean()
    avaliacao.save()
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'Avaliacao:{avaliacao.pk}',
        acao='AVALIACAO_CRIADA' if criado else 'AVALIACAO_ATUALIZADA',
        detalhes={'avaliacao_id': avaliacao.pk, 'banca_id': banca.pk, 'participacao_id': participacao.pk},
    )
    return avaliacao, criado


@transaction.atomic
def finalizar_resultado_banca(usuario, banca_id):
    """Somente fecha depois de receber todas as avaliações obrigatórias."""
    banca = get_object_or_404(
        Banca.objects.select_for_update(of=('self',)).select_related('monografia'),
        pk=banca_id,
    )
    monografia = Monografia.objects.select_for_update(of=('self',)).get(pk=banca.monografia_id)
    if not pode_convidar_para_banca(usuario, monografia):
        raise PermissionDenied('Você não pode finalizar o resultado desta banca.')
    if banca.status != 'REALIZADA' or monografia.status_fluxo != 'DEFESA_REALIZADA':
        raise OperacaoNaoPermitida('A defesa precisa estar realizada e o resultado ainda não finalizado.')
    media, resultado = calcular_resultado_banca(banca)
    momento = timezone.now()
    ids = ParticipacaoBanca.objects.filter(
        banca=banca, papel__in=PAPEIS_AVALIADORES,
    ).values_list('pk', flat=True)
    Avaliacao.objects.filter(participacao_id__in=ids, finalizada_em__isnull=True).update(finalizada_em=momento)
    monografia.status_fluxo = resultado
    monografia.save(update_fields=['status_fluxo'])
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'Banca:{banca.pk}', acao='RESULTADO_BANCA_FINALIZADO',
        detalhes={'banca_id': banca.pk, 'monografia_id': monografia.pk,
                  'media': str(media), 'resultado': resultado},
    )
    return media, resultado
