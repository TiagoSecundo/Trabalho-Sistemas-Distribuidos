"""Escritas acadêmicas compartilhadas entre HTML e API."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from equipe.models import Aluno
from monografias.models import HistoricoAcao, Monografia, ParticipacaoBanca
from monografias.services import MonografiaService
from .convites import emitir_token, validar_token
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
    if participacao.banca.status != 'AGENDADA' or participacao.convite_status != 'CONVIDADO':
        raise ValidationError({'convite': 'Esta participação não está aguardando convite.'})
    token = emitir_token(participacao)
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'ParticipacaoBanca:{participacao.pk}',
        acao='CONVITE_EXTERNO_EMITIDO', detalhes={'participacao_id': participacao.pk},
    )
    return participacao, token


@transaction.atomic
def confirmar_convite_externo(pk, token):
    participacao = get_object_or_404(ParticipacaoBanca.objects.select_for_update(), pk=pk)
    if (
        participacao.membro_externo_id is None
        or participacao.convite_status != 'CONVIDADO'
        or participacao.banca.status != 'AGENDADA'
        or not validar_token(participacao, token)
    ):
        raise PermissionDenied('Convite inválido, expirado ou já confirmado.')
    participacao.convite_status = 'CONFIRMADO'
    participacao.confirmado_em = timezone.now()
    participacao.save(update_fields=['convite_status', 'confirmado_em'])
    HistoricoAcao.objects.create(
        ator=None, objeto=f'ParticipacaoBanca:{participacao.pk}',
        acao='CONVITE_EXTERNO_CONFIRMADO', detalhes={'participacao_id': participacao.pk},
    )
