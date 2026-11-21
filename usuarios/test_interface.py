from datetime import timedelta
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from monografias.models import Banca, HistoricoAcao, MembroExterno, Monografia, ParticipacaoBanca
from usuarios.services import salvar_rascunho


class PerfisInterfaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.aluno_user = User.objects.create_user('aluna-telas', email='aluna@example.com', password='senha-telas-123')
        cls.prof_user = User.objects.create_user('prof-telas', email='prof@example.com', password='senha-telas-123')
        cls.outro_user = User.objects.create_user('outro-telas', password='senha-telas-123')
        cls.admin = User.objects.create_user('admin-telas', password='senha-telas-123', is_staff=True, is_superuser=True)
        cls.sem_perfil = User.objects.create_user('sem-perfil', password='senha-telas-123')
        cls.inativo = User.objects.create_user('inativo', password='senha-telas-123', is_active=False)
        alunos = Group.objects.create(name='Alunos')
        professores = Group.objects.create(name='Professores')
        coordenadores = Group.objects.create(name='Coordenadores')
        cls.aluno_user.groups.add(alunos)
        cls.outro_user.groups.add(alunos)
        cls.prof_user.groups.add(professores, coordenadores)
        cls.professor = Professor.objects.create(usuario=cls.prof_user, nome='Ana Professora', email='prof@example.com', departamento='Computação', area_pesquisa='Redes')
        cls.outro_professor = Professor.objects.create(nome='Outro Professor', email='outroprof@example.com', departamento='Outro', area_pesquisa='Redes')
        cls.curso = Curso.objects.create(nome='Computação', codigo='COMP', coordenador=cls.professor)
        cls.outro_curso = Curso.objects.create(nome='Outro Curso', codigo='OUTRO')
        cls.aluno = Aluno.objects.create(usuario=cls.aluno_user, nome='Aluna Principal', email='aluna@example.com', matricula='T001', curso=cls.curso)
        cls.outro_aluno = Aluno.objects.create(usuario=cls.outro_user, nome='Outro Aluno', email='outro@example.com', matricula='T002', curso=cls.outro_curso)
        cls.trabalho = Monografia.objects.create(titulo='Trabalho autorizado', resumo='Resumo', aluno=cls.aluno, curso=cls.curso, orientador=cls.professor)
        cls.outro_trabalho = Monografia.objects.create(titulo='Trabalho privado de outro curso', resumo='Privado', aluno=cls.outro_aluno, curso=cls.outro_curso, orientador=cls.outro_professor)
        cls.coordenado = Monografia.objects.create(titulo='Somente coordenação', resumo='Resumo', aluno=cls.aluno, curso=cls.curso, orientador=cls.outro_professor)
        cls.coorientado = Monografia.objects.create(titulo='Coorientação', resumo='Resumo', aluno=cls.outro_aluno, curso=cls.outro_curso, orientador=cls.outro_professor, coorientador=cls.professor)
        cls.banca = Banca.objects.create(monografia=cls.trabalho, inicio=timezone.now()+timedelta(days=10), fim=timezone.now()+timedelta(days=10, hours=1), local='Sala 1')
        cls.externo = MembroExterno.objects.create(nome='Pessoa Externa', email='externo@example.com', instituicao='Instituição Parceira')
        cls.participacao = ParticipacaoBanca.objects.create(banca=cls.banca, membro_externo=cls.externo)

    def entrar(self, usuario):
        self.client.force_login(usuario)

    def test_anonimo_precisa_login_para_todas_as_telas_privadas(self):
        paths = ['/usuarios/painel/', '/usuarios/painel/aluno/', '/usuarios/painel/professor/', '/usuarios/painel/coordenador/', '/usuarios/painel/administrador/', '/usuarios/rascunhos/novo/', f'/usuarios/trabalhos/{self.trabalho.pk}/', f'/usuarios/rascunhos/{self.trabalho.pk}/editar/', f'/usuarios/rascunhos/{self.trabalho.pk}/excluir/', f'/usuarios/convites/{self.participacao.pk}/emitir/']
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith('/accounts/login/?next='))

    def test_login_allauth_email_nao_confirmado_chega_ao_painel(self):
        EmailAddress.objects.create(user=self.aluno_user, email=self.aluno_user.email, primary=True, verified=False)
        response = self.client.post('/accounts/login/', {'login': self.aluno_user.username, 'password': 'senha-telas-123'})
        self.assertRedirects(response, '/usuarios/painel/')
        self.assertContains(self.client.get(response.url), 'Meu percurso acadêmico')

    def test_conta_inativa_nao_entra(self):
        response = self.client.post('/accounts/login/', {'login': self.inativo.username, 'password': 'senha-telas-123'}, follow=True)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_sem_vinculo_tem_orientacao_e_logout_sem_acesso_academico(self):
        self.sem_perfil.groups.add(Group.objects.get(name='Alunos'))
        self.entrar(self.sem_perfil)
        response = self.client.get('/usuarios/painel/')
        self.assertContains(response, 'Seu acesso acadêmico está em preparação')
        self.assertContains(response, 'Meu painel')
        self.assertContains(response, 'Sair')
        self.assertEqual(self.client.get('/usuarios/painel/aluno/').status_code, 403)
        self.assertEqual(self.client.get(f'/usuarios/trabalhos/{self.trabalho.pk}/').status_code, 404)

    def test_aluno_ve_somente_seus_trabalhos_e_contadores(self):
        self.entrar(self.aluno_user)
        response = self.client.get('/usuarios/painel/aluno/')
        self.assertContains(response, self.trabalho.titulo)
        self.assertContains(response, self.coordenado.titulo)
        self.assertNotContains(response, self.outro_trabalho.titulo)
        self.assertNotContains(response, self.coorientado.titulo)
        self.assertEqual(response.context['resumo']['total'], 2)
        self.assertContains(response, 'Novo rascunho')
        self.assertNotContains(response, 'Contas e acessos')
        self.assertEqual(self.client.get('/usuarios/painel/administrador/').status_code, 403)

    def test_professor_e_coordenador_alternam_escopos_sem_ampliar_permissoes(self):
        self.entrar(self.prof_user)
        response = self.client.get('/usuarios/painel/professor/')
        self.assertContains(response, self.trabalho.titulo)
        self.assertContains(response, self.coorientado.titulo)
        self.assertNotContains(response, self.coordenado.titulo)
        response = self.client.get('/usuarios/painel/coordenador/')
        self.assertContains(response, self.coordenado.titulo)
        self.assertNotContains(response, self.coorientado.titulo)
        self.assertNotContains(response, self.outro_trabalho.titulo)
        self.assertEqual(self.client.get('/usuarios/rascunhos/novo/').status_code, 403)
        self.assertEqual(self.client.get('/api/alunos/').status_code, 403)

    def test_admin_ve_gestao_e_prioridade_do_papel(self):
        self.admin.groups.add(Group.objects.get(name='Alunos'))
        self.entrar(self.admin)
        response = self.client.get('/usuarios/painel/')
        self.assertContains(response, 'Gestão acadêmica')
        self.assertContains(response, self.outro_trabalho.titulo)
        self.assertEqual(response.context['resumo']['total'], 4)
        self.assertEqual(self.client.get('/usuarios/painel/aluno/').status_code, 403)

    def test_busca_estado_e_paginacao_preservam_escopo(self):
        Monografia.objects.bulk_create([Monografia(titulo=f'Busca {i}', resumo='R', aluno=self.aluno, curso=self.curso, orientador=self.professor) for i in range(12)])
        self.entrar(self.aluno_user)
        response = self.client.get('/usuarios/painel/aluno/', {'q': 'Busca', 'estado': 'RASCUNHO', 'page': 2})
        self.assertEqual(response.context['pagina'].paginator.count, 12)
        self.assertEqual(len(response.context['pagina']), 2)
        self.assertContains(response, 'Página 2 de 2')
        response = self.client.get('/usuarios/painel/aluno/', {'q': self.outro_trabalho.titulo})
        self.assertEqual(response.context['pagina'].paginator.count, 0)
        self.assertContains(response, 'Nenhum trabalho encontrado')

    def test_detalhes_isolam_usuario_e_escapam_conteudo(self):
        self.entrar(self.outro_user)
        self.assertEqual(self.client.get(f'/usuarios/trabalhos/{self.trabalho.pk}/').status_code, 404)
        self.entrar(self.aluno_user)
        Monografia.objects.filter(pk=self.trabalho.pk).update(titulo='<script>alert(1)</script>')
        response = self.client.get(f'/usuarios/trabalhos/{self.trabalho.pk}/')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, 'Gerar convite')

    def test_formulario_html_cria_edita_exclui_e_audita(self):
        self.entrar(self.aluno_user)
        payload = {'titulo': 'Rascunho HTML', 'resumo': 'Resumo', 'palavras_chave': 'Django, testes', 'orientador': self.professor.pk}
        response = self.client.post('/usuarios/rascunhos/novo/', payload)
        trabalho = Monografia.objects.get(titulo='Rascunho HTML')
        self.assertRedirects(response, reverse('usuarios:trabalho', args=[trabalho.pk]))
        self.assertEqual(trabalho.aluno, self.aluno)
        self.assertEqual(trabalho.palavras_chave, ['Django', 'testes'])
        payload['titulo'] = 'HTML editado'
        self.assertEqual(self.client.post(reverse('usuarios:editar-rascunho', args=[trabalho.pk]), payload).status_code, 302)
        self.assertEqual(self.client.post(reverse('usuarios:excluir-rascunho', args=[trabalho.pk])).status_code, 302)
        self.assertFalse(Monografia.objects.filter(pk=trabalho.pk).exists())
        acoes = list(HistoricoAcao.objects.filter(objeto=f'Monografia:{trabalho.pk}').values_list('acao', flat=True))
        self.assertCountEqual(acoes, ['RASCUNHO_CRIADO', 'RASCUNHO_ALTERADO', 'RASCUNHO_EXCLUIDO'])

    def test_html_nao_aceita_escolher_dono_curso_ou_estado(self):
        self.entrar(self.aluno_user)
        response = self.client.post('/usuarios/rascunhos/novo/', {'titulo': 'Dono correto', 'resumo': 'R', 'orientador': self.professor.pk, 'aluno': self.outro_aluno.pk, 'curso': self.outro_curso.pk, 'status_fluxo': 'PUBLICADA'})
        self.assertEqual(response.status_code, 302)
        trabalho = Monografia.objects.get(titulo='Dono correto')
        self.assertEqual((trabalho.aluno_id, trabalho.curso_id, trabalho.status_fluxo), (self.aluno.pk, self.curso.pk, 'RASCUNHO'))

    def test_nao_edita_outro_aluno_nem_estado_fechado(self):
        self.entrar(self.outro_user)
        for acao in ('editar', 'excluir'):
            url = f'/usuarios/rascunhos/{self.trabalho.pk}/{acao}/'
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {'titulo': 'Invasão'}).status_code, 404)
        self.entrar(self.aluno_user)
        Monografia.objects.filter(pk=self.trabalho.pk).update(status_fluxo='APROVADA_ORIENTADOR')
        for acao in ('editar', 'excluir'):
            url = f'/usuarios/rascunhos/{self.trabalho.pk}/{acao}/'
            self.assertEqual(self.client.get(url).status_code, 409)
            self.assertEqual(self.client.post(url, {'titulo': 'Inválido'}).status_code, 409)
        self.assertEqual(self.client.post(f'/usuarios/rascunhos/{self.coordenado.pk}/editar/', {'titulo': 'Inválido', 'resumo': 'R', 'orientador': self.professor.pk, 'coorientador': self.professor.pk}).status_code, 200)
        self.coordenado.refresh_from_db()
        self.assertEqual(self.coordenado.titulo, 'Somente coordenação')

    def test_exclusao_com_dependencia_fica_protegida(self):
        self.entrar(self.aluno_user)
        response = self.client.post(f'/usuarios/rascunhos/{self.trabalho.pk}/excluir/')
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Monografia.objects.filter(pk=self.trabalho.pk).exists())

    def test_escritas_html_exigem_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.aluno_user)
        self.assertEqual(client.post('/usuarios/rascunhos/novo/', {}).status_code, 403)
        self.assertEqual(client.post(f'/usuarios/convites/{self.participacao.pk}/', {'token': 'falso'}).status_code, 403)

    def test_servico_faz_rollback_quando_auditoria_falha(self):
        with patch('usuarios.services.HistoricoAcao.objects.create', side_effect=RuntimeError('Falha controlada')):
            with self.assertRaises(RuntimeError):
                salvar_rascunho(self.aluno_user, {'titulo': 'Rollback', 'resumo': 'R', 'orientador': self.professor})
        self.assertFalse(Monografia.objects.filter(titulo='Rollback').exists())

    def test_convite_html_exige_curso_e_aprovacao(self):
        self.entrar(self.aluno_user)
        url = reverse('usuarios:emitir-convite', args=[self.participacao.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.entrar(self.prof_user)
        self.assertEqual(self.client.post(url).status_code, 400)
        outra_banca = Banca.objects.create(monografia=self.outro_trabalho, inicio=self.banca.inicio, fim=self.banca.fim, local='Sala 2')
        outra = ParticipacaoBanca.objects.create(banca=outra_banca, membro_externo=self.externo)
        self.assertEqual(self.client.get(reverse('usuarios:emitir-convite', args=[outra.pk])).status_code, 404)

    def test_convite_html_token_temporario_confirmacao_e_privacidade(self):
        Monografia.objects.filter(pk=self.trabalho.pk).update(status_fluxo='APROVADA_ORIENTADOR')
        self.entrar(self.prof_user)
        url = reverse('usuarios:emitir-convite', args=[self.participacao.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        token = response.context['token']
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotIn(token, response.context['url_confirmacao'])
        self.assertNotContains(self.client.get(url), token)
        self.client.logout()
        confirmacao = reverse('usuarios:confirmar-convite', args=[self.participacao.pk])
        self.assertNotContains(self.client.get(confirmacao), self.trabalho.titulo)
        self.assertEqual(self.client.post(confirmacao, {'token': 'falso'}).status_code, 403)
        self.assertContains(self.client.post(confirmacao, {'token': token}), 'Participação confirmada com sucesso')
        self.assertEqual(self.client.post(confirmacao, {'token': token}).status_code, 403)
        self.participacao.refresh_from_db()
        self.assertEqual(self.participacao.convite_status, 'CONFIRMADO')
