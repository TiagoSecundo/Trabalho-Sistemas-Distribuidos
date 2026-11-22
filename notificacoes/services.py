from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils import timezone

from .models import AvisoBanca, EntregaAviso


class MensagemInvalida(ValueError):
    pass


@transaction.atomic
def registrar_agendamento(banca):
    """Somente persiste dados; não abre conexão SMTP ou AMQP na requisição."""
    if banca.status != 'AGENDADA':
        raise ValueError('A banca ainda não está agendada.')
    participantes = banca.participacoes.select_related('professor', 'membro_externo')
    destinatarios = {banca.monografia.aluno.email.strip().lower()}
    for p in participantes:
        pessoa = p.professor if p.professor_id else p.membro_externo
        destinatarios.add(pessoa.email.strip().lower())
    inicio = timezone.localtime(banca.inicio).strftime('%d/%m/%Y às %H:%M (%Z)')
    fim = timezone.localtime(banca.fim).strftime('%d/%m/%Y às %H:%M (%Z)')
    # Snapshot: alteração posterior do cadastro não troca os destinatários.
    aviso, criado = AvisoBanca.objects.get_or_create(banca=banca, defaults={
        'assunto': 'Banca agendada — ' + ' '.join(banca.monografia.titulo.split()),
        'corpo': (f'A defesa foi agendada.\n\nTrabalho: {banca.monografia.titulo}\n'
                  f'Aluno: {banca.monografia.aluno.nome}\nInício: {inicio}\nTérmino: {fim}\n'
                  f'Modalidade: {banca.get_modalidade_display()}\nLocal: {banca.local or "—"}\n'
                  f'Link: {banca.link or "—"}\n\nConsulte seu painel acadêmico para acompanhar a banca.'),
    })
    if criado:
        EntregaAviso.objects.bulk_create([EntregaAviso(aviso=aviso, destinatario=e) for e in sorted(destinatarios)])
    return aviso


def dados_evento(aviso):
    return {'versao': 1, 'evento_id': str(aviso.pk), 'banca_id': aviso.banca_id}


def obter_evento(dados):
    if not isinstance(dados, dict):
        raise MensagemInvalida('Payload inválido.')
    try:
        evento_id = UUID(dados.get('evento_id', ''))
    except (ValueError, TypeError, AttributeError):
        raise MensagemInvalida('Identificador inválido.') from None
    aviso = AvisoBanca.objects.filter(pk=evento_id).first()
    if not aviso or dados != dados_evento(aviso):
        raise MensagemInvalida('Mensagem não corresponde à outbox.')
    return aviso


def enviar_evento(dados):
    aviso = obter_evento(dados)
    if aviso.processado_em:
        return False
    # Commit por destinatário: um erro no terceiro não reenvia aos dois primeiros.
    for pk in aviso.entregas.order_by('pk').values_list('pk', flat=True):
        with transaction.atomic():
            entrega = EntregaAviso.objects.select_for_update().get(pk=pk)
            if entrega.enviado_em:
                continue
            mensagem = EmailMessage(aviso.assunto, aviso.corpo, settings.DEFAULT_FROM_EMAIL,
                [entrega.destinatario], headers={'Message-ID': f'<banca-{aviso.pk}-{pk}@allteam.test>'})
            if mensagem.send(fail_silently=False) != 1:
                raise RuntimeError('SMTP não confirmou envio.')
            entrega.enviado_em = timezone.now()
            entrega.save(update_fields=['enviado_em'])
    with transaction.atomic():
        aviso = AvisoBanca.objects.select_for_update().get(pk=aviso.pk)
        if not aviso.entregas.filter(enviado_em__isnull=True).exists():
            aviso.processado_em = timezone.now()
            aviso.ultimo_erro = ''
            aviso.save(update_fields=['processado_em', 'ultimo_erro'])
    return True


def registrar_falha(dados, erro):
    try:
        aviso = obter_evento(dados)
    except MensagemInvalida:
        return
    with transaction.atomic():
        aviso = AvisoBanca.objects.select_for_update().get(pk=aviso.pk)
        if aviso.processado_em:
            return
        aviso.falhas += 1
        aviso.ultimo_erro = type(erro).__name__[:255]
        aviso.proxima_tentativa = timezone.now() + timedelta(seconds=30 * 2 ** min(aviso.falhas - 1, 6))
        aviso.save(update_fields=['falhas', 'ultimo_erro', 'proxima_tentativa'])
