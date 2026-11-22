"""Testes opt-in com RabbitMQ real e filas exclusivas descartadas ao terminar."""
import json
import os
from datetime import timedelta
from unittest import skipUnless
from uuid import uuid4

import pika
from django.conf import settings
from django.test import TransactionTestCase, override_settings, tag
from django.urls import reverse
from django.utils import timezone

from .indexacao import dados_evento
from .mensageria import conectar, consumir_disponiveis, despachar_pendentes, preparar_canal
from .models import EventoIndexacao, IndicePublicacao
from .test_helpers import CenarioRepositorio


@tag('integration')
@skipUnless(os.environ.get('RUN_B13_INTEGRATION') == '1', 'Requer RabbitMQ real em RABBITMQ_URL.')
class RabbitMQRepositorioTests(CenarioRepositorio, TransactionTestCase):
    def setUp(self):
        self.preparar_cenario(); self.arquivos_temporarios()
        self.fila='allteam.repositorio.teste.'+uuid4().hex
        config=override_settings(REPOSITORIO_FILA=self.fila)
        config.enable(); self.addCleanup(config.disable)
        self.conexao=conectar(); self.addCleanup(self.conexao.close)
        self.canal=preparar_canal(self.conexao)
        self.addCleanup(self.limpar)
        self.p=self.publicar_trabalho()

    def limpar(self):
        self.canal.queue_delete(queue=self.fila)
        self.canal.queue_delete(queue=self.fila+'.dlq')
        self.canal.exchange_delete(exchange=self.fila+'.eventos')
        self.canal.exchange_delete(exchange=self.fila+'.falhas')

    def enviar(self, body):
        self.canal.basic_publish(exchange=self.fila+'.eventos',routing_key='monografia.publicada',body=body,
            properties=pika.BasicProperties(delivery_mode=2),mandatory=True)

    def test_publicacao_fila_extracao_busca_e_redelivery_reais(self):
        self.assertFalse(IndicePublicacao.objects.exists())
        self.assertEqual(despachar_pendentes(self.canal),1)
        self.assertEqual(consumir_disponiveis(self.conexao,self.canal),1)
        self.assertEqual(self.client.get(reverse('repositorio-api:monografias'),{'busca':'hiperconvergencia'}).json()['count'],1)
        self.enviar(json.dumps(dados_evento(self.p.evento_indexacao)).encode())
        self.assertEqual(consumir_disponiveis(self.conexao,self.canal),1)
        self.assertEqual(IndicePublicacao.objects.count(),1)
        self.assertIsNotNone(EventoIndexacao.objects.get().processado_em)
        self.assertEqual(self.canal.queue_declare(queue=self.fila,passive=True).method.message_count,0)

    def test_mensagens_invalidas_e_documento_corrompido_vao_para_dlq(self):
        self.enviar(b'{json-invalido')
        self.enviar(json.dumps({**dados_evento(self.p.evento_indexacao),'documento_id':self.p.termo_id}).encode())
        self.assertEqual(consumir_disponiveis(self.conexao,self.canal),0)
        self.assertFalse(IndicePublicacao.objects.exists())
        for _ in range(2):
            metodo,_,_=self.canal.basic_get(queue=self.fila+'.dlq',auto_ack=True)
            self.assertIsNotNone(metodo)
        with self.p.documento_final.arquivo.storage.open(self.p.documento_final.arquivo.name,'wb') as stream: stream.write(b'invalido')
        self.assertEqual(despachar_pendentes(self.canal),1)
        self.assertEqual(consumir_disponiveis(self.conexao,self.canal),0)
        evento=EventoIndexacao.objects.get(); self.assertEqual(evento.falhas,1)
        self.assertIsNone(evento.processado_em)
        self.assertIsNotNone(self.canal.basic_get(queue=self.fila+'.dlq',auto_ack=True)[0])

    def test_canal_indisponivel_preserva_outbox_e_reconexao_processa(self):
        canal_fechado=self.conexao.channel(); canal_fechado.close()
        self.assertEqual(despachar_pendentes(canal_fechado),0)
        evento=EventoIndexacao.objects.get(); self.assertIsNone(evento.enviado_em)
        EventoIndexacao.objects.update(proxima_tentativa=timezone.now()-timedelta(seconds=1))
        self.assertEqual(despachar_pendentes(self.canal),1)
        self.assertEqual(consumir_disponiveis(self.conexao,self.canal),1)
        self.assertEqual(IndicePublicacao.objects.get().sha256,self.p.sha256)
