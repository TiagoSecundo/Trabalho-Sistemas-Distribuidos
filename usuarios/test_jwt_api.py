"""Verifica o emissor recebido no merge com a matriz de papéis atual."""
from datetime import timedelta

import jwt
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from equipe.models import Aluno, Curso, Professor
from monografias.models import HistoricoAcao


CHAVE_TESTE = 'chave-local-de-teste-para-jwt-com-mais-de-32-caracteres'
JWT_TESTE = {'ALGORITHM': 'HS256', 'SIGNING_KEY': CHAVE_TESTE,
             'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10)}


@override_settings(SIMPLE_JWT=JWT_TESTE)
class EmissaoJWTTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.aluno_user = User.objects.create_user('aluno-jwt')
        cls.prof_user = User.objects.create_user('prof-jwt', is_staff=True)
        cls.sem_perfil = User.objects.create_user('sem-perfil-jwt', is_staff=True)
        cls.admin = User.objects.create_superuser('admin-jwt')
        cls.prof = Professor.objects.create(usuario=cls.prof_user, nome='Professor JWT',
                                            email='prof-jwt@example.com', departamento='D', area_pesquisa='A')
        cls.curso = Curso.objects.create(nome='Curso JWT', codigo='JWT', coordenador=cls.prof)
        cls.aluno = Aluno.objects.create(usuario=cls.aluno_user, nome='Aluno JWT',
                                         matricula='JWT001', email='aluno-jwt@example.com', curso=cls.curso)

    def emitir(self, user, role=None):
        self.client.force_login(user)
        return self.client.post('/api/usuarios/token-microservico/', {} if role is None else {'role': role})

    def payload(self, response):
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response['Cache-Control'], 'no-store')
        return jwt.decode(response.json()['access'], CHAVE_TESTE, algorithms=['HS256'])

    def test_aluno_recebe_somente_seu_vinculo_e_auditoria(self):
        response = self.emitir(self.aluno_user)
        dados = self.payload(response)
        self.assertEqual(dados['role'], 'aluno')
        self.assertEqual(dados['user_id'], str(self.aluno_user.pk))
        self.assertEqual(dados['aluno_id'], self.aluno.pk)
        self.assertEqual(dados['curso_id'], self.curso.pk)
        self.assertEqual(response.json()['expires_in'], 600)
        self.assertTrue(HistoricoAcao.objects.filter(ator=self.aluno_user, acao='TOKEN_MICROSSERVICO_EMITIDO').exists())
        self.assertEqual(self.emitir(self.aluno_user, 'admin').status_code, 403)

    def test_professor_staff_escolhe_papel_sem_virar_administrador(self):
        self.assertEqual(self.emitir(self.prof_user).status_code, 400)
        for role in ('orientador', 'coordenador'):
            dados = self.payload(self.emitir(self.prof_user, role))
            self.assertEqual(dados['role'], role)
            self.assertEqual(dados['professor_id'], self.prof.pk)
            self.assertEqual(dados['curso_ids'], [self.curso.pk] if role == 'coordenador' else [])
        self.assertEqual(self.emitir(self.prof_user, 'admin').status_code, 403)
        self.curso.coordenador = None
        self.curso.save(update_fields=['coordenador'])
        self.assertEqual(self.emitir(self.prof_user, 'coordenador').status_code, 403)

    def test_sem_vinculo_negado_e_admin_explicito_permitido(self):
        self.assertEqual(self.emitir(self.sem_perfil).status_code, 403)
        self.assertEqual(self.payload(self.emitir(self.admin))['role'], 'admin')

    @override_settings(SIMPLE_JWT={'ALGORITHM': 'HS256', 'SIGNING_KEY': '',
                                   'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10)})
    def test_sem_chave_nao_emite_token(self):
        self.assertEqual(self.emitir(self.aluno_user).status_code, 503)

    def test_csrf_e_sessao_obrigatorios(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/usuarios/token-microservico/').status_code, 403)
        client.force_login(self.aluno_user)
        self.assertEqual(client.post('/api/usuarios/token-microservico/').status_code, 403)
