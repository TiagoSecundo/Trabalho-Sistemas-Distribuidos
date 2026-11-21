"""Fluxos reais dos perfis; opt-in com RUN_BROWSER_TESTS=1."""
from datetime import timedelta
import os
from pathlib import Path
import shutil
from unittest import skipUnless

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from monografias.models import Banca, MembroExterno, Monografia, ParticipacaoBanca


@tag('browser')
@skipUnless(os.environ.get('RUN_BROWSER_TESTS') == '1', 'Teste de navegador opcional.')
class PerfisNavegadorTests(StaticLiveServerTestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        User = get_user_model()
        self.aluno_user = User.objects.create_user('aluno-browser', email='aluno@browser.example', password='senha-browser-123')
        self.prof_user = User.objects.create_user('prof-browser', email='prof@browser.example', password='senha-browser-123')
        self.admin_user = User.objects.create_superuser('admin-browser', email='admin@browser.example', password='senha-browser-123')
        self.aluno_user.groups.add(Group.objects.create(name='Alunos'))
        self.prof_user.groups.add(Group.objects.create(name='Professores'), Group.objects.create(name='Coordenadores'))
        for user in (self.aluno_user, self.prof_user, self.admin_user):
            EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=False)
        self.professor = Professor.objects.create(usuario=self.prof_user, nome='Ana Professora', email=self.prof_user.email, departamento='Computação', area_pesquisa='Sistemas distribuídos')
        self.curso = Curso.objects.create(nome='Sistemas de Informação', codigo='SI', coordenador=self.professor)
        self.aluno = Aluno.objects.create(usuario=self.aluno_user, nome='Lucas Aluno', email=self.aluno_user.email, matricula='2026001', curso=self.curso)
        # Estado preparado para testar o convite; aprovação não faz parte deste fluxo.
        self.trabalho = Monografia.objects.create(titulo='Gestão de monografias com Django', resumo='Estudo de uma aplicação acadêmica integrada.', palavras_chave=['Django', 'Educação'], aluno=self.aluno, curso=self.curso, orientador=self.professor, status_fluxo='APROVADA_ORIENTADOR')
        banca = Banca.objects.create(monografia=self.trabalho, inicio=timezone.now()+timedelta(days=7), fim=timezone.now()+timedelta(days=7, hours=1), local='Sala de defesas')
        externo = MembroExterno.objects.create(nome='Bruno Externo', email='externo@browser.example', instituicao='Instituto Parceiro')
        self.participacao = ParticipacaoBanca.objects.create(banca=banca, membro_externo=externo)
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser = self.playwright.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'), headless=True)
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page(viewport={'width': 1366, 'height': 960})
        self.page.set_default_timeout(15000)
        self.erros_js = []
        self.page.on('pageerror', lambda error: self.erros_js.append(str(error)))

    def abrir(self, path):
        self.page.goto(self.live_server_url + path)

    def entrar(self, username):
        self.page.context.clear_cookies()
        self.abrir('/accounts/login/')
        self.page.locator('#id_login').fill(username)
        self.page.locator('#id_password').fill('senha-browser-123')
        self.page.locator('form:has(#id_login) button[type=submit]').click()
        self.page.wait_for_url(self.live_server_url + '/usuarios/painel/')

    def screenshot(self, name):
        if destino := os.environ.get('BROWSER_ARTIFACTS'):
            Path(destino).mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(Path(destino) / name), full_page=True)

    def test_aluno_crud_api_busca_responsividade_e_logout(self):
        from playwright.sync_api import expect
        self.entrar('aluno-browser')
        expect(self.page.locator('h1')).to_have_text('Meu percurso acadêmico')
        self.screenshot('perfil-aluno-desktop.png')
        self.page.get_by_role('link', name='+ Novo rascunho').click()
        self.page.locator('#id_titulo').fill('Rascunho pelo navegador')
        self.page.locator('#id_resumo').fill('Resumo do novo trabalho.')
        self.page.locator('#id_palavras_chave').fill('API, Django')
        self.page.locator('#id_orientador').select_option(str(self.professor.pk))
        with self.page.expect_response(lambda r: '/api/usuarios/rascunhos/' in r.url and r.request.method == 'POST') as response:
            self.page.get_by_role('button', name='Salvar rascunho').click()
        self.assertEqual(response.value.status, 201)
        self.page.wait_for_url('**/usuarios/trabalhos/*/')
        expect(self.page.locator('h1')).to_have_text('Rascunho pelo navegador')
        self.page.get_by_role('link', name='Editar rascunho', exact=True).click()
        self.page.locator('#id_titulo').fill('Rascunho revisado')
        with self.page.expect_response(lambda r: r.request.method == 'PATCH') as response:
            self.page.get_by_role('button', name='Salvar rascunho').click()
        self.assertEqual(response.value.status, 200)
        self.page.wait_for_url('**/usuarios/trabalhos/*/')
        expect(self.page.locator('h1')).to_have_text('Rascunho revisado')
        self.abrir('/usuarios/painel/aluno/')
        self.page.locator('#busca-perfil').fill('revisado')
        self.page.get_by_role('button', name='Filtrar').click()
        expect(self.page.locator('.perfil-work-list')).to_contain_text('Rascunho revisado')
        expect(self.page.locator('.perfil-work-list')).not_to_contain_text(self.trabalho.titulo)
        self.page.get_by_role('link', name='Ver trabalho →').click()
        self.page.get_by_role('link', name='Excluir rascunho', exact=True).click()
        with self.page.expect_response(lambda r: r.request.method == 'DELETE') as response:
            self.page.get_by_role('button', name='Confirmar exclusão').click()
        self.assertEqual(response.value.status, 204)
        self.page.wait_for_url('**/usuarios/painel/aluno/')
        trabalhos = self.page.request.get(self.live_server_url + '/api/usuarios/rascunhos/').json()['results']
        self.assertFalse(any(item['titulo'] == 'Rascunho revisado' for item in trabalhos))
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.screenshot('perfil-aluno-mobile.png')
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
        self.page.get_by_role('button', name='Alternar navegação').click()
        self.page.get_by_role('button', name='Sair', exact=True).click()
        self.page.wait_for_url(self.live_server_url + '/')
        self.abrir('/usuarios/painel/')
        self.assertIn('/accounts/login/', self.page.url)
        self.assertEqual(self.erros_js, [])

    def test_professor_coordenador_convite_e_administrador(self):
        from playwright.sync_api import expect
        self.entrar('prof-browser')
        expect(self.page.locator('h1')).to_have_text('Coordenação acadêmica')
        self.screenshot('perfil-coordenador-desktop.png')
        self.page.get_by_role('navigation', name='Seus perfis').get_by_role('link', name='Professor', exact=True).click()
        expect(self.page.locator('h1')).to_have_text('Orientações e coorientações')
        self.screenshot('perfil-professor-desktop.png')
        self.abrir(f'/usuarios/trabalhos/{self.trabalho.pk}/')
        self.page.get_by_role('link', name='Preparar convite').click()
        self.page.get_by_role('button', name='Gerar convite', exact=True).click()
        token = self.page.locator('#codigo-convite').input_value()
        url = self.page.locator('#endereco-convite').input_value()
        self.assertNotIn(token, url)
        self.page.context.clear_cookies()
        self.page.goto(url)
        self.page.locator('#id_token').fill(token)
        self.page.get_by_role('button', name='Confirmar minha participação').click()
        expect(self.page.get_by_role('status')).to_contain_text('Participação confirmada com sucesso')
        self.entrar('admin-browser')
        participacao = self.page.request.get(self.live_server_url + f'/api/participacoes-banca/{self.participacao.pk}/').json()
        self.assertEqual(participacao['convite_status'], 'CONFIRMADO')
        expect(self.page.locator('h1')).to_have_text('Gestão acadêmica')
        expect(self.page.get_by_role('link', name='Contas e acessos', exact=False)).to_be_visible()
        self.screenshot('perfil-administrador-desktop.png')
        self.assertEqual(self.erros_js, [])
