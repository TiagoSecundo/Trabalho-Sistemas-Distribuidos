"""B12 no Chrome com contas, sessões e banco isolado; opt-in RUN_BROWSER_TESTS=1.

O transporte do PDF original é simulado aqui; este teste não comprova o
microserviço externo. As requisições HTML e as persistências são reais.
"""
import os
from pathlib import Path
import shutil
from unittest import skipUnless
from types import SimpleNamespace

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag

from .test_publicacao import CenarioPublicacao, ORIGINAL, conteudo_pdf


@tag('browser')
@override_settings(ACCOUNT_RATE_LIMITS=False)
@skipUnless(os.environ.get('RUN_BROWSER_TESTS') == '1', 'Teste Chrome opcional.')
class PublicacaoNavegadorTests(CenarioPublicacao, StaticLiveServerTestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        self.preparar_cenario()
        self.arquivos_temporarios()
        self.sem_ressalvas = self.trabalho()
        self.com_ressalvas = self.trabalho('APROVADA_COM_RESSALVAS')
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser = self.playwright.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'), headless=True)
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page(viewport={'width': 1366, 'height': 900})
        self.page.set_default_timeout(15000)
        self.erros_js = []
        self.page.on('pageerror', lambda error: self.erros_js.append(str(error)))

    def entrar(self, user, m):
        self.m = m
        self.page.context.clear_cookies()
        self.page.goto(self.live_server_url+'/accounts/login/')
        self.page.locator('#id_login').fill(user.username)
        self.page.locator('#id_password').fill('Senha-b12-segura!')
        self.page.get_by_role('button', name='Entrar', exact=True).click()
        self.page.wait_for_url(self.live_server_url+'/usuarios/painel/')
        self.page.goto(f'{self.live_server_url}/usuarios/trabalhos/{m.pk}/')
        self.page.get_by_role('link', name='Acompanhar documentos e publicação').click()

    def enviar(self, tipo, titulo):
        self.page.locator('#tipo-documento').select_option(tipo)
        self.page.locator('#arquivo-documento').set_input_files({'name': f'{titulo}.pdf', 'mimeType': 'application/pdf', 'buffer': conteudo_pdf(titulo)})
        self.page.get_by_role('button', name='Enviar documento', exact=True).click()
        documento = next(d for d in self.dados()['documentos'] if d['tipo'] == tipo and d['vigente'])
        return SimpleNamespace(pk=documento['id'])

    def dados(self):
        return self.page.request.get(f'{self.live_server_url}/api/usuarios/monografias/{self.m.pk}/documentos/').json()

    def aceitar(self, documento, botao):
        self.page.locator(f'#confirmacao-{documento.pk}').check()
        self.page.get_by_role('button', name=botao, exact=True).click()

    def captura(self, nome):
        destino = os.environ.get('BROWSER_ARTIFACTS')
        if destino:
            Path(destino).mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(Path(destino)/nome), full_page=True)

    def test_sem_ressalvas_envio_conferencia_publicacao_e_download(self):
        from playwright.sync_api import expect
        m = self.sem_ressalvas
        self.entrar(self.aluno_user, m)
        termo = self.enviar('TERMO_AUTORIZACAO', 'Termo de teste')
        self.assertIsNone(self.dados()['publicacao'])
        self.entrar(self.coordenador_user, m)
        expect(self.page.get_by_text('Aguardando conferência', exact=True)).to_be_visible()
        self.aceitar(termo, 'Confirmar assinatura do termo')
        expect(self.page.get_by_text('Monografia publicada automaticamente: todos os requisitos foram atendidos.')).to_be_visible()
        dados = self.dados()
        final = next(d for d in dados['documentos'] if d['id'] == dados['publicacao']['documento_final_id'])
        self.assertEqual(final['tipo'], 'ORIGINAL_APROVADA')
        with self.page.expect_download() as download_info:
            self.page.get_by_role('link', name='Baixar PDF final', exact=True).click()
        self.assertEqual(Path(download_info.value.path()).read_bytes(), ORIGINAL)
        self.captura('b12-publicada-desktop.png')
        self.assertEqual(self.erros_js, [])

    def test_ressalvas_rejeicao_reenvio_e_conferencia_por_orientador(self):
        from playwright.sync_api import expect
        m = self.com_ressalvas
        self.entrar(self.aluno_user, m)
        termo = self.enviar('TERMO_AUTORIZACAO', 'Termo de teste')
        corrigida = self.enviar('VERSAO_CORRIGIDA', 'Primeira correção')
        self.entrar(self.coordenador_user, m)
        self.aceitar(termo, 'Confirmar assinatura do termo')
        self.assertIsNone(self.dados()['publicacao'])
        expect(self.page.get_by_role('button', name='Aceitar versão corrigida')).to_have_count(0)
        self.entrar(self.orientador_user, m)
        self.page.get_by_text('Rejeitar documento e solicitar novo envio', exact=True).click()
        self.page.locator(f'#motivo-{corrigida.pk}').fill('Ajustar a conclusão conforme a banca.')
        self.page.get_by_role('button', name='Rejeitar documento', exact=True).click()
        expect(self.page.get_by_text('Motivo da decisão: Ajustar a conclusão conforme a banca.', exact=True)).to_be_visible()
        self.entrar(self.aluno_user, m)
        nova = self.enviar('VERSAO_CORRIGIDA', 'Correção revisada')
        self.entrar(self.orientador_user, m)
        self.aceitar(nova, 'Aceitar versão corrigida')
        expect(self.page.get_by_role('link', name='Baixar PDF final', exact=True)).to_be_visible()
        self.assertEqual(self.dados()['publicacao']['documento_final_id'], nova.pk)
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.assertFalse(self.page.evaluate('document.documentElement.scrollWidth > window.innerWidth'))
        self.captura('b12-publicada-mobile.png')
        self.assertEqual(self.erros_js, [])
