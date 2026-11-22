"""Testes B11: defesa, avaliação própria, média, permissões e fechamento."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from monografias.models import Avaliacao, Banca, HistoricoAcao, Monografia, ParticipacaoBanca


class FluxoAvaliacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.docente = User.objects.create_user('docente-b11', password='Teste123!')
        cls.avaliador = User.objects.create_user('avaliador-b11', password='Teste123!')
        cls.suplente_user = User.objects.create_user('suplente-b11', password='Teste123!')
        cls.estranho = User.objects.create_user('estranho-b11', password='Teste123!')
        cls.aluno_user = User.objects.create_user('aluno-b11', password='Teste123!')
        cls.orientador = Professor.objects.create(usuario=cls.docente, nome='Orientadora', email='orientadora-b11@example.com', departamento='D', area_pesquisa='A')
        cls.professor2 = Professor.objects.create(usuario=cls.avaliador, nome='Avaliador', email='avaliador-b11@example.com', departamento='D', area_pesquisa='A')
        cls.professor3 = Professor.objects.create(usuario=cls.suplente_user, nome='Suplente', email='suplente-b11@example.com', departamento='D', area_pesquisa='A')
        cls.curso = Curso.objects.create(nome='Computação B11', codigo='B11')
        cls.aluno = Aluno.objects.create(usuario=cls.aluno_user, nome='Aluno B11', matricula='B11-001', email='aluno-b11@example.com', curso=cls.curso)
        cls.monografia = Monografia.objects.create(titulo='TCC B11', resumo='Resumo', aluno=cls.aluno, curso=cls.curso, orientador=cls.orientador, status_fluxo='BANCA_AGENDADA')
        inicio = timezone.now() - timedelta(days=2)
        cls.banca = Banca.objects.create(monografia=cls.monografia, inicio=inicio, fim=inicio+timedelta(hours=1), local='Sala 1', status='AGENDADA')
        cls.presidente = ParticipacaoBanca.objects.create(banca=cls.banca, professor=cls.orientador, papel='PRESIDENTE')
        cls.titular = ParticipacaoBanca.objects.create(banca=cls.banca, professor=cls.professor2, papel='AVALIADOR')
        cls.suplente = ParticipacaoBanca.objects.create(banca=cls.banca, professor=cls.professor3, papel='SUPLENTE')

    def realizar(self):
        self.client.force_login(self.docente)
        resposta = self.client.post(reverse('api-realizar-banca', args=[self.banca.pk]))
        self.assertEqual(resposta.status_code, 200, resposta.content)

    def avaliar(self, usuario, participacao, nota, recomendacao='APROVADA'):
        self.client.force_login(usuario)
        return self.client.post(reverse('api-minha-avaliacao', args=[participacao.pk]), {
            'nota': nota, 'parecer': 'Parecer fundamentado', 'recomendacao': recomendacao,
        }, content_type='application/json')

    def fechar(self):
        self.client.force_login(self.docente)
        return self.client.post(reverse('api-finalizar-banca', args=[self.banca.pk]))

    def test_resultado_aprovado_media_exatamente_seis(self):
        self.realizar()
        self.assertEqual(self.avaliar(self.docente, self.presidente, '6.00').status_code, 201)
        self.assertEqual(self.avaliar(self.avaliador, self.titular, '6.00').status_code, 201)
        resposta = self.fechar()
        self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertEqual((resposta.data['media'], resposta.data['resultado']), ('6.00', 'APROVADA'))
        self.monografia.refresh_from_db()
        self.assertEqual(self.monografia.status_fluxo, 'APROVADA')
        self.assertEqual(Avaliacao.objects.filter(participacao__banca=self.banca, finalizada_em__isnull=False).count(), 2)
        self.assertTrue(HistoricoAcao.objects.filter(acao='RESULTADO_BANCA_FINALIZADO', detalhes__resultado='APROVADA').exists())
        self.assertEqual(self.avaliar(self.docente, self.presidente, '9.00').status_code, 409)
        self.assertEqual(self.fechar().status_code, 409)

    def test_resultado_ressalvas_e_recomendacao_individual_reprovado(self):
        self.realizar()
        self.avaliar(self.docente, self.presidente, '8.00', 'REPROVADA')
        self.avaliar(self.avaliador, self.titular, '6.00', 'APROVADA_COM_RESSALVAS')
        self.assertEqual(self.fechar().data, {'banca_id': self.banca.pk, 'media': '7.00', 'resultado': 'APROVADA_COM_RESSALVAS'})

    def test_recomendacao_reprovado_nao_e_veto_individual(self):
        self.realizar()
        self.avaliar(self.docente, self.presidente, '6.00', 'REPROVADA')
        self.avaliar(self.avaliador, self.titular, '8.00')
        self.assertEqual(self.fechar().data['resultado'], 'APROVADA')

    def test_media_abaixo_de_seis_reprova(self):
        self.realizar()
        self.avaliar(self.docente, self.presidente, '5.00', 'APROVADA')
        self.avaliar(self.avaliador, self.titular, '6.00', 'APROVADA')
        resposta = self.fechar()
        self.assertEqual((resposta.data['media'], resposta.data['resultado']), ('5.50', 'REPROVADA'))

    def test_nao_fecha_com_avaliacao_faltando_e_nao_conta_suplente(self):
        self.realizar()
        self.avaliar(self.docente, self.presidente, '9.00')
        self.assertEqual(self.fechar().status_code, 400)
        self.assertEqual(self.avaliar(self.suplente_user, self.suplente, '9.00').status_code, 403)
        self.monografia.refresh_from_db()
        self.assertEqual(self.monografia.status_fluxo, 'DEFESA_REALIZADA')
        self.assertFalse(Avaliacao.objects.filter(participacao=self.presidente, finalizada_em__isnull=False).exists())

    def test_aluno_e_terceiros_nao_avaliam_ou_fecham(self):
        self.realizar()
        self.assertEqual(self.avaliar(self.aluno_user, self.presidente, '10.00').status_code, 404)
        self.assertEqual(self.avaliar(self.estranho, self.presidente, '10.00').status_code, 404)
        self.client.force_login(self.aluno_user)
        self.assertEqual(self.client.post(reverse('api-finalizar-banca', args=[self.banca.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse('api-realizar-banca', args=[self.banca.pk])).status_code, 403)
        self.assertEqual(Avaliacao.objects.count(), 0)

    def test_validacao_nota_e_edicao_antes_do_fechamento(self):
        self.realizar()
        self.assertEqual(self.avaliar(self.docente, self.presidente, '10.50').status_code, 400)
        self.assertEqual(self.avaliar(self.docente, self.presidente, '6.00').status_code, 201)
        self.assertEqual(self.avaliar(self.docente, self.presidente, '8.50', 'APROVADA_COM_RESSALVAS').status_code, 200)
        self.assertEqual(Avaliacao.objects.get(participacao=self.presidente).nota, Decimal('8.50'))
        self.assertEqual(Avaliacao.objects.count(), 1)

    def test_defesa_nao_pode_ser_realizada_antes_da_aprovacao(self):
        self.monografia.status_fluxo = 'RASCUNHO'
        self.monografia.save(update_fields=['status_fluxo'])
        self.client.force_login(self.docente)
        resposta = self.client.post(reverse('api-realizar-banca', args=[self.banca.pk]))
        self.assertEqual(resposta.status_code, 409)
        self.banca.refresh_from_db()
        self.assertEqual(self.banca.status, 'AGENDADA')

    def test_formulario_html_aproveita_painel_existente(self):
        self.realizar()
        self.client.force_login(self.docente)
        detalhes = self.client.get(reverse('usuarios:trabalho', args=[self.monografia.pk]))
        self.assertContains(detalhes, 'Registrar minha avaliação')
        pagina = self.client.get(reverse('usuarios:avaliar-participacao', args=[self.presidente.pk]))
        self.assertContains(pagina, 'Recomendação')
        resposta = self.client.post(reverse('usuarios:avaliar-participacao', args=[self.presidente.pk]), {
            'nota': '6.00', 'parecer': 'Aprovado', 'recomendacao': 'APROVADA',
        })
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Avaliacao.objects.filter(participacao=self.presidente).exists())
        self.client.force_login(self.estranho)
        self.assertEqual(self.client.get(reverse('usuarios:avaliar-participacao', args=[self.presidente.pk])).status_code, 404)

    def test_defesa_futura_nao_pode_ser_marcada_realizada(self):
        self.banca.fim = timezone.now() + timedelta(days=1)
        self.banca.save(update_fields=['fim'])
        self.client.force_login(self.docente)
        resposta = self.client.post(reverse('api-realizar-banca', args=[self.banca.pk]))
        self.assertEqual(resposta.status_code, 400)
