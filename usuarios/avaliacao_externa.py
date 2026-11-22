"""B11: código temporário e de uso único para avaliação de integrante externo.

O token usado para confirmar o convite no B10 não concede autorização para avaliar.
Todas as alterações fazem lock na banca antes da participação, como o B11 existente.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from Curso_Django.services import OperacaoNaoPermitida
from monografias.models import Avaliacao, Banca, HistoricoAcao, ParticipacaoBanca
from .roles import pode_convidar_para_banca

TITULARES = ('PRESIDENTE', 'AVALIADOR')
VALIDADE_CODIGO = timedelta(days=7)


def _valido(participacao, codigo):
    if not isinstance(codigo, str) or not codigo or len(codigo) > 512:
        return False
    if not participacao.avaliacao_token_hash or not participacao.avaliacao_expira_em:
        return False
    if participacao.avaliacao_expira_em <= timezone.now():
        return False
    recebido = hashlib.sha256(codigo.encode('utf-8')).hexdigest()
    return hmac.compare_digest(participacao.avaliacao_token_hash, recebido)


@transaction.atomic
def emitir_codigo_avaliacao_externa(usuario, participacao_id):
    """Responsável gera um código novo; o anterior é revogado no mesmo ato."""
    referencia = get_object_or_404(ParticipacaoBanca, pk=participacao_id)
    banca = Banca.objects.select_for_update(of=('self',)).select_related('monografia').get(pk=referencia.banca_id)
    participacao = ParticipacaoBanca.objects.select_for_update(of=('self',)).get(pk=participacao_id, banca=banca)
    if not pode_convidar_para_banca(usuario, banca.monografia):
        raise PermissionDenied('Sem permissão para emitir código de avaliação.')
    if participacao.membro_externo_id is None or participacao.papel not in TITULARES:
        raise OperacaoNaoPermitida('Somente avaliadores externos titulares recebem esse código.')
    if participacao.convite_status != 'CONFIRMADO':
        raise OperacaoNaoPermitida('O membro externo precisa confirmar o convite primeiro.')
    if banca.status != 'REALIZADA' or banca.monografia.status_fluxo != 'DEFESA_REALIZADA':
        raise OperacaoNaoPermitida('A defesa precisa estar realizada e o resultado ainda aberto.')
    if Avaliacao.objects.filter(participacao=participacao, finalizada_em__isnull=False).exists():
        raise OperacaoNaoPermitida('Esta avaliação já foi finalizada.')
    codigo = secrets.token_urlsafe(32)
    participacao.avaliacao_token_hash = hashlib.sha256(codigo.encode('utf-8')).hexdigest()
    participacao.avaliacao_expira_em = timezone.now() + VALIDADE_CODIGO
    participacao.save(update_fields=['avaliacao_token_hash', 'avaliacao_expira_em'])
    HistoricoAcao.objects.create(
        ator=usuario, objeto=f'ParticipacaoBanca:{participacao.pk}',
        acao='CODIGO_AVALIACAO_EXTERNA_EMITIDO',
        detalhes={'participacao_id': participacao.pk, 'banca_id': banca.pk},
    )
    return participacao, codigo


@transaction.atomic
def registrar_avaliacao_externa(participacao_id, codigo, dados):
    """Código autoriza só a avaliação do titular referido, uma única vez."""
    referencia = get_object_or_404(ParticipacaoBanca, pk=participacao_id)
    banca = Banca.objects.select_for_update(of=('self',)).select_related('monografia').get(pk=referencia.banca_id)
    participacao = ParticipacaoBanca.objects.select_for_update(of=('self',)).get(pk=participacao_id, banca=banca)
    # Confere o código antes de disponibilizar qualquer informação da banca.
    if (participacao.membro_externo_id is None or
            not _valido(participacao, codigo)):
        raise PermissionDenied('Código de avaliação inválido ou expirado.')
    if participacao.papel not in TITULARES or participacao.convite_status != 'CONFIRMADO':
        raise OperacaoNaoPermitida('Esta participação não está habilitada para avaliar.')
    if banca.status != 'REALIZADA' or banca.monografia.status_fluxo != 'DEFESA_REALIZADA':
        raise OperacaoNaoPermitida('A avaliação só é permitida após a defesa e antes do fechamento.')
    avaliacao = Avaliacao.objects.filter(participacao=participacao).first()
    criada = avaliacao is None
    if criada:
        avaliacao = Avaliacao(participacao=participacao)
    elif avaliacao.finalizada_em is not None:
        raise OperacaoNaoPermitida('Esta avaliação já foi finalizada.')
    for campo in ('nota', 'parecer', 'recomendacao'):
        setattr(avaliacao, campo, dados.get(campo))
    avaliacao.full_clean()
    avaliacao.save()
    # Consumo único: uma correção exige reemissão pelo orientador/coordenador.
    participacao.avaliacao_token_hash = ''
    participacao.avaliacao_expira_em = None
    participacao.save(update_fields=['avaliacao_token_hash', 'avaliacao_expira_em'])
    HistoricoAcao.objects.create(
        ator=None, objeto=f'Avaliacao:{avaliacao.pk}',
        acao='AVALIACAO_EXTERNA_CRIADA' if criada else 'AVALIACAO_EXTERNA_ATUALIZADA',
        detalhes={'avaliacao_id': avaliacao.pk, 'participacao_id': participacao.pk,
                  'membro_externo_id': participacao.membro_externo_id, 'banca_id': banca.pk},
    )
    return avaliacao, criada
