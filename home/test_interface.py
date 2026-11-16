from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from equipe.interface import recurso as recurso_equipe
from equipe.models import Aluno, Curso, Professor
from monografias.interface import RECURSOS, recurso as recurso_monografias
from monografias.models import Banca, Monografia


class InterfaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user('gestor', password='teste-seguro', is_staff=True)
        cls.comum = get_user_model().objects.create_user('comum', password='teste-seguro')
        cls.professor = Professor.objects.create(nome='Ana', email='ana@example.com', departamento='Computação', area_pesquisa='Redes')
        cls.curso = Curso.objects.create(nome='Computação', codigo='CC', coordenador=cls.professor)
        cls.aluno = Aluno.objects.create(nome='Carla', email='carla@example.com', matricula='001', curso=cls.curso)
        cls.monografia = Monografia.objects.create(titulo='Estudo de APIs', resumo='Resumo', aluno=cls.aluno, curso=cls.curso, orientador=cls.professor)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_pagina_inicial_explicita_dominio_e_login(self):
        self.client.logout()
        response = self.client.get('/')
        self.assertContains(response, 'Monografias, orientações e bancas')
        self.assertContains(response, '/entrar/')

    def test_todos_recursos_tem_formulario_lista_e_configuracao_da_api(self):
        configs = [recurso_equipe(tipo) for tipo in ('aluno', 'professor', 'curso')]
        configs += [recurso_monografias(tipo) for tipo in RECURSOS]
        for config in configs:
            for url in (config['lista_url'], config['adicionar_url']):
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'id="crud-config"')
                    self.assertContains(response, 'home/crud.js')
                    self.assertEqual(response.context['api_config']['colunas'], config['colunas'])
                    self.client.logout()
                    self.assertEqual(self.client.get(url).status_code, 302)
                    self.client.force_login(self.admin)

    def test_rota_desconhecida_e_id_inexistente(self):
        for url in ('/equipe/?tipo=usuario', '/equipe/curso/9999/', '/monografias/segredos/', '/monografias/bancas/9999/'):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_login_staff_redirect_seguro_e_saida_post(self):
        self.client.logout()
        response = self.client.post('/entrar/?next=/monografias/bancas/', {'username': 'gestor', 'password': 'teste-seguro'})
        self.assertRedirects(response, '/monografias/bancas/')
        self.assertEqual(self.client.get('/sair/').status_code, 405)
        self.assertRedirects(self.client.post('/sair/'), '/')
        response = self.client.post('/entrar/?next=https://example.com/', {'username': 'gestor', 'password': 'teste-seguro'})
        self.assertRedirects(response, '/monografias/')
        self.client.logout()
        response = self.client.post('/entrar/', {'username': 'comum', 'password': 'teste-seguro'})
        self.assertContains(response, 'Esta área exige uma conta administrativa')
        self.assertEqual(self.client.get('/monografias/').status_code, 302)

    def test_formulario_crud_curso_e_exclusao_protegida(self):
        response = self.client.post('/equipe/adicionar/?tipo=curso', {'nome': 'Engenharia', 'codigo': 'ENG', 'coordenador': self.professor.pk})
        curso = Curso.objects.get(codigo='ENG')
        self.assertRedirects(response, f'/equipe/curso/{curso.pk}/')
        response = self.client.post(f'/equipe/curso/{curso.pk}/editar/', {'nome': 'Engenharia de Software', 'codigo': 'ENG', 'coordenador': ''})
        self.assertEqual(response.status_code, 302)
        curso.refresh_from_db()
        self.assertIsNone(curso.coordenador)
        self.assertEqual(self.client.post(f'/equipe/curso/{curso.pk}/excluir/').status_code, 302)
        self.assertEqual(self.client.post(f'/equipe/curso/{self.curso.pk}/excluir/').status_code, 409)
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())

    def test_servico_aplica_mesmo_bloqueio_na_api_e_no_html(self):
        self.monografia.status_fluxo = 'PUBLICADA'
        self.monografia.save()
        self.assertEqual(self.client.get(f'/monografias/editar/{self.monografia.pk}/').status_code, 409)
        self.assertEqual(self.client.post(f'/monografias/excluir/{self.monografia.pk}/').status_code, 409)
        self.assertEqual(self.client.patch(f'/api/monografias/{self.monografia.pk}/', {'titulo': 'Alteração indevida'}, content_type='application/json').status_code, 409)
        self.monografia.refresh_from_db()
        self.assertEqual(self.monografia.titulo, 'Estudo de APIs')

    def test_formulario_banca_horario_local_e_validacao(self):
        inicio = (timezone.localtime() + timedelta(days=7)).replace(second=0, microsecond=0)
        payload = {'monografia': self.monografia.pk, 'inicio': inicio.strftime('%Y-%m-%dT%H:%M'), 'fim': (inicio + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'), 'modalidade': 'REMOTA', 'link': ''}
        response = self.client.post('/monografias/bancas/adicionar/', payload)
        self.assertTrue(response.context['form'].errors)
        payload['link'] = 'https://example.com/reuniao'
        self.assertEqual(self.client.post('/monografias/bancas/adicionar/', payload).status_code, 302)
        self.assertEqual(Banca.objects.get().inicio, inicio)

    def test_nomes_de_relacoes_sao_leitura_e_nao_geram_n_mais_um(self):
        for i in range(5):
            Monografia.objects.create(titulo=f'Trabalho {i}', resumo='Resumo', aluno=self.aluno, curso=self.curso, orientador=self.professor)
        # Sessão + usuário + count + consulta com select_related.
        with self.assertNumQueries(4):
            response = self.client.get('/api/monografias/')
        self.assertEqual(response.json()['results'][0]['aluno_nome'], 'Carla')
        response = self.client.patch(f'/api/monografias/{self.monografia.pk}/', {'aluno_nome': 'Nome falso'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_csrf_da_tela_autoriza_json_e_exige_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.get('/equipe/adicionar/?tipo=curso').status_code, 200)
        payload = {'nome': 'Curso da interface', 'codigo': 'UI'}
        self.assertEqual(client.post('/api/cursos/', payload, content_type='application/json').status_code, 403)
        self.assertEqual(client.post('/api/cursos/', payload, content_type='application/json', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code, 201)

    def test_sessao_expirada_no_fetch_nao_dispara_dialogo_http_basic(self):
        self.client.logout()
        response = self.client.get('/api/cursos/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('WWW-Authenticate', response)
        response = self.client.get('/api/cursos/')
        self.assertEqual(response.status_code, 401)
        self.assertTrue(response['WWW-Authenticate'].startswith('Basic'))

    def test_opcoes_de_relacionamentos_incluem_alem_da_primeira_pagina(self):
        Professor.objects.bulk_create([Professor(nome=f'Professor {i}', email=f'p{i}@example.com', departamento='D', area_pesquisa='A') for i in range(25)])
        response = self.client.get('/equipe/adicionar/?tipo=curso')
        self.assertEqual(response.context['form'].fields['coordenador'].queryset.count(), 26)
        self.assertContains(response, 'Professor 24')
