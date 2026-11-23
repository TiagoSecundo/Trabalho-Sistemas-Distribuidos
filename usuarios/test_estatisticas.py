from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from equipe.models import Aluno, Curso, Professor
from monografias.models import Banca, Monografia


INDICADORES = ('por-curso', 'por-orientador', 'por-ano-defesa', 'taxa-aprovacao', 'tempo-medio')
SUBMISSAO = datetime(2024, 12, 21, 2, tzinfo=timezone.utc)
DEFESA = datetime(2025, 1, 1, 2, tzinfo=timezone.utc)


class EstatisticasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        usuarios = get_user_model().objects
        cls.admin = usuarios.create_user('gestora')
        cls.admin.groups.add(Group.objects.get_or_create(name='Administradores')[0])
        cls.coordenador = usuarios.create_user('coordenador')
        cls.professor = usuarios.create_user('orientador')
        cls.usuario_aluno = usuarios.create_user('aluno')
        coordenador = Professor.objects.create(
            nome='Coordenador', email='coord@example.com', usuario=cls.coordenador,
        )
        cls.orientador = Professor.objects.create(
            nome='Orientador', email='orientador@example.com', usuario=cls.professor,
        )
        cls.curso = Curso.objects.create(nome='Computação', codigo='CC', coordenador=coordenador)
        cls.outro_curso = Curso.objects.create(nome='Design', codigo='DS')
        cls.aluno = Aluno.objects.create(
            nome='Aluno', matricula='01', curso=cls.curso, usuario=cls.usuario_aluno,
        )
        cls.outro_aluno = Aluno.objects.create(nome='Outro aluno', matricula='02', curso=cls.outro_curso)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def monografia(self, estado, aluno=None, submissao=SUBMISSAO, orientador=None):
        aluno = aluno or self.aluno
        return Monografia.objects.create(
            titulo='Monografia', aluno=aluno, curso=aluno.curso,
            orientador=orientador or self.orientador, status_fluxo=estado, data_submissao=submissao,
        )

    def banca(self, trabalho, inicio=DEFESA, estado='REALIZADA'):
        return Banca.objects.create(
            monografia=trabalho, inicio=inicio, fim=inicio + timedelta(hours=1), status=estado,
        )

    def url(self, indicador):
        return reverse(f'api-estatisticas-{indicador}')

    def obter(self, indicador, **filtros):
        resposta = self.api.get(self.url(indicador), filtros)
        self.assertEqual(resposta.status_code, 200, resposta.content)
        return resposta.json()

    def test_contagens_submetidas_por_curso_e_orientador(self):
        homonimo = Professor.objects.create(nome=self.orientador.nome, email='homonimo@example.com')
        trabalho = self.monografia('APROVADA')
        self.banca(trabalho)
        self.banca(trabalho, DEFESA + timedelta(days=5))
        self.monografia('REPROVADA', orientador=homonimo)
        self.monografia('SUBMETIDA', aluno=self.outro_aluno)
        self.monografia('RASCUNHO', submissao=None)
        self.assertEqual(self.obter('por-curso'), [
            {'grupo_id': self.curso.pk, 'rotulo': self.curso.nome, 'total': 2},
            {'grupo_id': self.outro_curso.pk, 'rotulo': self.outro_curso.nome, 'total': 1},
        ])
        self.assertEqual(self.obter('por-orientador'), [
            {'grupo_id': self.orientador.pk, 'rotulo': self.orientador.nome, 'total': 2},
            {'grupo_id': homonimo.pk, 'rotulo': homonimo.nome, 'total': 1},
        ])

    def test_ano_local_e_banca_realizada_mais_recente(self):
        trabalho = self.monografia('DEFESA_REALIZADA')
        self.banca(trabalho, DEFESA - timedelta(days=365))
        self.banca(trabalho)
        self.banca(trabalho, DEFESA + timedelta(days=10), 'CANCELADA')
        self.banca(self.monografia('BANCA_AGENDADA'), DEFESA, 'AGENDADA')
        self.banca(self.monografia('DEFESA_REALIZADA'), DEFESA + timedelta(hours=2))
        self.assertEqual(self.obter('por-ano-defesa'), [
            {'ano': 2024, 'total': 1}, {'ano': 2025, 'total': 1},
        ])

    def test_taxa_com_resultados_finais_e_estados_posteriores(self):
        for estado in ('APROVADA', 'APROVADA_COM_RESSALVAS', 'CORRECOES_ENTREGUES', 'PUBLICADA', 'REPROVADA'):
            trabalho = self.monografia(estado)
            self.banca(trabalho)
            self.banca(trabalho, DEFESA + timedelta(days=1))
        self.banca(self.monografia('DEFESA_REALIZADA'))
        self.banca(self.monografia('APROVADA_ORIENTADOR'))
        self.banca(self.monografia('REPROVADA'), estado='CANCELADA')
        self.assertEqual(self.obter('taxa-aprovacao'), {
            'aprovadas': 4, 'reprovadas': 1, 'total': 5, 'percentual': 80.0,
        })

    def test_media_usa_ultima_defesa_e_ignora_intervalos_invalidos(self):
        trabalho = self.monografia('DEFESA_REALIZADA')
        self.banca(trabalho, DEFESA - timedelta(days=5))
        self.banca(trabalho)
        self.banca(trabalho, DEFESA + timedelta(days=30), 'CANCELADA')
        self.banca(self.monografia('APROVADA', submissao=DEFESA - timedelta(hours=12)))
        self.banca(self.monografia('APROVADA', submissao=DEFESA + timedelta(days=1)))
        self.banca(self.monografia('APROVADA', submissao=None))
        self.assertEqual(self.obter('tempo-medio'), {'total': 2, 'dias': 5.75})

    def test_respostas_sem_dados(self):
        for indicador in INDICADORES[:3]:
            self.assertEqual(self.obter(indicador), [])
        self.assertEqual(self.obter('taxa-aprovacao'), {
            'aprovadas': 0, 'reprovadas': 0, 'total': 0, 'percentual': None,
        })
        self.assertEqual(self.obter('tempo-medio'), {'total': 0, 'dias': None})

    def test_filtro_e_escopo_aplicados_em_todos_os_indicadores(self):
        self.banca(self.monografia('APROVADA'))
        outro_orientador = Professor.objects.create(
            nome='Outro orientador', email='outro-orientador@example.com',
        )
        outro_trabalho = self.monografia(
            'REPROVADA', aluno=self.outro_aluno, orientador=outro_orientador,
            submissao=DEFESA - timedelta(days=2),
        )
        self.banca(outro_trabalho, DEFESA + timedelta(days=1))
        for indicador in INDICADORES:
            with self.subTest(indicador=indicador):
                self.api.force_authenticate(self.admin)
                somente_curso = self.obter(indicador, curso=self.curso.pk)
                self.assertNotEqual(somente_curso, self.obter(indicador))
                self.assertNotEqual(somente_curso, self.obter(indicador, curso=self.outro_curso.pk))
                self.assertEqual(self.api.get(self.url(indicador), {'curso': 'inválido'}).status_code, 400)
                self.api.force_authenticate(self.coordenador)
                self.assertEqual(self.obter(indicador), somente_curso)
                self.assertEqual(self.obter(indicador, curso=self.curso.pk), somente_curso)
                fora = self.api.get(self.url(indicador), {'curso': self.outro_curso.pk})
                inexistente = self.api.get(self.url(indicador), {'curso': self.outro_curso.pk + 100})
                self.assertEqual(fora.status_code, 404)
                self.assertEqual(fora.json(), inexistente.json())

    def test_permissoes_da_pagina_e_api(self):
        pagina = reverse('usuarios:estatisticas')
        for usuario in (None, self.professor, self.usuario_aluno):
            with self.subTest(usuario=usuario):
                self.api.force_authenticate(usuario)
                for indicador in INDICADORES:
                    self.assertIn(self.api.get(self.url(indicador)).status_code, (401, 403))
                if usuario is None:
                    self.client.logout()
                else:
                    self.client.force_login(usuario)
                self.assertEqual(self.client.get(pagina).status_code, 302 if usuario is None else 403)
        self.client.force_login(self.coordenador)
        resposta = self.client.get(pagina)
        self.assertContains(resposta, 'data-indicador=', count=5)
        self.assertContains(resposta, 'chart.umd.js')
        self.assertContains(resposta, self.curso.nome)
        self.assertNotContains(resposta, self.outro_curso.nome)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(pagina), self.outro_curso.nome)

    def test_endpoints_somente_leitura(self):
        for indicador in INDICADORES:
            for metodo in ('POST', 'PUT', 'PATCH', 'DELETE'):
                with self.subTest(indicador=indicador, metodo=metodo):
                    self.assertEqual(self.api.generic(metodo, self.url(indicador)).status_code, 405)
