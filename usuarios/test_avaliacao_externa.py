"""B11 complementar: avaliador externo envia nota com código de uso único."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from monografias.models import Avaliacao, Banca, HistoricoAcao, MembroExterno, Monografia, ParticipacaoBanca


class AvaliadorExternoB11Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.orientador_user = User.objects.create_user('orientador-externo', password='Teste123!')
        cls.terceiro_user = User.objects.create_user('outro-externo', password='Teste123!')
        cls.aluno_user = User.objects.create_user('aluno-externo', password='Teste123!')
        cls.orientador = Professor.objects.create(
            usuario=cls.orientador_user, nome='Orientador', email='orientador-externo@example.com',
            departamento='D', area_pesquisa='A',
        )
        cls.curso = Curso.objects.create(nome='Curso avaliação externa', codigo='EXT11')
        cls.aluno = Aluno.objects.create(
            usuario=cls.aluno_user, nome='Aluno', matricula='EXT11-01',
            email='aluno-externo@example.com', curso=cls.curso,
        )
        cls.monografia = Monografia.objects.create(
            titulo='TCC avaliação externa', resumo='Resumo', aluno=cls.aluno,
            curso=cls.curso, orientador=cls.orientador, status_fluxo='BANCA_AGENDADA',
        )
        inicio = timezone.now() - timedelta(days=2)
        cls.banca = Banca.objects.create(
            monografia=cls.monografia, inicio=inicio, fim=inicio + timedelta(hours=1),
            local='Sala', status='AGENDADA',
        )
        cls.presidente = ParticipacaoBanca.objects.create(
            banca=cls.banca, professor=cls.orientador, papel='PRESIDENTE',
            convite_status='CONFIRMADO',
        )
        cls.externo = MembroExterno.objects.create(
            nome='Convidado externo', email='externo-avaliacao@example.com', instituicao='Outra universidade',
        )
        cls.externo2 = MembroExterno.objects.create(
            nome='Segundo externo', email='externo2-avaliacao@example.com', instituicao='Outra universidade',
        )
        cls.participacao = ParticipacaoBanca.objects.create(
            banca=cls.banca, membro_externo=cls.externo, papel='AVALIADOR', convite_status='CONFIRMADO',
        )
        cls.participacao2 = ParticipacaoBanca.objects.create(
            banca=cls.banca, membro_externo=cls.externo2, papel='SUPLENTE', convite_status='CONFIRMADO',
        )

    def realizar(self):
        self.client.force_login(self.orientador_user)
        resposta = self.client.post(reverse('api-realizar-banca', args=[self.banca.pk]))
        self.assertEqual(resposta.status_code, 200, resposta.content)

    def emitir(self, participacao=None):
        self.client.force_login(self.orientador_user)
        pk = participacao.pk if participacao else self.participacao.pk
        return self.client.post(reverse('api-emitir-avaliacao-externa', args=[pk]))

    def avaliar(self, codigo, participacao=None, **extra):
        self.client.logout()
        pk = participacao.pk if participacao else self.participacao.pk
        return self.client.post(reverse('api-avaliacao-externa', args=[pk]), {
            'codigo': codigo, 'nota': '8.00', 'parecer': 'Avaliação fundamentada',
            'recomendacao': 'APROVADA_COM_RESSALVAS', **extra,
        }, content_type='application/json')

    def test_requer_defesa_realizada_para_emitir(self):
        self.assertEqual(self.emitir().status_code, 409)
        self.realizar()
        resposta = self.emitir()
        self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertGreaterEqual(len(resposta.data['codigo']), 40)
        self.participacao.refresh_from_db()
        self.assertNotEqual(self.participacao.avaliacao_token_hash, resposta.data['codigo'])
        self.assertTrue(self.participacao.avaliacao_expira_em > timezone.now())

    def test_requer_permissao_do_responsavel(self):
        self.realizar()
        self.client.force_login(self.terceiro_user)
        self.assertEqual(self.client.post(reverse('api-emitir-avaliacao-externa', args=[self.participacao.pk])).status_code, 403)
        self.client.force_login(self.aluno_user)
        self.assertEqual(self.client.post(reverse('api-emitir-avaliacao-externa', args=[self.participacao.pk])).status_code, 403)
        self.client.logout()
        self.assertIn(self.client.post(reverse('api-emitir-avaliacao-externa', args=[self.participacao.pk])).status_code, (401, 403))

    def test_convite_nao_confirmado_nao_recebe_codigo(self):
        self.realizar()
        self.participacao.convite_status = 'CONVIDADO'
        self.participacao.save(update_fields=['convite_status'])
        self.assertEqual(self.emitir().status_code, 409)

    def test_suplente_e_professor_interno_nao_recebem_codigo_externo(self):
        self.realizar()
        self.assertEqual(self.emitir(self.participacao2).status_code, 409)
        self.assertEqual(self.emitir(self.presidente).status_code, 409)

    def test_avaliacao_anonima_grava_e_invalida_codigo(self):
        self.realizar()
        codigo = self.emitir().data['codigo']
        resposta = self.avaliar(codigo)
        self.assertEqual(resposta.status_code, 201, resposta.content)
        self.assertEqual(Avaliacao.objects.get(participacao=self.participacao).nota, Decimal('8.00'))
        self.participacao.refresh_from_db()
        self.assertEqual(self.participacao.avaliacao_token_hash, '')
        self.assertIsNone(self.participacao.avaliacao_expira_em)
        self.assertEqual(self.avaliar(codigo).status_code, 403)
        self.assertTrue(HistoricoAcao.objects.filter(acao='AVALIACAO_EXTERNA_CRIADA').exists())

    def test_codigo_de_convite_nao_autoriza_avaliacao(self):
        from usuarios.convites import emitir_token
        self.realizar()
        self.participacao.refresh_from_db()
        convite = emitir_token(self.participacao)
        self.assertEqual(self.avaliar(convite).status_code, 403)
        self.assertFalse(Avaliacao.objects.filter(participacao=self.participacao).exists())

    def test_codigo_expirado_e_de_outro_membro_sao_recusados(self):
        self.realizar()
        codigo = self.emitir().data['codigo']
        self.assertEqual(self.avaliar(codigo, participacao=self.participacao2).status_code, 403)
        self.participacao.refresh_from_db()
        self.participacao.avaliacao_expira_em = timezone.now() - timedelta(seconds=1)
        self.participacao.save(update_fields=['avaliacao_expira_em'])
        self.assertEqual(self.avaliar(codigo).status_code, 403)

    def test_reemitir_revoga_codigo_anterior_e_permite_correcao(self):
        self.realizar()
        codigo_antigo = self.emitir().data['codigo']
        codigo_novo = self.emitir().data['codigo']
        self.assertNotEqual(codigo_antigo, codigo_novo)
        self.assertEqual(self.avaliar(codigo_antigo).status_code, 403)
        self.assertEqual(self.avaliar(codigo_novo).status_code, 201)
        codigo_correcao = self.emitir().data['codigo']
        self.assertEqual(self.avaliar(codigo_correcao, nota='7.00').status_code, 200)
        self.assertEqual(Avaliacao.objects.get(participacao=self.participacao).nota, Decimal('7.00'))

    def test_nota_invalida_nao_consumira_codigo(self):
        self.realizar()
        codigo = self.emitir().data['codigo']
        self.assertEqual(self.avaliar(codigo, nota='11.00').status_code, 400)
        self.assertEqual(self.avaliar(codigo, parecer='').status_code, 400)
        self.assertEqual(self.avaliar(codigo, recomendacao='INVALIDA').status_code, 400)
        self.assertEqual(self.avaliar(codigo, nota='6.00').status_code, 201)

    def test_resultado_final_inclui_externo_e_bloqueia_reemissao(self):
        self.realizar()
        codigo = self.emitir().data['codigo']
        self.client.force_login(self.orientador_user)
        interno = self.client.post(reverse('api-minha-avaliacao', args=[self.presidente.pk]), {
            'nota': '6.00', 'parecer': 'Ok', 'recomendacao': 'APROVADA',
        }, content_type='application/json')
        self.assertEqual(interno.status_code, 201, interno.content)
        self.assertEqual(self.client.post(reverse('api-finalizar-banca', args=[self.banca.pk])).status_code, 400)
        self.assertEqual(self.avaliar(codigo).status_code, 201)
        self.client.force_login(self.orientador_user)
        final = self.client.post(reverse('api-finalizar-banca', args=[self.banca.pk]))
        self.assertEqual(final.status_code, 200, final.content)
        self.assertEqual(final.data['media'], '7.00')
        self.assertEqual(final.data['resultado'], 'APROVADA_COM_RESSALVAS')
        self.assertEqual(self.emitir().status_code, 409)
        self.assertIsNotNone(Avaliacao.objects.get(participacao=self.participacao).finalizada_em)

    def test_interface_html_emite_e_recebe_avaliacao_sem_login(self):
        self.realizar()
        self.client.force_login(self.orientador_user)
        tela = self.client.get(reverse('usuarios:trabalho', args=[self.monografia.pk]))
        self.assertContains(tela, 'Gerar acesso de avaliação externa')
        emissao = self.client.post(reverse('usuarios:emitir-avaliacao-externa', args=[self.participacao.pk]))
        self.assertEqual(emissao.status_code, 200, emissao.content)
        codigo = emissao.context['codigo_avaliacao']
        self.assertContains(emissao, 'Código de avaliação')
        self.client.logout()
        pagina = self.client.get(reverse('usuarios:avaliacao-externa', args=[self.participacao.pk]))
        self.assertContains(pagina, 'Registrar avaliação da banca')
        self.assertNotContains(pagina, self.monografia.titulo)
        resposta = self.client.post(reverse('usuarios:avaliacao-externa', args=[self.participacao.pk]), {
            'codigo': codigo, 'nota': '9.00', 'parecer': 'Parecer pela aprovação',
            'recomendacao': 'APROVADA',
        })
        self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertContains(resposta, 'avaliação foi registrada')
        self.assertTrue(Avaliacao.objects.filter(participacao=self.participacao).exists())

    def test_form_html_invalido_e_codigo_incorreto(self):
        self.realizar()
        codigo = self.emitir().data['codigo']
        self.client.logout()
        url = reverse('usuarios:avaliacao-externa', args=[self.participacao.pk])
        incorreto = self.client.post(url, {
            'codigo': 'qualquer', 'nota': '8.00', 'parecer': 'Parecer',
            'recomendacao': 'APROVADA',
        })
        self.assertEqual(incorreto.status_code, 403)
        invalido = self.client.post(url, {
            'codigo': codigo, 'nota': '11.00', 'parecer': 'Parecer',
            'recomendacao': 'APROVADA',
        })
        self.assertEqual(invalido.status_code, 200)  # erros do formulário
        self.assertFalse(Avaliacao.objects.filter(participacao=self.participacao).exists())
        self.assertEqual(self.client.post(url, {
            'codigo': codigo, 'nota': '8.00', 'parecer': 'Parecer', 'recomendacao': 'APROVADA',
        }).status_code, 200)

    def test_integracao_b10_confirmacao_externa_ate_resultado_final(self):
        """Convite B10 é consumido; código B11 independente permite fechar a banca."""
        from usuarios.services import emitir_convite_externo
        novo = Monografia.objects.create(
            titulo='Integração de ponta a ponta', resumo='Resumo', aluno=self.aluno,
            curso=self.curso, orientador=self.orientador, status_fluxo='APROVADA_ORIENTADOR',
        )
        inicio = timezone.now() + timedelta(days=3)
        banca = Banca.objects.create(
            monografia=novo, inicio=inicio, fim=inicio + timedelta(hours=1),
            local='Sala B10', status='PENDENTE',
        )
        interno = ParticipacaoBanca.objects.create(banca=banca, professor=self.orientador, papel='PRESIDENTE')
        externo = ParticipacaoBanca.objects.create(banca=banca, membro_externo=self.externo, papel='AVALIADOR')
        self.client.force_login(self.orientador_user)
        _, convite = emitir_convite_externo(self.orientador_user, externo.pk)
        self.client.logout()
        confirmado = self.client.post(reverse('confirmar-convite-externo', args=[externo.pk]), {
            'token': convite, 'acao': 'confirmar',
        })
        self.assertEqual(confirmado.status_code, 200, confirmado.content)
        externo.refresh_from_db()
        self.assertEqual(externo.token_hash, '')
        self.assertEqual(externo.convite_status, 'CONFIRMADO')
        self.client.force_login(self.orientador_user)
        confirmado_interno = self.client.post(reverse('api-responder-convite-interno', args=[interno.pk]), {
            'acao': 'confirmar',
        }, content_type='application/json')
        self.assertEqual(confirmado_interno.status_code, 200, confirmado_interno.content)
        banca.refresh_from_db()
        self.assertEqual(banca.status, 'AGENDADA')
        novo.refresh_from_db()
        self.assertEqual(novo.status_fluxo, 'BANCA_AGENDADA')
        fim = timezone.now() - timedelta(hours=1)
        Banca.objects.filter(pk=banca.pk).update(inicio=fim - timedelta(hours=1), fim=fim)
        self.assertEqual(self.client.post(reverse('api-realizar-banca', args=[banca.pk])).status_code, 200)
        emissao = self.client.post(reverse('api-emitir-avaliacao-externa', args=[externo.pk]))
        self.assertEqual(emissao.status_code, 200, emissao.content)
        codigo = emissao.data['codigo']
        self.assertNotEqual(codigo, convite)
        self.client.logout()
        externa = self.client.post(reverse('api-avaliacao-externa', args=[externo.pk]), {
            'codigo': codigo, 'nota': '8.00', 'parecer': 'Aprovado', 'recomendacao': 'APROVADA',
        }, content_type='application/json')
        self.assertEqual(externa.status_code, 201, externa.content)
        self.client.force_login(self.orientador_user)
        interna = self.client.post(reverse('api-minha-avaliacao', args=[interno.pk]), {
            'nota': '6.00', 'parecer': 'Aprovado', 'recomendacao': 'APROVADA',
        }, content_type='application/json')
        self.assertEqual(interna.status_code, 201, interna.content)
        fechamento = self.client.post(reverse('api-finalizar-banca', args=[banca.pk]))
        self.assertEqual(fechamento.status_code, 200, fechamento.content)
        self.assertEqual(fechamento.data['media'], '7.00')
