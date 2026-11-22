from datetime import timedelta
from unittest.mock import Mock, patch

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from usuarios.agendamento import adicionar_participante, propor_banca, responder_convite_interno, responder_convite_externo
from usuarios.convites import emitir_token, validar_token
from usuarios import test_agendamento
from .models import AvisoBanca
from .services import dados_evento, enviar_evento, MensagemInvalida, registrar_agendamento, registrar_falha
from .mensageria import despachar_pendentes


class CenarioAvisos:
    def preparar(self):
        test_agendamento.FluxoAgendamentoB10Tests.setUpTestData.__func__(type(self))
        inicio = timezone.now() + timedelta(days=2)
        self.banca = propor_banca(self.orientador_user, self.monografia.pk, {
            'inicio': inicio, 'fim': inicio + timedelta(hours=1), 'modalidade': 'REMOTA',
            'link': 'https://reuniao.example.test/defesa', 'local': '',
        })
        self.interno = adicionar_participante(self.orientador_user, self.banca.pk,
            {'professor': self.orientador, 'papel': 'PRESIDENTE'})
        self.part_externa = adicionar_participante(self.orientador_user, self.banca.pk,
            {'membro_externo': self.externo, 'papel': 'AVALIADOR'})

    def agendar(self):
        responder_convite_interno(self.orientador_user, self.interno.pk, True)
        token = emitir_token(self.part_externa)
        responder_convite_externo(self.part_externa.pk, token, True, validar_token)
        self.banca.refresh_from_db()
        return AvisoBanca.objects.get(banca=self.banca)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AvisosTests(CenarioAvisos, TestCase):
    def setUp(self):
        self.preparar()

    def test_apenas_confirmacao_final_cria_outbox_sem_smtp_ou_broker(self):
        self.assertFalse(AvisoBanca.objects.exists())
        with (patch('notificacoes.services.EmailMessage.send', side_effect=AssertionError('SMTP no HTTP')),
              patch('notificacoes.mensageria.conectar', side_effect=AssertionError('Broker no HTTP'))):
            aviso = self.agendar()
        self.assertEqual(self.banca.status, 'AGENDADA')
        self.assertIsNone(aviso.processado_em)
        self.assertEqual(aviso.entregas.count(), 3)
        self.assertEqual(len(mail.outbox), 0)

    def test_todos_recebem_dados_e_repeticao_nao_reenvia(self):
        aviso = self.agendar()
        self.assertTrue(enviar_evento(dados_evento(aviso)))
        self.assertFalse(enviar_evento(dados_evento(aviso)))
        self.assertEqual({m.to[0] for m in mail.outbox}, {self.aluno.email, self.orientador.email, self.externo.email})
        self.assertEqual(len(mail.outbox), 3)
        for m in mail.outbox:
            self.assertIn(self.monografia.titulo, m.body)
            self.assertIn(self.banca.link, m.body)
            self.assertIn('Início:', m.body)
            self.assertIn('Modalidade:', m.body)
            self.assertEqual(len(m.to), 1)

    def test_falha_parcial_preserva_entregas_e_retoma_restantes(self):
        aviso = self.agendar()
        with patch('notificacoes.services.EmailMessage.send', side_effect=[1, OSError('indisponível')]):
            with self.assertRaises(OSError) as erro:
                enviar_evento(dados_evento(aviso))
        registrar_falha(dados_evento(aviso), erro.exception)
        self.assertEqual(aviso.entregas.filter(enviado_em__isnull=False).count(), 1)
        enviar_evento(dados_evento(aviso))
        self.assertEqual(len(mail.outbox), 2)
        aviso.refresh_from_db()
        self.assertEqual(aviso.falhas, 1)
        self.assertIsNotNone(aviso.processado_em)

    def test_broker_indisponivel_preserva_agendamento_e_outbox(self):
        aviso = self.agendar()
        canal = Mock()
        canal.basic_publish.side_effect = OSError('offline')
        self.assertEqual(despachar_pendentes(canal), 0)
        aviso.refresh_from_db()
        self.assertIsNone(aviso.enviado_em)
        self.assertEqual(aviso.ultimo_erro, 'OSError')
        self.assertEqual(self.banca.status, 'AGENDADA')

    def test_payload_adulterado_e_proposta_pendente_nao_enviam(self):
        with self.assertRaises(ValueError):
            registrar_agendamento(self.banca)
        aviso = self.agendar()
        with self.assertRaises(MensagemInvalida):
            enviar_evento({**dados_evento(aviso), 'banca_id': 999})
        self.assertEqual(len(mail.outbox), 0)

    def test_destinatarios_duplicados_e_suplentes(self):
        suplente = adicionar_participante(self.orientador_user, self.banca.pk,
            {'professor': self.avaliador, 'papel': 'SUPLENTE'})
        responder_convite_interno(self.avaliador_user, suplente.pk, True)
        aviso = self.agendar()
        registrar_agendamento(self.banca)
        self.assertEqual(AvisoBanca.objects.count(), 1)
        self.assertEqual(aviso.entregas.count(), 4)
