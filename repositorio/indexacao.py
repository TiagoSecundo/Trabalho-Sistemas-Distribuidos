"""Extração somente no worker; índice e confirmação do evento são atômicos."""
from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.contrib.postgres.search import SearchVector
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader

from usuarios.publicacao import abrir_documento_verificado
from .consultas import publicacoes_publicas
from .models import EventoIndexacao, IndicePublicacao


class MensagemInvalida(Exception):
    pass


def dados_evento(evento):
    p = evento.publicacao
    return {'evento_id': str(evento.pk), 'tipo': 'monografia.publicada', 'versao': 1,
            'origem': 'principal', 'publicacao_id': p.pk, 'monografia_id': p.monografia_id,
            'documento_id': p.documento_final_id, 'sha256': evento.sha256,
            'ocorrido_em': evento.criado_em.isoformat()}


def identificar_evento(dados):
    try:
        return UUID(dados['evento_id'])
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise MensagemInvalida('Identificador de evento inválido.') from exc


@transaction.atomic
def indexar_evento(dados):
    evento_id = identificar_evento(dados)
    evento = EventoIndexacao.objects.select_for_update(of=('self',)).select_related('publicacao').filter(pk=evento_id).first()
    if not evento or dados != dados_evento(evento):
        raise MensagemInvalida('Evento não corresponde à outbox local.')
    publicacao = publicacoes_publicas().filter(pk=evento.publicacao_id).first()
    if not publicacao or publicacao.sha256 != evento.sha256:
        raise MensagemInvalida('Publicação ou versão não está disponível ao público.')
    if evento.processado_em and IndicePublicacao.objects.filter(publicacao=publicacao, sha256=evento.sha256).exists():
        return False
    partes, tamanho = [], 0
    with abrir_documento_verificado(publicacao.documento_final) as arquivo:
        for pagina in PdfReader(arquivo, strict=True).pages:
            texto = (pagina.extract_text() or '').replace('\x00', '')
            tamanho += len(texto)
            if tamanho > settings.REPOSITORIO_MAX_TEXTO:
                raise ValueError('O texto excede o limite configurado para indexação.')
            partes.append(texto)
    indice, _ = IndicePublicacao.objects.update_or_create(publicacao=publicacao, defaults={
        'texto': '\n'.join(partes), 'sha256': evento.sha256, 'indexado_em': timezone.now(),
    })
    IndicePublicacao.objects.filter(pk=indice.pk).update(vetor=SearchVector('texto', config='portuguese'))
    evento.processado_em = timezone.now()
    evento.ultimo_erro = ''
    evento.save(update_fields=['processado_em', 'ultimo_erro'])
    return True


@transaction.atomic
def registrar_falha(dados, exc):
    """Guarda apenas a classe de falha; mensagens externas podem conter segredos."""
    try:
        pk = identificar_evento(dados)
    except MensagemInvalida:
        return
    evento = EventoIndexacao.objects.select_for_update().filter(pk=pk, processado_em__isnull=True).first()
    if evento and dados == dados_evento(evento):
        evento.falhas += 1
        evento.ultimo_erro = type(exc).__name__[:255]
        evento.enviado_em = None
        evento.proxima_tentativa = timezone.now()+timedelta(seconds=min(30 * 2 ** min(evento.falhas-1, 6), 1800))
        evento.save(update_fields=['falhas', 'ultimo_erro', 'enviado_em', 'proxima_tentativa'])
