"""Demonstração opt-in: Chrome + HTTP/JWT + RabbitMQ + SMTP locais reais.

Exige microserviço com dados descartáveis e extrator ativo. Não altera estados
acadêmicos diretamente nem simula relógio: aguarda o término da banca de teste.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest import skipUnless
from urllib.request import Request, urlopen
from uuid import uuid4

from allauth.account.models import EmailAddress
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import override_settings, tag
from django.utils import timezone

from monografias.models import Avaliacao, Banca, HistoricoAcao, MembroExterno, Monografia, Publicacao
from notificacoes import mensageria as avisos
from notificacoes.models import AvisoBanca
from notificacoes.services import dados_evento, enviar_evento
from repositorio import mensageria as indice
from repositorio.models import IndicePublicacao
from repositorio.test_helpers import pdf_com_texto
from .integracao_microservico import _requisicao, _token
from .test_publicacao import CenarioPublicacao, conteudo_pdf
from .browser_helpers import banco, fora_do_loop
from .services import salvar_rascunho


@tag('integration', 'browser')
@skipUnless(os.environ.get('RUN_P1_INTEGRATION') == '1', 'Requer serviços reais isolados; consulte documentação da Parte 1.')
class Parte1IntegradaTests(CenarioPublicacao, StaticLiveServerTestCase):
    def setUp(self):
        from playwright.sync_api import sync_playwright
        self.preparar_cenario()
        self.codigo = uuid4().hex[:12]
        self.titulo = 'Demonstração Parte 1 ' + self.codigo
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = override_settings(
            MEDIA_ROOT=self.tmp.name,
            MICROSERVICO_API_URL=os.environ['P1_MICROSERVICO_URL'],
            SIMPLE_JWT={'ALGORITHM': 'HS256', 'SIGNING_KEY': os.environ['P1_JWT_SIGNING_KEY'],
                        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10)},
            NOTIFICACOES_FILA='parte1.avisos.' + self.codigo,
            REPOSITORIO_FILA='parte1.indice.' + self.codigo,
            EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
            EMAIL_HOST='127.0.0.1', EMAIL_PORT=1025,
        )
        self.config.enable()
        self.addCleanup(self.config.disable)
        for pessoa in (self.aluno, self.orientador, self.coordenador):
            pessoa.email = f'{pessoa.usuario.username}-{self.codigo}@example.test'
            pessoa.save(update_fields=['email'])
            pessoa.usuario.email = pessoa.email
            pessoa.usuario.save(update_fields=['email'])
            EmailAddress.objects.create(user=pessoa.usuario, email=pessoa.email, primary=True, verified=True)
        self.externo = MembroExterno.objects.create(nome='Avaliador externo de teste',
            email=f'externo-{self.codigo}@example.test', instituicao='Instituição de teste')
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser = self.playwright.chromium.launch(executable_path=shutil.which('google-chrome'), headless=True)
        self.addCleanup(self.browser.close)
        self.erros_js = []
        self.aluno_page = self.login(self.aluno_user)
        self.prof_page = self.login(self.orientador_user)
        self.coord_page = self.login(self.coordenador_user)
        self.admin_page = self.login(self.admin)
        self.externo_page = self.nova_pagina()

    def nova_pagina(self):
        page = self.browser.new_page(viewport={'width': 1366, 'height': 1000})
        page.set_default_timeout(15000)
        page.on('pageerror', lambda e: self.erros_js.append(str(e)))
        return page

    def abrir(self, page, path):
        return page.goto(self.live_server_url + path)

    def login(self, user):
        page = self.nova_pagina()
        self.abrir(page, '/accounts/login/')
        page.locator('#id_login').fill(user.username)
        page.locator('#id_password').fill('Senha-b12-segura!')
        page.locator('form:has(#id_login) button[type=submit]').click()
        page.wait_for_url(self.live_server_url + '/usuarios/painel/')
        return page

    def captura(self, page, nome):
        pasta = Path(os.environ.get('BROWSER_ARTIFACTS', '/tmp/allteam-parte1-browser'))
        pasta.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(pasta / nome), full_page=True)

    def post(self, page, path, data=None):
        cookies = page.context.cookies(self.live_server_url)
        csrf = next(c['value'] for c in cookies if c['name'] == 'csrftoken')
        return page.request.post(self.live_server_url + path, data=data or {}, headers={'X-CSRFToken': csrf})

    @fora_do_loop
    def micro_extracoes(self):
        banco(self.m.refresh_from_db)
        return _requisicao('GET', f'monografias/{self.m.microservico_id}/extracoes/', _token(self.aluno_user, self.m, 'aluno'))['versoes']

    def aguardar_extracoes(self, quantidade):
        limite = time.monotonic() + 30
        while time.monotonic() < limite:
            versoes = self.micro_extracoes()
            if len(versoes) == quantidade and all(v['processado_em'] for v in versoes):
                return versoes
            time.sleep(0.5)
        self.fail('Extrator não concluiu as versões em 30 segundos.')

    @fora_do_loop
    def ciclo_fila(self, modulo, nome):
        conexao = modulo.conectar()
        try:
            canal = modulo.preparar_canal(conexao)
            self.assertEqual(modulo.despachar_pendentes(canal), 1)
            self.assertEqual(modulo.consumir_disponiveis(conexao, canal), 1)
        finally:
            if conexao.is_open:
                canal.queue_delete(queue=nome)
                canal.queue_delete(queue=nome + '.dlq')
                canal.exchange_delete(exchange=nome + '.eventos')
                canal.exchange_delete(exchange=nome + '.falhas')
                conexao.close()

    def mensagens(self):
        with urlopen('http://127.0.0.1:8025/api/v1/messages?limit=200', timeout=5) as resposta:
            return json.load(resposta)['messages']

    def test_percurso_completo_com_ajustes_filas_avaliacao_externa_e_publicacao(self):
        from playwright.sync_api import expect
        p, prof, coord, externo = self.aluno_page, self.prof_page, self.coord_page, self.externo_page
        self.abrir(p, '/usuarios/rascunhos/novo/')
        p.locator('#id_titulo').fill(self.titulo)
        p.locator('#id_resumo').fill('Demonstração integrada com dados descartáveis.')
        p.locator('#id_palavras_chave').fill('Distribuidos, Academico')
        p.locator('#id_orientador').select_option(str(self.orientador.pk))
        p.get_by_role('button', name='Salvar rascunho').click()
        p.wait_for_url('**/usuarios/trabalhos/*/')
        self.m = banco(lambda: Monografia.objects.get(titulo=self.titulo))
        caminho = f'/usuarios/trabalhos/{self.m.pk}/'

        def submeter(conteudo):
            p.locator('input[name=arquivo]').set_input_files({'name': 'trabalho.pdf', 'mimeType': 'application/pdf', 'buffer': conteudo})
            p.get_by_role('button', name='Enviar PDF e submeter ao orientador').click()
            expect(p.locator('body')).to_contain_text('PDF submetido ao orientador com sucesso.')

        original = pdf_com_texto('Primeira versao ' + self.codigo)
        submeter(original)
        self.aguardar_extracoes(1)
        self.abrir(prof, caminho)
        self.assertEqual(prof.request.get(self.live_server_url + caminho + 'pdf/').body(), original)
        prof.locator('textarea[name=motivo]').fill('Revisar a metodologia antes da aprovação.')
        prof.get_by_role('button', name='Devolver para ajustes').click()
        expect(prof.locator('body')).to_contain_text('Ajustes solicitados.')
        self.abrir(p, f'/usuarios/rascunhos/{self.m.pk}/editar/')
        p.locator('#id_resumo').fill('Metodologia revisada após orientação.')
        p.get_by_role('button', name='Salvar rascunho').click()
        p.wait_for_url('**/usuarios/trabalhos/*/')
        revisado = pdf_com_texto('Segunda versao revisada ' + self.codigo)
        submeter(revisado)
        versoes = self.aguardar_extracoes(2)
        self.assertEqual({v['sha256'] for v in versoes}, {hashlib.sha256(original).hexdigest(), hashlib.sha256(revisado).hexdigest()})
        self.captura(p, '01-submissao-revisada.png')
        self.abrir(prof, caminho)
        prof.get_by_role('button', name='Aprovar submissão', exact=True).click()
        expect(prof.locator('body')).to_contain_text('A banca pode ser proposta.')
        banco(self.m.refresh_from_db)
        self.assertEqual(self.m.status_fluxo, 'APROVADA_ORIENTADOR')
        print('P1: B09 com duas versões extraídas pelo worker e aprovação HTTP/JWT.', flush=True)

        self.abrir(prof, caminho + 'propor-banca/')
        inicio = (timezone.localtime() + timedelta(minutes=2)).replace(second=0, microsecond=0)
        fim = inicio + timedelta(minutes=1)
        prof.locator('#id_inicio').fill(inicio.strftime('%Y-%m-%dT%H:%M'))
        prof.locator('#id_fim').fill(fim.strftime('%Y-%m-%dT%H:%M'))
        prof.locator('#id_modalidade').select_option('REMOTA')
        prof.locator('#id_link').fill('https://reuniao.example.test/' + self.codigo)
        prof.get_by_role('button', name='Criar proposta').click()
        prof.wait_for_url('**/usuarios/bancas/*/participantes/novo/')
        banca = banco(lambda: Banca.objects.get(monografia=self.m))
        for campo, valor, papel in [('professor', self.orientador.pk, 'PRESIDENTE'), ('membro_externo', self.externo.pk, 'AVALIADOR')]:
            self.abrir(prof, f'/usuarios/bancas/{banca.pk}/participantes/novo/')
            prof.locator('#id_' + campo).select_option(str(valor))
            prof.locator('#id_papel').select_option(papel)
            prof.get_by_role('button', name='Incluir participante').click()
            prof.wait_for_url('**/usuarios/trabalhos/*/')
        interno = banco(lambda: banca.participacoes.get(professor=self.orientador))
        participacao = banco(lambda: banca.participacoes.get(membro_externo=self.externo))
        self.assertFalse(banco(lambda: AvisoBanca.objects.exists()))
        prof.get_by_role('button', name='Confirmar presença').click()
        self.assertFalse(banco(lambda: AvisoBanca.objects.exists()))
        self.abrir(prof, f'/usuarios/convites/{participacao.pk}/emitir/')
        prof.get_by_role('button', name='Gerar convite', exact=True).click()
        token = prof.locator('#codigo-convite').input_value()
        self.abrir(externo, f'/usuarios/convites/{participacao.pk}/')
        externo.locator('#id_token').fill(token)
        externo.get_by_role('button', name='Confirmar minha participação').click()
        expect(externo.locator('body')).to_contain_text('Participação confirmada com sucesso.')
        banco(banca.refresh_from_db)
        self.assertEqual(banca.status, 'AGENDADA')
        self.ciclo_fila(avisos, 'parte1.avisos.' + self.codigo)
        aviso = banco(lambda: AvisoBanca.objects.get(banca=banca))
        self.assertEqual(banco(lambda: aviso.entregas.filter(enviado_em__isnull=False).count()), 3)
        self.assertFalse(banco(lambda: enviar_evento(dados_evento(aviso))))
        mensagens = [m for m in self.mensagens() if self.codigo in m['Subject']]
        self.assertEqual(len(mensagens), 3)
        self.assertEqual({m['To'][0]['Address'] for m in mensagens}, {self.aluno.email, self.orientador.email, self.externo.email})
        self.abrir(prof, caminho)
        self.captura(prof, '02-banca-agendada.png')
        print('P1: B10 confirmado por professor e externo; três avisos recebidos no SMTP local.', flush=True)
        print(f'P1: aguardando término real da banca de teste ({fim.isoformat()}).', flush=True)
        while timezone.now() <= fim:
            time.sleep(min(5, max(0.1, (fim - timezone.now()).total_seconds() + 0.1)))

        self.abrir(prof, caminho)
        prof.get_by_role('button', name='Registrar defesa realizada').click()
        self.abrir(prof, f'/usuarios/participacoes/{interno.pk}/avaliar/')
        prof.locator('#id_nota').fill('8')
        prof.locator('#id_parecer').fill('Aprovado com ajustes de redação.')
        prof.locator('#id_recomendacao').select_option('APROVADA_COM_RESSALVAS')
        prof.get_by_role('button', name='Salvar minha avaliação').click()
        self.assertEqual(self.post(prof, f'/api/usuarios/bancas/{banca.pk}/finalizar/').status, 400)
        self.abrir(prof, f'/usuarios/participacoes/{participacao.pk}/avaliacao-externa/emitir/')
        prof.get_by_role('button', name='Gerar código de avaliação').click()
        codigo = prof.locator('#codigo-avaliacao').input_value()
        self.assertNotEqual(codigo, token)
        self.abrir(externo, f'/usuarios/participacoes/{participacao.pk}/avaliacao-externa/')
        externo.locator('#id_codigo').fill(codigo)
        externo.locator('#id_nota').fill('9')
        externo.locator('#id_parecer').fill('Trabalho aprovado pelo membro externo.')
        externo.locator('#id_recomendacao').select_option('APROVADA')
        externo.get_by_role('button', name='Enviar minha avaliação').click()
        self.assertTrue(banco(lambda: Avaliacao.objects.filter(participacao=participacao).exists()))
        self.captura(externo, '03-avaliacao-externa.png')
        self.abrir(prof, caminho)
        prof.get_by_role('button', name='Calcular e finalizar resultado').click()
        banco(self.m.refresh_from_db)
        self.assertEqual(self.m.status_fluxo, 'APROVADA_COM_RESSALVAS')
        self.assertEqual(self.post(prof, f'/api/usuarios/participacoes/{interno.pk}/avaliacao/',
            {'nota': '10', 'parecer': 'Alteração', 'recomendacao': 'APROVADA'}).status, 409)
        self.assertFalse(banco(lambda: Publicacao.objects.exists()))

        documentos = caminho + 'documentos/'
        final = pdf_com_texto('Hiperconvergencia versão final ' + self.codigo)
        for tipo, conteudo in [('VERSAO_CORRIGIDA', final), ('TERMO_AUTORIZACAO', conteudo_pdf('Termo fictício de teste'))]:
            self.abrir(p, documentos)
            p.locator('#tipo-documento').select_option(tipo)
            p.locator('#arquivo-documento').set_input_files({'name': 'documento.pdf', 'mimeType': 'application/pdf', 'buffer': conteudo})
            p.get_by_role('button', name='Enviar documento', exact=True).click()
        self.abrir(prof, documentos)
        prof.locator('input[name=confirmacao]').check()
        prof.get_by_role('button', name='Aceitar versão corrigida').click()
        self.assertFalse(banco(lambda: Publicacao.objects.exists()))
        self.abrir(coord, documentos)
        coord.locator('input[name=confirmacao]').check()
        coord.get_by_role('button', name='Confirmar assinatura do termo').click()
        expect(coord.locator('body')).to_contain_text('Publicado em')
        self.captura(coord, '04-publicacao-automatica.png')
        self.ciclo_fila(indice, 'parte1.indice.' + self.codigo)
        self.assertEqual(banco(lambda: IndicePublicacao.objects.get().sha256), hashlib.sha256(final).hexdigest())
        self.abrir(externo, '/repositorio/?busca=' + self.codigo)
        expect(externo.locator('body')).to_contain_text(self.titulo)
        self.abrir(externo, f'/repositorio/{self.m.pk}/')
        self.captura(externo, '05-repositorio-publico.png')
        self.assertEqual(externo.request.get(self.live_server_url + f'/api/publico/monografias/{self.m.pk}/arquivo/').body(), final)
        self.assertNotEqual(externo.request.get(self.live_server_url + documentos, max_redirects=0).status, 200)
        historico = banco(lambda: list(HistoricoAcao.objects.values('acao', 'detalhes')))
        self.assertNotIn(token, json.dumps(historico))
        self.assertNotIn(codigo, json.dumps(historico))
        self.assertEqual(self.erros_js, [])
        print('P1: B11 interno/externo, média 8,50, bloqueio após fechamento, B12 e pesquisa B13 concluídos.', flush=True)

    def test_recuperacao_de_senha_com_email_smtp_real_e_navegador(self):
        p = self.externo_page
        self.abrir(p, '/accounts/password/reset/')
        p.locator('#id_email').fill(self.aluno.email)
        p.locator('form:has(#id_email) button[type=submit], form:has(#id_email) input[type=submit]').click()
        mensagens = [m for m in self.mensagens() if any(d['Address'] == self.aluno.email for d in m['To'])]
        self.assertEqual(len(mensagens), 1)
        with urlopen('http://127.0.0.1:8025/api/v1/message/' + mensagens[0]['ID'], timeout=5) as resposta:
            corpo = json.load(resposta)['Text']
        link = re.search(r'https?://[^\s]+/accounts/password/reset/key/[^\s]+', corpo).group(0)
        p.goto(link)
        p.locator('#id_password1').fill('NovaSenha-SMTP_439!teste')
        p.locator('#id_password2').fill('NovaSenha-SMTP_439!teste')
        p.get_by_role('button', name='Alterar senha', exact=True).click()
        banco(self.aluno_user.refresh_from_db)
        self.assertTrue(self.aluno_user.check_password('NovaSenha-SMTP_439!teste'))
        self.captura(p, '06-senha-recuperada.png')

    def test_resposta_perdida_apos_submissao_real_recupera_sem_duplicar_versao(self):
        destino = os.environ['P1_MICROSERVICO_URL'].rstrip('/')

        class ProxyInterrompido(BaseHTTPRequestHandler):
            descartada = False

            def log_message(self, *args):
                pass  # Não registra cabeçalhos/credenciais.

            def encaminhar(self):
                tamanho = int(self.headers.get('Content-Length', 0))
                corpo = self.rfile.read(tamanho) if tamanho else None
                cabecalhos = {k: v for k, v in self.headers.items() if k.lower() in ('authorization', 'content-type', 'accept')}
                req = Request(destino + self.path.removeprefix('/api'), data=corpo, headers=cabecalhos, method=self.command)
                with urlopen(req, timeout=10) as resposta:
                    dados = resposta.read()
                    if self.path.endswith('/submeter/') and not type(self).descartada:
                        type(self).descartada = True
                        self.connection.shutdown(socket.SHUT_RDWR)
                        self.connection.close()
                        self.close_connection = True
                        return
                    self.send_response(resposta.status)
                    self.send_header('Content-Type', resposta.headers['Content-Type'])
                    self.send_header('Content-Length', str(len(dados)))
                    self.end_headers()
                    self.wfile.write(dados)

            do_GET = do_POST = do_PATCH = encaminhar

        proxy = ThreadingHTTPServer(('127.0.0.1', 0), ProxyInterrompido)
        thread = Thread(target=proxy.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(proxy.server_close)
        self.addCleanup(proxy.shutdown)
        self.m = banco(salvar_rascunho, self.aluno_user, {
            'titulo': self.titulo, 'resumo': 'Teste de resposta perdida', 'orientador': self.orientador})
        pdf = pdf_com_texto('Resposta perdida ' + self.codigo)
        csrf = next(c['value'] for c in self.aluno_page.context.cookies() if c['name'] == 'csrftoken')

        def enviar():
            return self.aluno_page.request.post(
                f'{self.live_server_url}/api/usuarios/monografias/{self.m.pk}/submeter-pdf/',
                multipart={'arquivo': {'name': 'teste.pdf', 'mimeType': 'application/pdf', 'buffer': pdf}},
                headers={'X-CSRFToken': csrf})

        with override_settings(MICROSERVICO_API_URL=f'http://127.0.0.1:{proxy.server_port}/api/'):
            self.assertEqual(enviar().status, 503)
            banco(self.m.refresh_from_db)
            remoto_id = self.m.microservico_id
            self.assertIsNotNone(remoto_id)
            self.assertEqual(self.m.status_fluxo, 'RASCUNHO')
            self.assertEqual(enviar().status, 200)
        banco(self.m.refresh_from_db)
        self.assertEqual(self.m.microservico_id, remoto_id)
        self.assertEqual(self.m.status_fluxo, 'SUBMETIDA')
        self.assertEqual(self.m.sha256, hashlib.sha256(pdf).hexdigest())
        self.assertEqual(len(self.aguardar_extracoes(1)), 1)
        self.assertTrue(ProxyInterrompido.descartada)
