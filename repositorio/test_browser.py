import os
from pathlib import Path
import shutil
from unittest import skipUnless

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag

from monografias.models import Monografia
from .indexacao import dados_evento, indexar_evento
from .test_helpers import CenarioRepositorio


@tag('browser')
@skipUnless(os.environ.get('RUN_BROWSER_TESTS') == '1', 'Requer Chrome e Playwright.')
class RepositorioBrowserTests(CenarioRepositorio, StaticLiveServerTestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        self.preparar_cenario(); self.arquivos_temporarios()
        self.p=self.publicar_trabalho('Arquiteturas de sistemas distribuídos para a educação')
        indexar_evento(dados_evento(self.p.evento_indexacao))
        for i in range(12): self.publicar_trabalho(f'Pesquisa acadêmica {i:02d}: serviços digitais e inovação')
        self.segredo=Monografia.objects.create(titulo='Trabalho confidencial',resumo='Privado',aluno=self.aluno,curso=self.curso,orientador=self.orientador)
        self.playwright=sync_playwright().start(); self.addCleanup(self.playwright.stop)
        self.browser=self.playwright.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True)
        self.addCleanup(self.browser.close)
        self.page=self.browser.new_page(viewport={'width':1440,'height':1000})
        self.page.set_default_timeout(15000)
        self.erros=[]; self.page.on('pageerror',lambda error:self.erros.append(str(error)))

    def foto(self,name):
        if destino:=os.environ.get('BROWSER_ARTIFACTS'):
            Path(destino).mkdir(parents=True,exist_ok=True)
            self.page.screenshot(path=str(Path(destino)/name),full_page=True)

    def test_visitante_pesquisa_seis_filtros_detalhe_download_historico_e_mobile(self):
        from playwright.sync_api import expect
        self.page.goto(self.live_server_url+'/')
        self.page.get_by_role('link',name='Explorar o repositório').click()
        expect(self.page.locator('#contagem')).to_have_text('13 trabalhos encontrados')
        self.foto('b13-catalogo-desktop.png')
        self.page.get_by_role('button',name='Próxima →').click()
        expect(self.page.locator('[data-pagina]')).to_have_text('Página 2 de 2')
        self.page.go_back(); expect(self.page.locator('[data-pagina]')).to_have_text('Página 1 de 2')
        self.page.locator('#titulo').fill('Arquiteturas')
        self.page.locator('#autor').fill('Aluno B12')
        self.page.locator('#curso').select_option(str(self.curso.pk))
        self.page.locator('#orientador').select_option(str(self.orientador.pk))
        self.page.locator('#ano_defesa').fill('2024')
        self.page.locator('#palavras_chave').fill('redes, distribuídos')
        self.page.get_by_role('button',name='Aplicar filtros',exact=True).click()
        expect(self.page.locator('#contagem')).to_have_text('1 trabalho encontrado')
        self.assertIn('ano_defesa=2024',self.page.url)
        self.page.reload(); expect(self.page.locator('#contagem')).to_have_text('1 trabalho encontrado')
        self.page.get_by_role('link',name='Ver trabalho →').click()
        expect(self.page.get_by_role('heading',name=self.p.monografia.titulo)).to_be_visible()
        expect(self.page.locator('[data-api-detalhe]')).to_have_attribute('data-api-confirmada','true')
        self.assertEqual(self.page.locator('text=Termo privado').count(),0)
        with self.page.expect_download() as download:
            self.page.get_by_role('link',name='Baixar PDF',exact=True).click()
        import hashlib
        self.assertEqual(hashlib.sha256(Path(download.value.path()).read_bytes()).hexdigest(),self.p.sha256)
        self.foto('b13-detalhe-desktop.png')
        self.page.set_viewport_size({'width':390,'height':844})
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))
        self.foto('b13-detalhe-mobile.png')
        self.page.get_by_role('link',name='← Explorar o repositório').click()
        expect(self.page.locator('#contagem')).to_have_text('13 trabalhos encontrados')
        self.page.locator('#busca').fill('hiperconvergencia')
        self.page.get_by_role('button',name='Pesquisar',exact=False).click()
        expect(self.page.locator('#contagem')).to_have_text('1 trabalho encontrado')
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > innerWidth'))
        self.foto('b13-catalogo-mobile.png')
        self.assertEqual(self.page.request.get(self.live_server_url+f'/repositorio/{self.segredo.pk}/').status,404)
        self.assertEqual(self.erros,[])

    def test_vazio_falha_retentativa_e_escape_de_html(self):
        from playwright.sync_api import expect
        self.page.goto(self.live_server_url+'/repositorio/?busca=inexistente')
        expect(self.page.get_by_role('heading',name='Nenhum trabalho encontrado')).to_be_visible()
        self.page.get_by_role('button',name='Ver todos os trabalhos').click()
        expect(self.page.locator('#contagem')).to_have_text('13 trabalhos encontrados')
        self.page.route('**/api/publico/cursos/',lambda route:route.abort())
        self.page.reload()
        expect(self.page.locator('[data-opcoes-erro]')).to_be_visible()
        expect(self.page.locator('#contagem')).to_have_text('13 trabalhos encontrados')
        self.page.unroute('**/api/publico/cursos/')
        self.page.get_by_role('button',name='Recarregar opções').click()
        expect(self.page.locator('[data-opcoes-erro]')).to_be_hidden()
        expect(self.page.locator('#curso option')).to_have_count(2)
        self.page.route('**/api/publico/monografias/**',lambda route:route.abort())
        self.page.locator('#busca').fill('Arquiteturas')
        self.page.get_by_role('button',name='Pesquisar',exact=False).click()
        expect(self.page.get_by_role('alert')).to_be_visible()
        self.page.unroute('**/api/publico/monografias/**')
        self.page.get_by_role('button',name='Tentar novamente').click()
        expect(self.page.locator('#contagem')).to_have_text('1 trabalho encontrado')
        self.page.route('**/api/publico/monografias/**',lambda route:route.fulfill(json={
            'count':1,'page':1,'pages':1,'next':None,'previous':None,'results':[{
                'titulo':'<img src=x onerror=alert(1)>','resumo':'<script>alert(1)</script>',
                'autor':'Aluno','orientador':{'nome':'Professor'},'curso':{'nome':'Computação'},
                'ano_defesa':2024,'palavras_chave':['<b>texto</b>'],'url':'/repositorio/1/',
            }]}))
        self.page.get_by_role('button',name='Pesquisar',exact=False).click()
        expect(self.page.locator('.repo-card h3')).to_have_text('<img src=x onerror=alert(1)>')
        self.assertEqual(self.page.locator('.repo-card img, .repo-card script').count(),0)
        self.assertEqual(self.erros,[])
