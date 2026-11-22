"""RabbitMQ com publisher confirms, entrega persistente e ACK após commit."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pika
from django.conf import settings
from django.db import close_old_connections, connections, transaction
from django.utils import timezone

from .indexacao import MensagemInvalida, dados_evento, indexar_evento, registrar_falha
from .models import EventoIndexacao


def conectar():
    if not settings.RABBITMQ_URL:
        raise ValueError('Configure RABBITMQ_URL no ambiente do worker.')
    parametros = pika.URLParameters(settings.RABBITMQ_URL)
    parametros.socket_timeout = 5
    parametros.stack_timeout = 10
    parametros.blocked_connection_timeout = 10
    parametros.heartbeat = 60
    parametros.connection_attempts = 1
    return pika.BlockingConnection(parametros)


def preparar_canal(conexao):
    canal = conexao.channel()
    fila = settings.REPOSITORIO_FILA
    # Namespace próprio: não altera a topologia ou as filas do microserviço B09.
    canal.exchange_declare(exchange=fila+'.eventos', exchange_type='direct', durable=True)
    canal.exchange_declare(exchange=fila+'.falhas', exchange_type='direct', durable=True)
    canal.queue_declare(queue=fila+'.dlq', durable=True)
    canal.queue_bind(queue=fila+'.dlq', exchange=fila+'.falhas', routing_key='falha')
    canal.queue_declare(queue=fila, durable=True, arguments={
        'x-dead-letter-exchange': fila+'.falhas', 'x-dead-letter-routing-key': 'falha',
    })
    canal.queue_bind(queue=fila, exchange=fila+'.eventos', routing_key='monografia.publicada')
    canal.basic_qos(prefetch_count=1)
    canal.confirm_delivery()
    return canal


def despachar_pendentes(canal, limite=20):
    enviados = 0
    for _ in range(limite):
        with transaction.atomic():
            evento = EventoIndexacao.objects.select_for_update(skip_locked=True, of=('self',)).select_related('publicacao').filter(
                processado_em__isnull=True, falhas__lt=settings.REPOSITORIO_MAX_TENTATIVAS,
                proxima_tentativa__lte=timezone.now(),
            ).first()
            if not evento:
                break
            evento.tentativas_envio += 1
            try:
                canal.basic_publish(exchange=settings.REPOSITORIO_FILA+'.eventos', routing_key='monografia.publicada',
                    body=json.dumps(dados_evento(evento)).encode(), mandatory=True,
                    properties=pika.BasicProperties(content_type='application/json', delivery_mode=2, message_id=str(evento.pk)))
            except Exception as exc:
                evento.ultimo_erro = type(exc).__name__[:255]
                evento.proxima_tentativa = timezone.now()+timedelta(seconds=30)
                evento.save(update_fields=['tentativas_envio', 'ultimo_erro', 'proxima_tentativa'])
                # A outbox permanece pendente mesmo se o broker recebeu antes da falha.
                break
            evento.enviado_em = timezone.now()
            evento.proxima_tentativa = timezone.now()+timedelta(minutes=5)
            evento.save(update_fields=['tentativas_envio', 'enviado_em', 'proxima_tentativa'])
            enviados += 1
    return enviados


def _processar(dados):
    close_old_connections()
    try:
        return indexar_evento(dados)
    finally:
        connections.close_all()


def consumir_disponiveis(conexao, canal, limite=20):
    processados = 0
    with ThreadPoolExecutor(max_workers=1) as executor:
        for _ in range(limite):
            metodo, _, corpo = canal.basic_get(queue=settings.REPOSITORIO_FILA, auto_ack=False)
            if metodo is None:
                break
            dados = {}
            try:
                if len(corpo) > 16384:
                    raise MensagemInvalida('Mensagem excessiva.')
                dados = json.loads(corpo)
                if not isinstance(dados, dict):
                    raise MensagemInvalida('Mensagem deve ser um objeto JSON.')
                tarefa = executor.submit(_processar, dados)
                # Pika permanece nesta thread; a extração não interrompe heartbeats.
                while not tarefa.done():
                    conexao.process_data_events(time_limit=0.2)
                tarefa.result()
            except Exception as exc:
                registrar_falha(dados, exc)
                canal.basic_reject(delivery_tag=metodo.delivery_tag, requeue=False)
            else:
                canal.basic_ack(delivery_tag=metodo.delivery_tag)
                processados += 1
    return processados
