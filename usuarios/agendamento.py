"""B10: proposta, disponibilidade e confirmações de banca.

Regras compartilhadas por interface e API, com validação na mesma transação.
"""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from Curso_Django.services import OperacaoNaoPermitida
from equipe.models import Professor
from monografias.models import Banca, HistoricoAcao, MembroExterno, Monografia, ParticipacaoBanca
from monografias.services import BancaService
from .roles import pode_convidar_para_banca


TITULARES = ('PRESIDENTE', 'AVALIADOR')


def _auditar(usuario, objeto, acao, **detalhes):
    HistoricoAcao.objects.create(
        ator=usuario, objeto=objeto, acao=acao, detalhes=detalhes,
    )


def _bloquear_membros(banca):
    """Serializa confirmações de propostas concorrentes com membros compartilhados (PostgreSQL)."""
    participantes = ParticipacaoBanca.objects.filter(banca=banca)
    professores = list(participantes.filter(professor__isnull=False).values_list('professor_id', flat=True))
    externos = list(participantes.filter(membro_externo__isnull=False).values_list('membro_externo_id', flat=True))
    list(Professor.objects.select_for_update().filter(pk__in=professores).order_by('pk'))
    list(MembroExterno.objects.select_for_update().filter(pk__in=externos).order_by('pk'))


def _verificar_conflitos(banca):
    """Confere conflitos com agendamentos ou propostas já confirmadas."""
    for participante in ParticipacaoBanca.objects.filter(banca=banca):
        _verificar_conflitos_para_pessoa(banca, participante)


def _agendar_se_confirmado(usuario, banca):
    """Banca só se torna AGENDADA quando todos confirmaram e não há conflitos."""
    if banca.status != 'PENDENTE':
        return False
    monografia = Monografia.objects.select_for_update(of=('self',)).get(pk=banca.monografia_id)
    if monografia.status_fluxo != 'APROVADA_ORIENTADOR':
        raise OperacaoNaoPermitida('A monografia deixou de estar aprovada pelo orientador.')
    participantes = list(ParticipacaoBanca.objects.filter(banca=banca))
    if not any(p.papel in TITULARES for p in participantes):
        return False
    if not all(p.convite_status == 'CONFIRMADO' for p in participantes):
        return False
    if banca.inicio <= timezone.now():
        raise ValidationError('O horário da defesa deve estar no futuro.')
    _verificar_conflitos(banca)
    banca.status = 'AGENDADA'
    banca.save(update_fields=['status'])
    monografia.status_fluxo = 'BANCA_AGENDADA'
    monografia.save(update_fields=['status_fluxo'])
    _auditar(usuario, f'Banca:{banca.pk}', 'BANCA_AGENDADA', banca_id=banca.pk, monografia_id=monografia.pk)
    from notificacoes.services import registrar_agendamento
    registrar_agendamento(banca)
    return True


@transaction.atomic
def propor_banca(usuario, monografia_id, dados):
    monografia = get_object_or_404(Monografia, pk=monografia_id)
    if not pode_convidar_para_banca(usuario, monografia):
        raise PermissionDenied('Apenas orientador, coordenador do curso ou administrador podem propor a banca.')
    banca = BancaService.criar(Banca, {**dados, 'monografia': monografia})
    _auditar(usuario, f'Banca:{banca.pk}', 'PROPOSTA_BANCA_CRIADA',
             banca_id=banca.pk, monografia_id=monografia.pk)
    return banca


@transaction.atomic
def adicionar_participante(usuario, banca_id, dados):
    banca = get_object_or_404(Banca.objects.select_for_update(of=('self',)).select_related('monografia'), pk=banca_id)
    if not pode_convidar_para_banca(usuario, banca.monografia):
        raise PermissionDenied('Você não pode configurar esta banca.')
    if banca.status != 'PENDENTE':
        raise OperacaoNaoPermitida('Só é possível incluir participantes em uma proposta pendente.')
    participacao = ParticipacaoBanca(banca=banca, **dados)
    participacao.full_clean()
    participacao.save()
    _auditar(usuario, f'ParticipacaoBanca:{participacao.pk}', 'PARTICIPANTE_INCLUIDO',
             banca_id=banca.pk, participacao_id=participacao.pk)
    return participacao


@transaction.atomic
def retirar_participante(usuario, participacao_id):
    referencia = get_object_or_404(ParticipacaoBanca, pk=participacao_id)
    banca = Banca.objects.select_for_update(of=('self',)).select_related('monografia').get(pk=referencia.banca_id)
    if not pode_convidar_para_banca(usuario, banca.monografia):
        raise PermissionDenied('Você não pode alterar esta banca.')
    if banca.status != 'PENDENTE':
        raise OperacaoNaoPermitida('Não é possível retirar participantes de uma banca agendada.')
    participacao = ParticipacaoBanca.objects.select_for_update(of=('self',)).get(pk=participacao_id, banca=banca)
    if hasattr(participacao, 'avaliacao'):
        raise OperacaoNaoPermitida('Uma participação avaliada não pode ser retirada.')
    participacao.delete()
    _bloquear_membros(banca)
    _agendar_se_confirmado(usuario, banca)
    _auditar(usuario, f'ParticipacaoBanca:{participacao_id}', 'PARTICIPANTE_RETIRADO',
             banca_id=banca.pk, participacao_id=participacao_id)


@transaction.atomic
def responder_convite_interno(usuario, participacao_id, aceitar):
    referencia = get_object_or_404(ParticipacaoBanca, pk=participacao_id)
    banca = Banca.objects.select_for_update(of=('self',)).get(pk=referencia.banca_id)
    participacao = ParticipacaoBanca.objects.select_for_update(of=('self',)).select_related('professor').get(pk=participacao_id)
    if not usuario.is_authenticated or not usuario.is_active or not participacao.professor_id or participacao.professor.usuario_id != usuario.pk:
        raise PermissionDenied('Somente o professor convidado pode responder.')
    if banca.status != 'PENDENTE' or participacao.convite_status != 'CONVIDADO':
        raise OperacaoNaoPermitida('A participação não está aguardando resposta.')
    _bloquear_membros(banca)
    if aceitar:
        _verificar_conflitos_para_pessoa(banca, participacao)
    participacao.convite_status = 'CONFIRMADO' if aceitar else 'RECUSADO'
    participacao.confirmado_em = timezone.now() if aceitar else None
    participacao.save(update_fields=['convite_status', 'confirmado_em'])
    _auditar(usuario, f'ParticipacaoBanca:{participacao.pk}',
             'CONVITE_INTERNO_CONFIRMADO' if aceitar else 'CONVITE_INTERNO_RECUSADO',
             banca_id=banca.pk, participacao_id=participacao.pk)
    return _agendar_se_confirmado(usuario, banca) if aceitar else False


def _verificar_conflitos_para_pessoa(banca, participante):
    outras = ParticipacaoBanca.objects.filter(
        banca__inicio__lt=banca.fim, banca__fim__gt=banca.inicio,
        banca__status__in=['PENDENTE', 'AGENDADA'],
    ).exclude(banca=banca).filter(
        **({'professor_id': participante.professor_id} if participante.professor_id
           else {'membro_externo_id': participante.membro_externo_id})
    ).exclude(banca__status='PENDENTE', convite_status__in=['CONVIDADO', 'RECUSADO'])
    if outras.exists():
        raise ValidationError('Conflito de horário: este participante já está comprometido com outra banca.')


@transaction.atomic
def responder_convite_externo(participacao_id, token, aceitar, validar_token):
    referencia = get_object_or_404(ParticipacaoBanca, pk=participacao_id)
    banca = Banca.objects.select_for_update(of=('self',)).get(pk=referencia.banca_id)
    participacao = ParticipacaoBanca.objects.select_for_update(of=('self',)).get(pk=participacao_id)
    if (
        participacao.membro_externo_id is None or
        participacao.convite_status != 'CONVIDADO' or
        banca.status not in ('PENDENTE', 'AGENDADA') or
        not validar_token(participacao, token)
    ):
        raise PermissionDenied('Convite inválido, expirado ou já respondido.')
    if not aceitar and banca.status != 'PENDENTE':
        raise OperacaoNaoPermitida('Não é possível recusar um convite depois do agendamento.')
    _bloquear_membros(banca)
    if aceitar:
        _verificar_conflitos_para_pessoa(banca, participacao)
    participacao.convite_status = 'CONFIRMADO' if aceitar else 'RECUSADO'
    participacao.confirmado_em = timezone.now() if aceitar else None
    participacao.token_hash = ''
    participacao.expira_em = None
    participacao.save(update_fields=['convite_status', 'confirmado_em', 'token_hash', 'expira_em'])
    _auditar(None, f'ParticipacaoBanca:{participacao.pk}',
             'CONVITE_EXTERNO_CONFIRMADO' if aceitar else 'CONVITE_EXTERNO_RECUSADO',
             banca_id=banca.pk, participacao_id=participacao.pk)
    return _agendar_se_confirmado(None, banca) if aceitar else False


@transaction.atomic
def cancelar_proposta(usuario, banca_id):
    banca = get_object_or_404(Banca.objects.select_for_update(of=('self',)).select_related('monografia'), pk=banca_id)
    if not pode_convidar_para_banca(usuario, banca.monografia):
        raise PermissionDenied('Você não pode cancelar esta proposta.')
    if banca.status != 'PENDENTE':
        raise OperacaoNaoPermitida('Somente propostas pendentes podem ser canceladas.')
    banca.status = 'CANCELADA'
    banca.save(update_fields=['status'])
    # Códigos antigos deixam de autorizar confirmação porque a banca foi cancelada.
    _auditar(usuario, f'Banca:{banca.pk}', 'PROPOSTA_BANCA_CANCELADA', banca_id=banca.pk)
    return banca
