"""Integração real do navegador; opt-in com RUN_BROWSER_TESTS=1."""
import json
import os
from pathlib import Path
import re
import shutil
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag

from equipe.models import Professor
from usuarios.browser_helpers import banco


@tag('browser')
@skipUnless(os.environ.get('RUN_BROWSER_TESTS') == '1', 'Teste de navegador opcional; consulte docs/DESENVOLVIMENTO.md.')
class NavegadorTests(StaticLiveServerTestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright

        get_user_model().objects.create_user('gestor-browser', password='senha-de-teste-browser', is_staff=True, is_superuser=True)
        Professor.objects.bulk_create([
            Professor(nome=f'Professor de apoio {i:02}', email=f'apoio{i}@example.com', departamento='Computação', area_pesquisa='Redes')
            for i in range(22)
        ])
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        executable = shutil.which('google-chrome') or shutil.which('chromium')
        self.browser = self.playwright.chromium.launch(executable_path=executable, headless=True)
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page(viewport={'width': 1366, 'height': 900})
        self.page.set_default_timeout(15000)
        self.erros_js = []
        self.page.on('pageerror', lambda error: self.erros_js.append(str(error)))

    def abrir(self, path):
        self.page.goto(self.live_server_url + path)

    def entrar(self):
        self.abrir('/entrar/')
        self.page.locator('#id_login').fill('gestor-browser')
        self.page.locator('#id_password').fill('senha-de-teste-browser')
        self.page.get_by_role('button', name='Entrar', exact=True).click()
        self.page.wait_for_url(self.live_server_url + '/usuarios/painel/')

    def preencher(self, campos):
        for campo, valor in campos.items():
            control = self.page.locator(f'#id_{campo}')
            if control.evaluate('(el) => el.tagName') == 'SELECT':
                control.select_option(str(valor))
            else:
                control.fill(str(valor))

    def enviar(self, method, status):
        config = json.loads(self.page.locator('#crud-config').text_content())
        with self.page.expect_response(lambda response: '/api/' in response.url and response.request.method == method) as pending:
            self.page.get_by_role('button', name=re.compile('^Salvar')).click()
        response = pending.value
        self.assertEqual(response.status, status)
        if status >= 400:
            return response.json()
        if method == 'PATCH':
            self.page.wait_for_url(self.live_server_url + config['detalhes'].replace('/0/', f"/{config['id']}/"))
        else:
            self.page.wait_for_url(re.compile(r'/\d+/$'))
        # O redirect pode liberar o corpo da resposta POST no Chrome. Confira
        # o registro persistido pelo endpoint de detalhe na mesma sessão.
        salvo = json.loads(self.page.locator('#crud-config').text_content())
        return self.page.request.get(self.live_server_url + salvo['endpoint'] + str(salvo['id']) + '/').json()

    def cadastrar(self, path, campos):
        from playwright.sync_api import expect

        self.abrir(path)
        config = json.loads(self.page.locator('#crud-config').text_content())
        self.preencher(campos)
        dados = self.enviar('POST', 201)
        config['id'] = dados['id']
        expect(self.page).to_have_url(self.live_server_url + config['detalhes'].replace('/0/', f"/{dados['id']}/"))
        expect(self.page.locator('[data-api-status]')).to_have_text('')
        return config

    def editar(self, config, campo, valor):
        from playwright.sync_api import expect

        self.abrir(config['editar'].replace('/0/', f"/{config['id']}/"))
        self.preencher({campo: valor})
        dados = self.enviar('PATCH', 200)
        self.assertEqual(str(dados[campo]), str(valor))
        expect(self.page).to_have_url(self.live_server_url + config['detalhes'].replace('/0/', f"/{config['id']}/"))

    def screenshot(self, nome):
        destino = os.environ.get('BROWSER_ARTIFACTS')
        if destino:
            Path(destino).mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(Path(destino) / nome), full_page=True)

    def test_crud_cadastral_e_consulta_academica_com_busca_e_paginacao(self):
        from playwright.sync_api import expect

        self.entrar()
        professor = self.cadastrar('/equipe/adicionar/?tipo=professor', {'nome': 'Ana Orientadora', 'email': 'ana@example.com', 'departamento': 'Computação', 'area_pesquisa': 'Sistemas distribuídos'})
        self.editar(professor, 'area_pesquisa', 'Engenharia de software')
        curso = self.cadastrar('/equipe/adicionar/?tipo=curso', {'nome': 'Ciência da Computação', 'codigo': 'CC', 'coordenador': professor['id']})
        self.editar(curso, 'codigo', 'COMP')
        aluno = self.cadastrar('/equipe/adicionar/?tipo=aluno', {'nome': 'Carla Silva', 'matricula': '2026001', 'email': 'carla@example.com', 'curso': curso['id'], 'orientador_atual': professor['id']})
        self.editar(aluno, 'nome', 'Carla Souza')
        externo = self.cadastrar('/monografias/membros-externos/adicionar/', {'nome': 'Bruno Avaliador', 'email': 'bruno@example.com', 'instituicao': 'Universidade Parceira'})
        self.editar(externo, 'instituicao', 'Instituto de Pesquisa')
        from monografias.models import Monografia
        trabalho = banco(lambda: Monografia.objects.create(titulo='Consulta acadêmica', resumo='Resumo',
            aluno_id=aluno['id'], curso_id=curso['id'], orientador_id=professor['id']))
        self.abrir('/monografias/')
        expect(self.page.locator('[data-count]')).to_contain_text('1 registro(s)')
        expect(self.page.get_by_role('link', name='Adicionar monografia')).to_have_count(0)
        expect(self.page.locator('[data-rows]').get_by_role('link', name='Editar')).to_have_count(0)
        self.assertEqual(self.page.request.post(self.live_server_url + '/api/monografias/', data={}).status, 403)
        self.abrir('/equipe/?tipo=professor')
        expect(self.page.locator('[data-count]')).to_contain_text('23 registro(s)')
        self.page.get_by_role('button', name='Próxima', exact=True).click()
        expect(self.page.locator('[data-count]')).to_contain_text('Página 2')
        self.page.locator('#busca').fill('Ana Orientadora')
        self.page.get_by_role('button', name='Buscar', exact=True).click()
        expect(self.page.locator('[data-count]')).to_contain_text('1 registro(s)')
        expect(self.page.locator('[data-rows]')).to_contain_text('Ana Orientadora')
        self.page.locator('#busca').fill('Nenhumresultado')
        self.page.get_by_role('button', name='Buscar', exact=True).click()
        expect(self.page.locator('[data-rows]')).to_contain_text('Nenhum registro encontrado')

        self.abrir('/monografias/')
        expect(self.page.locator('[data-count]')).to_contain_text('1 registro(s)')
        self.screenshot('monografias-desktop.png')
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.screenshot('monografias-mobile.png')
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        self.page.get_by_role('button', name='Alternar navegação').click()
        expect(self.page.get_by_role('button', name='Sair', exact=True)).to_be_visible()
        self.page.set_viewport_size({'width': 1366, 'height': 900})

        # Exclusão em ordem inversa das dependências, pela interface e pela API.
        banco(trabalho.delete)  # Remove apenas a fixture criada diretamente por este teste.
        for config in (externo, aluno, curso, professor):
            self.abrir(config['excluir'].replace('/0/', f"/{config['id']}/"))
            with self.page.expect_response(lambda response: response.request.method == 'DELETE') as pending:
                self.page.get_by_role('button', name='Confirmar exclusão').click()
            self.assertEqual(pending.value.status, 204)
            expect(self.page).to_have_url(self.live_server_url + config['lista'])
            result = self.page.request.get(self.live_server_url + config['endpoint'] + str(config['id']) + '/')
            self.assertEqual(result.status, 404)
        self.assertEqual(self.erros_js, [])

    def test_sessao_expirada_xss_e_falha_de_rede(self):
        from playwright.sync_api import expect

        self.entrar()
        self.abrir('/equipe/adicionar/?tipo=curso')
        self.preencher({'nome': '<img src=x onerror="window.injetado=true">', 'codigo': 'XSS'})
        self.enviar('POST', 201)
        self.page.wait_for_url(re.compile(r'/equipe/curso/\d+/$'))
        expect(self.page.locator('[data-values]')).to_contain_text('<img src=x')
        self.assertIsNone(self.page.evaluate('window.injetado'))
        self.assertEqual(self.page.locator('[data-values] img').count(), 0)
        self.abrir('/equipe/adicionar/?tipo=curso')
        self.preencher({'nome': 'Sessão expirada', 'codigo': 'EXP'})
        self.page.context.clear_cookies()
        self.enviar('POST', 403)
        expect(self.page.locator('[data-api-error]')).to_contain_text('sessão inválida')
        expect(self.page.locator('[data-api-login]')).to_be_visible()
        expect(self.page.locator('#id_nome')).to_have_value('Sessão expirada')
        self.entrar()
        self.page.route('**/api/cursos/**', lambda route: route.abort())
        self.abrir('/equipe/?tipo=curso')
        expect(self.page.locator('[data-api-error]')).to_contain_text('Verifique a conexão')
        expect(self.page.locator('[data-retry]')).to_be_visible()
        self.page.unroute('**/api/cursos/**')
        self.page.get_by_role('button', name='Tentar novamente').click()
        expect(self.page.locator('[data-count]')).to_contain_text('1 registro(s)')
        self.abrir('/')
        self.screenshot('inicio-desktop.png')
        self.assertEqual(self.erros_js, [])
