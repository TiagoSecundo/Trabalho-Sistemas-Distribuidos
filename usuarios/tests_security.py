from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from equipe.models import Aluno, Curso, Professor
from monografias.models import Banca, HistoricoAcao, MembroExterno, Monografia, ParticipacaoBanca
from usuarios.roles import obter_papeis


class SegurancaAcademicaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.aluno_user = User.objects.create_user(username='aluno_seg', password='SenhaSegura123!')
        self.outro_user = User.objects.create_user(username='outro_seg', password='SenhaSegura123!')
        self.prof_user = User.objects.create_user(username='prof_seg', password='SenhaSegura123!')
        self.admin_user = User.objects.create_user(username='admin_seg', password='SenhaSegura123!', is_staff=True, is_superuser=True)
        grupo_aluno = Group.objects.create(name='Alunos')
        grupo_prof = Group.objects.create(name='Professores')
        grupo_coord = Group.objects.create(name='Coordenadores')
        self.aluno_user.groups.add(grupo_aluno)
        self.outro_user.groups.add(grupo_aluno)
        self.prof_user.groups.add(grupo_prof, grupo_coord)
        self.prof = Professor.objects.create(usuario=self.prof_user, nome='Prof', email='prof@seg.example', departamento='Computação', area_pesquisa='Segurança')
        self.curso = Curso.objects.create(nome='Sistemas', codigo='SIST', coordenador=self.prof)
        self.aluno = Aluno.objects.create(usuario=self.aluno_user, nome='Aluno A', matricula='SM001', email='aluno@seg.example', curso=self.curso)
        self.outro = Aluno.objects.create(usuario=self.outro_user, nome='Aluno B', matricula='SM002', email='outro@seg.example', curso=self.curso)
        self.mono = Monografia.objects.create(titulo='Monografia A', resumo='Resumo', aluno=self.aluno, orientador=self.prof, curso=self.curso)

    def test_grupo_sem_vinculo_nao_concede_papel(self):
        self.assertEqual(obter_papeis(self.aluno_user), ['Aluno'])
        self.assertIn('Coordenador', obter_papeis(self.prof_user))
        User = get_user_model()
        sem_vinculo = User.objects.create_user(username='semvinculo', password='SenhaSegura123!')
        sem_vinculo.groups.add(Group.objects.get(name='Alunos'))
        self.assertEqual(obter_papeis(sem_vinculo), [])

    def test_usuario_sem_vinculo_nao_usa_api_academica(self):
        User = get_user_model()
        sem_vinculo = User.objects.create_user(username='semvinculo', password='SenhaSegura123!')
        sem_vinculo.groups.add(Group.objects.get(name='Alunos'))
        self.client.force_login(sem_vinculo)
        response = self.client.get('/api/usuarios/monografias/')
        self.assertEqual(response.status_code, 403)

    def test_outro_aluno_nao_altera_tcc(self):
        self.client.force_login(self.outro_user)
        response = self.client.patch(
            f'/api/usuarios/rascunhos/{self.mono.pk}/',
            data='{"titulo":"Invasão"}', content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_aluno_nao_forja_aluno_de_outro_no_post(self):
        self.client.force_login(self.outro_user)
        response = self.client.post(
            '/api/usuarios/rascunhos/',
            data='{"titulo":"Teste","resumo":"R","orientador":%d,"aluno":%d,"curso":%d}' % (self.prof.pk, self.aluno.pk, self.curso.pk),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Monografia.objects.filter(titulo='Teste').exists())

    def test_aluno_cria_rascunho_pertencente_a_si(self):
        self.client.force_login(self.aluno_user)
        response = self.client.post(
            '/api/usuarios/rascunhos/',
            data='{"titulo":"Meu TCC","resumo":"R","orientador":%d}' % self.prof.pk,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Monografia.objects.get(titulo='Meu TCC').aluno_id, self.aluno.pk)

    def test_crud_administrativo_permanece_restrito(self):
        self.client.force_login(self.aluno_user)
        self.assertEqual(self.client.get('/api/alunos/').status_code, 403)

    def test_token_externo_expira_e_nao_e_reutilizado_para_confirmar(self):
        Monografia.objects.filter(pk=self.mono.pk).update(status_fluxo='APROVADA_ORIENTADOR')
        banca = Banca.objects.create(monografia=self.mono, inicio=timezone.now()+timedelta(days=5), fim=timezone.now()+timedelta(days=5, hours=1), local='Sala 1', status='AGENDADA')
        externo = MembroExterno.objects.create(nome='Externo', email='ext@seg.example', instituicao='Outra')
        participacao = ParticipacaoBanca.objects.create(banca=banca, membro_externo=externo)
        self.client.force_login(self.admin_user)
        resposta = self.client.post(f'/api/usuarios/convites/{participacao.pk}/emitir/')
        self.assertEqual(resposta.status_code, 200, resposta.content)
        token = resposta.json()['token']
        self.assertNotEqual(token, ParticipacaoBanca.objects.get(pk=participacao.pk).token_hash)
        self.client.logout()
        url = f'/api/usuarios/convites/{participacao.pk}/confirmar/'
        self.assertEqual(self.client.post(url, {'token': 'falso'}).status_code, 403)
        ParticipacaoBanca.objects.filter(pk=participacao.pk).update(
            expira_em=timezone.now() - timedelta(seconds=1)
        )
        self.assertEqual(self.client.post(url, {'token': token}).status_code, 403)
        ParticipacaoBanca.objects.filter(pk=participacao.pk).update(
            expira_em=timezone.now() + timedelta(days=2)
        )
        self.assertEqual(self.client.post(url, {'token': token}).status_code, 200)
        self.assertEqual(self.client.post(url, {'token': token}).status_code, 403)
        self.assertTrue(HistoricoAcao.objects.filter(acao='CONVITE_EXTERNO_CONFIRMADO').exists())

    def test_crud_admin_registra_auditoria(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            '/api/cursos/', data='{"nome":"Novo Curso","codigo":"NOVO"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(HistoricoAcao.objects.filter(ator=self.admin_user, acao='CRUD_CRIACAO').exists())

    def test_rascunho_nao_pode_ser_excluido_depois_de_aprovado(self):
        self.client.force_login(self.aluno_user)
        Monografia.objects.filter(pk=self.mono.pk).update(status_fluxo='APROVADA_ORIENTADOR')
        response = self.client.delete(f'/api/usuarios/rascunhos/{self.mono.pk}/')
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Monografia.objects.filter(pk=self.mono.pk).exists())

    def test_login_registrado_no_historico(self):
        self.client.force_login(self.aluno_user)
        self.assertTrue(HistoricoAcao.objects.filter(ator=self.aluno_user, acao='LOGIN').exists())
