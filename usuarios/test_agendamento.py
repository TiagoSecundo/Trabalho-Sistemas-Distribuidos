"""B10: ciclo de convite e agendamento sem depender de RabbitMQ ou microserviço."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from monografias.models import Banca, HistoricoAcao, MembroExterno, Monografia, ParticipacaoBanca


class FluxoAgendamentoB10Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.orientador_user = User.objects.create_user('prof-b10', password='Segura123!')
        cls.avaliador_user = User.objects.create_user('avaliador-b10', password='Segura123!')
        cls.outro_user = User.objects.create_user('outro-b10', password='Segura123!')
        cls.aluno_user = User.objects.create_user('aluno-b10', password='Segura123!')
        cls.admin = User.objects.create_superuser('admin-b10', email='admin-b10@example.com', password='Segura123!')
        cls.orientador = Professor.objects.create(usuario=cls.orientador_user, nome='Orientador', email='orientador-b10@example.com', departamento='D', area_pesquisa='A')
        cls.avaliador = Professor.objects.create(usuario=cls.avaliador_user, nome='Avaliador', email='avaliador-b10@example.com', departamento='D', area_pesquisa='A')
        cls.curso = Curso.objects.create(nome='Curso B10', codigo='B10', coordenador=cls.orientador)
        cls.aluno = Aluno.objects.create(usuario=cls.aluno_user, nome='Aluna', matricula='B10-1', email='aluno-b10@example.com', curso=cls.curso)
        cls.monografia = Monografia.objects.create(titulo='Trabalho B10', resumo='R', aluno=cls.aluno, curso=cls.curso, orientador=cls.orientador, status_fluxo='APROVADA_ORIENTADOR')
        cls.outra = Monografia.objects.create(titulo='Outro B10', resumo='R', aluno=cls.aluno, curso=cls.curso, orientador=cls.orientador, status_fluxo='APROVADA_ORIENTADOR')
        cls.externo = MembroExterno.objects.create(nome='Membro Externo', email='externo-b10@example.com', instituicao='Outra Instituição')

    def dados(self, *, dias=6, deslocamento=0):
        inicio = timezone.now().replace(microsecond=0) + timedelta(days=dias, minutes=deslocamento)
        return {'inicio': inicio.isoformat(), 'fim': (inicio + timedelta(hours=1)).isoformat(), 'modalidade': 'PRESENCIAL', 'local': 'Sala B10'}

    def propor(self, monografia=None, usuario=None, **kw):
        self.client.force_login(usuario or self.orientador_user)
        return self.client.post(reverse('api-propor-banca', args=[(monografia or self.monografia).pk]), self.dados(**kw))

    def incluir(self, banca, professor=None, membro_externo=None, papel='AVALIADOR'):
        self.client.force_login(self.orientador_user)
        dados = {'papel': papel}
        if professor is not None:
            dados['professor'] = professor.pk
        if membro_externo is not None:
            dados['membro_externo'] = membro_externo.pk
        return self.client.post(reverse('api-adicionar-participante', args=[banca.pk]), dados)

    def responder(self, usuario, participacao, acao='confirmar'):
        self.client.force_login(usuario)
        return self.client.post(reverse('api-responder-convite-interno', args=[participacao.pk]), {'acao': acao})

    def test_nao_cria_banca_sem_aprovacao_do_orientador(self):
        Monografia.objects.filter(pk=self.monografia.pk).update(status_fluxo='RASCUNHO')
        self.assertEqual(self.propor().status_code, 409)
        self.assertFalse(Banca.objects.exists())

    def test_aluno_e_terceiro_nao_agendam(self):
        self.assertEqual(self.propor(usuario=self.aluno_user).status_code, 403)
        self.assertEqual(self.propor(usuario=self.outro_user).status_code, 403)
        self.assertFalse(Banca.objects.exists())

    def test_proposta_nao_e_agendamento_e_valida_futuro(self):
        resposta = self.propor()
        self.assertEqual(resposta.status_code, 201, resposta.content)
        banca = Banca.objects.get(pk=resposta.json()['id'])
        self.assertEqual(banca.status, 'PENDENTE')
        self.monografia.refresh_from_db()
        self.assertEqual(self.monografia.status_fluxo, 'APROVADA_ORIENTADOR')
        self.assertEqual(self.propor().status_code, 409)
        self.assertTrue(HistoricoAcao.objects.filter(acao='PROPOSTA_BANCA_CRIADA').exists())
        self.client.force_login(self.orientador_user)
        dados = self.dados(dias=-1)
        self.assertEqual(self.client.post(reverse('api-propor-banca', args=[self.outra.pk]), dados).status_code, 409)

    def test_professor_confirma_agenda_apos_todos_confirmarem(self):
        banca = Banca.objects.get(pk=self.propor().json()['id'])
        resp_a = self.incluir(banca, professor=self.orientador, papel='PRESIDENTE')
        resp_b = self.incluir(banca, professor=self.avaliador)
        self.assertEqual((resp_a.status_code, resp_b.status_code), (201, 201))
        p1 = ParticipacaoBanca.objects.get(pk=resp_a.json()['id'])
        p2 = ParticipacaoBanca.objects.get(pk=resp_b.json()['id'])
        self.assertEqual(self.responder(self.orientador_user, p1).json()['banca_agendada'], False)
        banca.refresh_from_db()
        self.assertEqual(banca.status, 'PENDENTE')
        self.assertEqual(self.responder(self.avaliador_user, p2).json()['banca_agendada'], True)
        banca.refresh_from_db()
        self.monografia.refresh_from_db()
        self.assertEqual(banca.status, 'AGENDADA')
        self.assertEqual(self.monografia.status_fluxo, 'BANCA_AGENDADA')
        self.assertEqual(self.responder(self.avaliador_user, p2).status_code, 409)

    def test_nao_marca_agendada_antes_de_incluir_avaliador(self):
        banca = Banca.objects.get(pk=self.propor().json()['id'])
        self.assertEqual(banca.status, 'PENDENTE')
        self.assertFalse(ParticipacaoBanca.objects.filter(banca=banca).exists())

    def test_token_externo_confirma_ou_recusa_e_agenda(self):
        banca = Banca.objects.get(pk=self.propor().json()['id'])
        p = ParticipacaoBanca.objects.get(pk=self.incluir(banca, membro_externo=self.externo).json()['id'])
        self.client.force_login(self.orientador_user)
        emitido = self.client.post(reverse('emitir-convite-externo', args=[p.pk]))
        self.assertEqual(emitido.status_code, 200)
        token = emitido.json()['token']
        self.client.logout()
        uri = reverse('confirmar-convite-externo', args=[p.pk])
        self.assertEqual(self.client.post(uri, {'token': 'invalido'}).status_code, 403)
        resposta = self.client.post(uri, {'token': token})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['banca_agendada'])
        self.assertEqual(self.client.post(uri, {'token': token}).status_code, 403)
        self.assertEqual(Banca.objects.get(pk=banca.pk).status, 'AGENDADA')

    def test_recusa_e_substituicao(self):
        banca = Banca.objects.get(pk=self.propor().json()['id'])
        p = ParticipacaoBanca.objects.get(pk=self.incluir(banca, professor=self.avaliador).json()['id'])
        self.assertEqual(self.responder(self.avaliador_user, p, 'recusar').status_code, 200)
        self.assertEqual(banca.participacoes.get().convite_status, 'RECUSADO')
        self.client.force_login(self.orientador_user)
        self.assertEqual(self.client.delete(reverse('api-retirar-participante', args=[p.pk])).status_code, 204)
        self.assertEqual(self.incluir(banca, professor=self.orientador).status_code, 201)

    def test_participante_de_outra_banca_nao_confirma(self):
        banca = Banca.objects.get(pk=self.propor().json()['id'])
        p = ParticipacaoBanca.objects.get(pk=self.incluir(banca, professor=self.avaliador).json()['id'])
        self.assertEqual(self.responder(self.outro_user, p).status_code, 403)
        self.assertEqual(p.convite_status, 'CONVIDADO')

    def test_conflito_de_horario_so_considera_confirmacoes(self):
        banca1 = Banca.objects.get(pk=self.propor().json()['id'])
        banca2 = Banca.objects.get(pk=self.propor(monografia=self.outra, deslocamento=30).json()['id'])
        p1 = ParticipacaoBanca.objects.get(pk=self.incluir(banca1, professor=self.avaliador).json()['id'])
        p2 = ParticipacaoBanca.objects.get(pk=self.incluir(banca2, professor=self.avaliador).json()['id'])
        self.assertEqual(self.responder(self.avaliador_user, p1).status_code, 200)
        self.assertEqual(self.responder(self.avaliador_user, p2).status_code, 400)
        self.assertEqual(ParticipacaoBanca.objects.get(pk=p2.pk).convite_status, 'CONVIDADO')
        self.assertEqual(Banca.objects.get(pk=banca2.pk).status, 'PENDENTE')

    def test_agendamento_sem_sobreposicao_e_permitido(self):
        banca1 = Banca.objects.get(pk=self.propor().json()['id'])
        banca2 = Banca.objects.get(pk=self.propor(monografia=self.outra, deslocamento=60).json()['id'])
        p1 = ParticipacaoBanca.objects.get(pk=self.incluir(banca1, professor=self.avaliador).json()['id'])
        p2 = ParticipacaoBanca.objects.get(pk=self.incluir(banca2, professor=self.avaliador).json()['id'])
        self.assertEqual(self.responder(self.avaliador_user, p1).status_code, 200)
        self.assertEqual(self.responder(self.avaliador_user, p2).status_code, 200)
        self.assertEqual(Banca.objects.get(pk=banca2.pk).status, 'AGENDADA')

    def test_cancelar_proposta_permite_nova(self):
        banca = Banca.objects.get(pk=self.propor().json()['id'])
        self.client.force_login(self.orientador_user)
        self.assertEqual(self.client.post(reverse('api-cancelar-proposta', args=[banca.pk])).status_code, 200)
        self.assertEqual(Banca.objects.get(pk=banca.pk).status, 'CANCELADA')
        self.assertEqual(self.propor().status_code, 201)

    def test_html_reutiliza_painel_e_formularios(self):
        self.client.force_login(self.orientador_user)
        detalhe = self.client.get(reverse('usuarios:trabalho', args=[self.monografia.pk]))
        self.assertContains(detalhe, 'Propor banca')
        proposta = self.client.get(reverse('usuarios:propor-banca', args=[self.monografia.pk]))
        self.assertContains(proposta, 'Criar proposta')
        banca = Banca.objects.get(pk=self.propor().json()['id'])
        pagina = self.client.get(reverse('usuarios:adicionar-participante', args=[banca.pk]))
        self.assertContains(pagina, 'Incluir participante')
