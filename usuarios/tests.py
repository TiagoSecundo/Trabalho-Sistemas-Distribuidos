from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from equipe.models import Aluno, Professor, Curso
from monografias.models import Monografia


class AutenticacaoTests(TestCase):

    def setUp(self):
        User = get_user_model()

        self.usuario1 = User.objects.create_user(
            username='aluno1',
            password='SenhaTeste123!'
        )

        self.usuario2 = User.objects.create_user(
            username='aluno2',
            password='SenhaTeste123!'
        )

        grupo = Group.objects.create(name='Alunos')

        self.usuario1.groups.add(grupo)
        self.usuario2.groups.add(grupo)

        self.curso = Curso.objects.create(
            nome='Sistemas de Informação',
            codigo='SI'
        )

        self.professor = Professor.objects.create(
            nome='Professor Teste',
            email='professor@exemplo.com',
            departamento='Computação',
            area_pesquisa='Software'
        )

        self.aluno1 = Aluno.objects.create(
            usuario=self.usuario1,
            nome='Aluno Um',
            matricula='001',
            email='aluno1@exemplo.com',
            curso=self.curso
        )

        self.aluno2 = Aluno.objects.create(
            usuario=self.usuario2,
            nome='Aluno Dois',
            matricula='002',
            email='aluno2@exemplo.com',
            curso=self.curso
        )

        self.monografia = Monografia.objects.create(
            titulo='Monografia do Aluno Um',
            resumo='Trabalho de teste',
            aluno=self.aluno1,
            curso=self.curso,
            orientador=self.professor
        )

    def test_usuario_nao_autenticado(self):
        response = self.client.get('/api/usuarios/me/')

        self.assertIn(response.status_code, [401, 403])

    def test_aluno_visualiza_somente_sua_monografia(self):
        self.client.force_login(self.usuario2)

        response = self.client.get(
            '/api/usuarios/monografias/'
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()['count'],
            0
        )

    def test_aluno_nao_acessa_crud_administrativo(self):
        self.client.force_login(self.usuario1)

        response = self.client.get('/api/alunos/')

        self.assertEqual(response.status_code, 403)