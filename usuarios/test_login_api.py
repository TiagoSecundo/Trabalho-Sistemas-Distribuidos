"""Regressões de login compartilhado e troca de identidade entre HTML e API."""
import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase, override_settings

from equipe.models import Aluno, Curso, Professor
from monografias.models import Monografia


# A matriz faz dezenas de logins pelo mesmo IP; não mede limites de frequência.
@override_settings(ACCOUNT_RATE_LIMITS=False)
class LoginAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user('admin-login', password='senha-login-123', is_staff=True, is_superuser=True)
        cls.aluno = User.objects.create_user('aluno-login', email='aluno@login.example', password='senha-login-123')
        cls.professor = User.objects.create_user('prof-login', password='senha-login-123')
        cls.coordenador = User.objects.create_user('coord-login', password='senha-login-123')
        cls.sem_perfil = User.objects.create_user('sem-perfil-login', password='senha-login-123')
        cls.aluno.groups.add(Group.objects.create(name='Alunos'))
        cls.professor.groups.add(Group.objects.create(name='Professores'))
        cls.coordenador.groups.add(Group.objects.create(name='Coordenadores'))
        professor = Professor.objects.create(usuario=cls.professor, nome='Orientador', email='prof@login.example', departamento='D', area_pesquisa='A')
        coordenador = Professor.objects.create(usuario=cls.coordenador, nome='Coordenador', email='coord@login.example', departamento='D', area_pesquisa='A')
        curso = Curso.objects.create(nome='Computação', codigo='LOGIN', coordenador=coordenador)
        aluno = Aluno.objects.create(usuario=cls.aluno, nome='Aluno', email=cls.aluno.email, matricula='LOGIN', curso=curso)
        cls.trabalho = Monografia.objects.create(titulo='Trabalho autorizado', resumo='Resumo', aluno=aluno, curso=curso, orientador=professor)
        cls.papeis = [(cls.admin, ['Administrador']), (cls.aluno, ['Aluno']), (cls.professor, ['Professor']), (cls.coordenador, ['Professor', 'Coordenador']), (cls.sem_perfil, [])]

    def basic(self, username='admin-login', password='senha-login-123'):
        return 'Basic ' + base64.b64encode(f'{username}:{password}'.encode()).decode()

    def test_mesmo_login_para_todos_os_perfis_e_rotas(self):
        for rota in ('/accounts/login/', '/entrar/', '/api-auth/login/'):
            for usuario, papeis in self.papeis:
                with self.subTest(rota=rota, usuario=usuario.username):
                    self.client.logout()
                    pagina = self.client.get(rota)
                    self.assertTemplateUsed(pagina, 'account/login.html')
                    self.assertContains(pagina, 'AllTeam')
                    response = self.client.post(rota, {'login': usuario.username, 'password': 'senha-login-123'})
                    self.assertRedirects(response, '/usuarios/painel/')
                    identidade = self.client.get('/api/usuarios/me/').json()
                    self.assertEqual(identidade['id'], usuario.pk)
                    self.assertEqual(identidade['papeis'], papeis)

    def test_login_email_next_api_e_destino_externo_rejeitado(self):
        response = self.client.post('/entrar/?next=/api/', {'login': self.aluno.email, 'password': 'senha-login-123'})
        self.assertRedirects(response, '/api/')
        self.client.logout()
        response = self.client.post('/api-auth/login/?next=https://example.com/', {'login': self.aluno.username, 'password': 'senha-login-123'})
        self.assertRedirects(response, '/usuarios/painel/')

    def test_raiz_da_api_reconhece_perfis_e_oferece_recursos_autorizados(self):
        for usuario, papeis in self.papeis:
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                response = self.client.get('/api/')
                self.assertEqual(response.status_code, 200)
                dados = response.json()
                self.assertEqual(dados['papeis'], papeis)
                self.assertEqual(dados['me'], 'http://testserver/api/usuarios/me/')
                self.assertEqual('minhas-monografias' in dados, bool(papeis))
                self.assertEqual('meus-rascunhos' in dados, usuario == self.aluno)
                self.assertEqual('alunos' in dados, usuario == self.admin)
                if papeis:
                    trabalhos = self.client.get('/api/usuarios/monografias/').json()['results']
                    self.assertEqual([item['id'] for item in trabalhos], [self.trabalho.pk])

    def test_logout_e_troca_de_usuario_sem_limpar_cookies(self):
        for saida in ('/sair/', '/accounts/logout/', '/api-auth/logout/'):
            with self.subTest(saida=saida):
                self.client.post('/accounts/login/', {'login': self.admin.username, 'password': 'senha-login-123'})
                self.assertEqual(self.client.get('/api/alunos/').status_code, 200)
                pagina = self.client.get(saida)
                if saida == '/accounts/logout/':
                    # O allauth mantém a confirmação por GET; só POST encerra.
                    self.assertContains(pagina, 'Confirmar saída')
                    self.assertTemplateUsed(pagina, 'account/logout.html')
                else:
                    self.assertEqual(pagina.status_code, 405)
                self.assertEqual(self.client.get('/api/usuarios/me/').json()['id'], self.admin.pk)
                self.assertRedirects(self.client.post(saida), '/accounts/login/')
                self.assertIn(self.client.get('/api/usuarios/me/').status_code, (401, 403))
                response = self.client.post('/accounts/login/', {'login': self.aluno.username, 'password': 'senha-login-123'})
                self.assertRedirects(response, '/usuarios/painel/')
                self.assertEqual(self.client.get('/api/usuarios/me/').json()['id'], self.aluno.pk)
                self.assertEqual(self.client.get('/api/alunos/').status_code, 403)
                self.client.post(saida)

    def test_sessao_tem_prioridade_sobre_credenciais_basic_antigas(self):
        self.client.force_login(self.aluno)
        for credencial in (self.basic(), self.basic(password='incorreta')):
            with self.subTest(credencial_valida=credencial == self.basic()):
                response = self.client.get('/api/usuarios/me/', HTTP_AUTHORIZATION=credencial)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['id'], self.aluno.pk)
                self.assertEqual(self.client.get('/api/alunos/', HTTP_AUTHORIZATION=credencial).status_code, 403)

    def test_navegador_apos_logout_ignora_basic_retido_e_nao_pede_senha_nativa(self):
        for headers in ({'HTTP_ACCEPT': 'text/html'}, {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}, {'HTTP_SEC_FETCH_MODE': 'cors', 'HTTP_ACCEPT': 'application/json'}):
            with self.subTest(headers=headers):
                self.client.force_login(self.admin)
                self.client.post('/sair/')
                response = self.client.get('/api/usuarios/me/', HTTP_AUTHORIZATION=self.basic(), **headers)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn('WWW-Authenticate', response)

    def test_basic_continua_disponivel_para_clientes_sem_sessao(self):
        for usuario, papeis in self.papeis:
            response = self.client.get('/api/usuarios/me/', HTTP_AUTHORIZATION=self.basic(usuario.username), HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['papeis'], papeis)
        response = self.client.get('/api/usuarios/me/')
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response['WWW-Authenticate'].startswith('Basic'))

    def test_sessao_com_basic_nao_contorna_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post('/api/cursos/', {'nome': 'Sem CSRF', 'codigo': 'CSRF'}, HTTP_AUTHORIZATION=self.basic())
        self.assertEqual(response.status_code, 403)
        for saida in ('/sair/', '/accounts/logout/', '/api-auth/logout/'):
            self.assertEqual(client.post(saida).status_code, 403)

    def test_usuario_academico_nao_entra_em_loop_no_crud_staff(self):
        self.client.force_login(self.aluno)
        for rota in ('/equipe/', '/monografias/'):
            self.assertEqual(self.client.get(rota).status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.get('/monografias/'), '/accounts/login/?next=/monografias/')

    def test_api_navegavel_vincula_login_painel_e_saida_post(self):
        response = self.client.get('/api/', HTTP_ACCEPT='text/html')
        self.assertContains(response, '/accounts/login/?next=/api/', status_code=403)
        self.assertNotIn('WWW-Authenticate', response)
        self.client.force_login(self.aluno)
        response = self.client.get('/api/', HTTP_ACCEPT='text/html')
        self.assertContains(response, '/usuarios/painel/')
        self.assertContains(response, 'action="/sair/"')
        self.assertContains(response, 'csrfmiddlewaretoken')
