"""B12: publicação, evidências, permissões, integridade e recuperação de falhas."""
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfWriter

from equipe.models import Aluno, Curso, Professor
from monografias.models import Avaliacao, Banca, DocumentoComplementar, HistoricoAcao, Monografia, ParticipacaoBanca, Publicacao
from .integracao_microservico import MicroservicoIndisponivel
from .publicacao import conferir_documento, enviar_documento, publicar_se_elegivel
from .services import finalizar_resultado_banca


def conteudo_pdf(titulo='Original', senha=None):
    output = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_metadata({'/Title': titulo})
    if senha:
        writer.encrypt(senha)
    writer.write(output)
    return output.getvalue()


ORIGINAL = conteudo_pdf()


def arquivo_pdf(titulo='Original', conteudo=None, nome='documento.pdf'):
    return SimpleUploadedFile(nome, conteudo if conteudo is not None else conteudo_pdf(titulo), content_type='application/pdf')


class CenarioPublicacao:
    def preparar_cenario(self):
        User = get_user_model()
        self.aluno_user = User.objects.create_user('aluno-b12', password='Senha-b12-segura!')
        self.orientador_user = User.objects.create_user('orientador-b12', password='Senha-b12-segura!')
        self.coordenador_user = User.objects.create_user('coordenador-b12', password='Senha-b12-segura!')
        self.outro_user = User.objects.create_user('outro-b12', password='Senha-b12-segura!', is_staff=True)
        self.admin = User.objects.create_superuser('admin-b12', 'admin-b12@example.com', 'Senha-b12-segura!')
        self.orientador = Professor.objects.create(usuario=self.orientador_user, nome='Orientador B12', email='orientador-b12@example.com', departamento='D', area_pesquisa='A')
        self.coordenador = Professor.objects.create(usuario=self.coordenador_user, nome='Coordenadora B12', email='coordenadora-b12@example.com', departamento='D', area_pesquisa='A')
        self.curso = Curso.objects.create(nome='Computação B12', codigo='B12', coordenador=self.coordenador)
        self.aluno = Aluno.objects.create(usuario=self.aluno_user, nome='Aluno B12', matricula='B12-001', email='aluno-b12@example.com', curso=self.curso)

    def trabalho(self, resultado='APROVADA'):
        monografia = Monografia.objects.create(titulo=f'TCC {resultado}', resumo='Resumo', aluno=self.aluno,
            curso=self.curso, orientador=self.orientador, status_fluxo='DEFESA_REALIZADA',
            microservico_id=81 + Monografia.objects.count(), sha256=hashlib.sha256(ORIGINAL).hexdigest())
        inicio = timezone.now() - timedelta(days=1)
        banca = Banca.objects.create(monografia=monografia, inicio=inicio, fim=inicio+timedelta(hours=1), status='REALIZADA', local='Sala')
        participacao = ParticipacaoBanca.objects.create(banca=banca, professor=self.orientador, papel='PRESIDENTE', convite_status='CONFIRMADO')
        Avaliacao.objects.create(participacao=participacao, nota='4.00' if resultado == 'REPROVADA' else '8.00', parecer='Parecer da banca', recomendacao=resultado)
        finalizar_resultado_banca(self.orientador_user, banca.pk)
        monografia.refresh_from_db()
        return monografia

    def arquivos_temporarios(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        config = override_settings(MEDIA_ROOT=self.temp.name)
        config.enable()
        self.addCleanup(config.disable)
        micro = patch('usuarios.publicacao.obter_pdf_remoto', side_effect=lambda *args: io.BytesIO(ORIGINAL))
        self.micro = micro.start()
        self.addCleanup(micro.stop)


class PublicacaoTests(CenarioPublicacao, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.preparar_cenario(cls)

    def setUp(self):
        self.arquivos_temporarios()
        self.m = self.trabalho()

    def enviar(self, tipo='TERMO_AUTORIZACAO', usuario=None, monografia=None, arquivo=None):
        self.client.force_login(usuario or self.aluno_user)
        return self.client.post(reverse('api-documentos', args=[(monografia or self.m).pk]),
            {'tipo': tipo, 'arquivo': arquivo if arquivo is not None else arquivo_pdf(tipo)})

    def conferir(self, documento, usuario=None, **dados):
        self.client.force_login(usuario or self.coordenador_user)
        return self.client.post(reverse('api-conferir-documento', args=[documento.monografia_id, documento.pk]),
            {'decisao': 'aceitar', 'confirmacao': True, **dados}, content_type='application/json')

    def doc(self, resposta):
        self.assertEqual(resposta.status_code, 201, resposta.content)
        return DocumentoComplementar.objects.get(pk=resposta.json()['id'])

    def publicar(self):
        termo = self.doc(self.enviar())
        resposta = self.conferir(termo)
        self.assertEqual(resposta.status_code, 200, resposta.content)
        return Publicacao.objects.get(monografia=self.m)

    def test_sem_ressalvas_so_publica_apos_conferencia_humana_e_fixa_original(self):
        termo = self.doc(self.enviar())
        self.assertEqual(termo.decisao, 'PENDENTE')
        self.assertFalse(Publicacao.objects.exists())
        self.assertEqual(self.conferir(termo, confirmacao=False).status_code, 400)
        self.assertEqual(self.conferir(termo).status_code, 200)
        publicacao = Publicacao.objects.get(monografia=self.m)
        self.assertEqual(publicacao.documento_final.tipo, 'ORIGINAL_APROVADA')
        self.assertEqual(publicacao.documento_final.origem_microservico_id, self.m.microservico_id)
        self.assertEqual(publicacao.sha256, hashlib.sha256(ORIGINAL).hexdigest())
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'PUBLICADA')
        self.assertEqual(self.m.data_publicacao, timezone.localdate())
        termo.refresh_from_db()
        self.assertEqual(termo.conferido_por, self.coordenador_user)
        self.assertIsNotNone(termo.conferido_em)
        self.assertEqual(HistoricoAcao.objects.filter(acao='MONOGRAFIA_PUBLICADA').count(), 1)

    def test_ressalvas_exige_correcao_conferida_e_publica_arquivo_corrigido(self):
        self.m = self.trabalho('APROVADA_COM_RESSALVAS')
        termo = self.doc(self.enviar())
        self.assertIsNone(self.conferir(termo).json()['publicacao'])
        corrigida = self.doc(self.enviar('VERSAO_CORRIGIDA'))
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'CORRECOES_ENTREGUES')
        self.assertFalse(Publicacao.objects.exists())
        self.assertEqual(self.conferir(corrigida, self.orientador_user).status_code, 200)
        publicacao = Publicacao.objects.get(monografia=self.m)
        self.assertEqual(publicacao.documento_final, corrigida)
        self.assertEqual(publicacao.resultado_banca, 'APROVADA_COM_RESSALVAS')
        self.assertNotEqual(publicacao.sha256, self.m.sha256)
        self.micro.assert_not_called()

    def test_correcao_antes_do_termo_tambem_publica_automaticamente(self):
        self.m = self.trabalho('APROVADA_COM_RESSALVAS')
        corrigida = self.doc(self.enviar('VERSAO_CORRIGIDA'))
        self.assertIsNone(self.conferir(corrigida, self.orientador_user).json()['publicacao'])
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'APROVADA')
        termo = self.doc(self.enviar())
        self.assertIsNotNone(self.conferir(termo).json()['publicacao'])

    def test_reprovado_e_status_forjado_nao_publicam(self):
        self.m = self.trabalho('REPROVADA')
        self.assertEqual(self.enviar().status_code, 409)
        Monografia.objects.filter(pk=self.m.pk).update(status_fluxo='APROVADA')
        self.assertEqual(self.enviar().status_code, 409)
        self.assertFalse(DocumentoComplementar.objects.exists())

    def test_sem_termo_ou_sem_resultado_final_nao_publica(self):
        self.assertIsNone(publicar_se_elegivel(self.orientador_user, self.m.pk))
        HistoricoAcao.objects.filter(acao='RESULTADO_BANCA_FINALIZADO').delete()
        self.assertEqual(self.enviar().status_code, 409)
        self.assertFalse(Publicacao.objects.exists())

    def test_avaliacao_alterada_apos_fechamento_bloqueia(self):
        Avaliacao.objects.filter(participacao__banca__monografia=self.m).update(nota='9.00')
        self.assertEqual(self.enviar().status_code, 409)

    def test_correcao_so_com_ressalvas_e_tipo_interno_nao_aceita_upload(self):
        self.assertEqual(self.enviar('VERSAO_CORRIGIDA').status_code, 409)
        self.assertEqual(self.enviar('ORIGINAL_APROVADA').status_code, 400)

    def test_validacao_bytes_estrutura_extensao_senha_e_tamanho(self):
        for arquivo in (arquivo_pdf(conteudo=b''), arquivo_pdf(conteudo=b'nao pdf'),
                        arquivo_pdf(conteudo=b'%PDF-1.7 truncado'), arquivo_pdf(nome='falso.txt'),
                        arquivo_pdf(conteudo=conteudo_pdf(senha='segredo'))):
            with self.subTest(nome=arquivo.name, tamanho=arquivo.size):
                self.assertEqual(self.enviar(arquivo=arquivo).status_code, 400)
        with override_settings(DOCUMENTOS_MAX_UPLOAD_MB=1):
            self.assertEqual(self.enviar(arquivo=arquivo_pdf(conteudo=b'%PDF-'+b'x'*(1024*1024))).status_code, 400)
        self.assertFalse(DocumentoComplementar.objects.exists())
        self.assertEqual(list(Path(self.temp.name).rglob('*.pdf')), [])

    def test_envio_so_autor_e_conferencias_separadas_por_papel(self):
        for user in (self.outro_user, self.orientador_user, self.coordenador_user, self.admin):
            self.assertEqual(self.enviar(usuario=user).status_code, 403)
        termo = self.doc(self.enviar())
        for user in (self.aluno_user, self.orientador_user, self.outro_user):
            self.assertEqual(self.conferir(termo, user).status_code, 403)
        self.m = self.trabalho('APROVADA_COM_RESSALVAS')
        corrigida = self.doc(self.enviar('VERSAO_CORRIGIDA'))
        for user in (self.aluno_user, self.coordenador_user, self.admin):
            self.assertEqual(self.conferir(corrigida, user).status_code, 403)

    def test_coordenador_de_outro_curso_nao_confere_termo(self):
        outro_curso = Curso.objects.create(nome='Outro', codigo='OUT')
        self.curso.coordenador = None
        self.curso.save()
        outro_curso.coordenador = self.coordenador
        outro_curso.save()
        termo = self.doc(self.enviar())
        self.assertEqual(self.conferir(termo).status_code, 403)
        self.assertEqual(self.conferir(termo, self.admin).status_code, 200)

    def test_rejeicao_exige_motivo_e_reenvio_preserva_historico(self):
        termo = self.doc(self.enviar())
        self.assertEqual(self.conferir(termo, decisao='rejeitar', motivo='').status_code, 400)
        self.assertEqual(self.conferir(termo, decisao='rejeitar', motivo='Assinatura ausente').status_code, 200)
        self.assertEqual(self.conferir(termo).status_code, 409)
        novo = self.doc(self.enviar(arquivo=arquivo_pdf('Termo assinado')))
        termo.refresh_from_db()
        self.assertFalse(termo.vigente)
        self.assertEqual(termo.motivo, 'Assinatura ausente')
        self.assertTrue(termo.arquivo.storage.exists(termo.arquivo.name))
        self.assertEqual(self.conferir(termo).status_code, 409)
        self.assertEqual(self.conferir(novo).status_code, 200)

    def test_rejeicao_correcao_volta_a_ressalvas_e_nova_versao_exige_conferencia(self):
        self.m = self.trabalho('APROVADA_COM_RESSALVAS')
        anterior = self.doc(self.enviar('VERSAO_CORRIGIDA'))
        self.conferir(anterior, self.orientador_user, decisao='rejeitar', motivo='Rever conclusão')
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'APROVADA_COM_RESSALVAS')
        nova = self.doc(self.enviar('VERSAO_CORRIGIDA', arquivo=arquivo_pdf('Correção 2')))
        self.assertEqual(nova.decisao, 'PENDENTE')
        self.assertEqual(self.conferir(anterior, self.orientador_user).status_code, 409)
        self.assertEqual(self.conferir(nova, self.orientador_user).status_code, 200)
        outra = self.doc(self.enviar('VERSAO_CORRIGIDA', arquivo=arquivo_pdf('Correção 3')))
        termo = self.doc(self.enviar())
        self.assertIsNone(self.conferir(termo).json()['publicacao'])
        self.assertIsNotNone(self.conferir(outra, self.orientador_user).json()['publicacao'])

    def test_publicacao_e_confirmacao_repetidas_sao_idempotentes(self):
        publicacao = self.publicar()
        self.assertEqual(self.conferir(publicacao.termo).json()['publicacao']['id'], publicacao.pk)
        self.assertEqual(publicar_se_elegivel(self.aluno_user, self.m.pk).pk, publicacao.pk)
        self.assertEqual(Publicacao.objects.count(), 1)
        self.assertEqual(HistoricoAcao.objects.filter(acao='MONOGRAFIA_PUBLICADA').count(), 1)
        self.assertEqual(HistoricoAcao.objects.filter(acao='DOCUMENTO_ACEITO').count(), 1)
        self.assertEqual(self.micro.call_count, 1)

    def test_falha_remota_desfaz_ultima_conferencia_e_permite_retry(self):
        termo = self.doc(self.enviar())
        self.micro.side_effect = MicroservicoIndisponivel('Indisponível')
        self.assertEqual(self.conferir(termo).status_code, 503)
        termo.refresh_from_db()
        self.assertEqual(termo.decisao, 'PENDENTE')
        self.assertFalse(Publicacao.objects.exists())
        self.assertFalse(HistoricoAcao.objects.filter(acao='DOCUMENTO_ACEITO').exists())
        self.micro.side_effect = lambda *args: io.BytesIO(ORIGINAL)
        self.assertEqual(self.conferir(termo).status_code, 200)

    def test_hash_original_divergente_e_transferencia_parcial_bloqueiam(self):
        termo = self.doc(self.enviar())
        for conteudo in (conteudo_pdf('Modificado no microserviço'), ORIGINAL[:50]):
            self.micro.side_effect = lambda *args: io.BytesIO(conteudo)
            self.assertIn(self.conferir(termo).status_code, (400, 409))
        self.assertFalse(Publicacao.objects.exists())
        self.assertEqual(DocumentoComplementar.objects.count(), 1)

    def test_documento_adulterado_bloqueia_conferencia_publicacao_e_download(self):
        self.m = self.trabalho('APROVADA_COM_RESSALVAS')
        corrigida = self.doc(self.enviar('VERSAO_CORRIGIDA'))
        self.conferir(corrigida, self.orientador_user)
        with corrigida.arquivo.storage.open(corrigida.arquivo.name, 'wb') as arquivo:
            arquivo.write(conteudo_pdf('Adulterado'))
        termo = self.doc(self.enviar())
        self.assertEqual(self.conferir(termo).status_code, 409)
        self.assertFalse(Publicacao.objects.exists())
        self.assertEqual(self.client.get(reverse('api-documento-arquivo', args=[self.m.pk, corrigida.pk])).status_code, 409)

    def test_rollback_remove_arquivos_novos_e_preserva_versao_anterior(self):
        termo = self.doc(self.enviar())
        with patch('usuarios.publicacao._registrar', side_effect=RuntimeError('Falha de auditoria')):
            with self.assertRaises(RuntimeError):
                self.enviar(arquivo=arquivo_pdf('Novo termo'))
        termo.refresh_from_db()
        self.assertTrue(termo.vigente)
        self.assertEqual(DocumentoComplementar.objects.count(), 1)
        self.assertEqual(len(list(Path(self.temp.name).rglob('*.pdf'))), 1)
        with patch('usuarios.publicacao.Publicacao.objects.create', side_effect=RuntimeError('Falha de banco')):
            with self.assertRaises(RuntimeError):
                self.conferir(termo)
        self.assertEqual(len(list(Path(self.temp.name).rglob('*.pdf'))), 1)
        termo.refresh_from_db()
        self.assertEqual(termo.decisao, 'PENDENTE')

    def test_documentos_privados_sem_url_direta_ou_acesso_por_id_alheio(self):
        termo = self.doc(self.enviar())
        with self.assertRaises(ValueError):
            _ = termo.arquivo.url
        self.client.force_login(self.outro_user)
        for rota in ('api-documentos', 'usuarios:documentos'):
            self.assertEqual(self.client.get(reverse(rota, args=[self.m.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('api-documento-arquivo', args=[self.m.pk, termo.pk])).status_code, 403)
        self.client.logout()
        self.assertIn(self.client.get(reverse('api-documento-arquivo', args=[self.m.pk, termo.pk])).status_code, (401, 403))
        self.assertEqual(self.client.get('/media/'+termo.arquivo.name).status_code, 404)
        self.client.force_login(self.aluno_user)
        outra = self.trabalho()
        self.assertEqual(self.client.get(reverse('api-documento-arquivo', args=[outra.pk, termo.pk])).status_code, 404)
        response = self.client.get(reverse('api-documento-arquivo', args=[self.m.pk, termo.pk]))
        self.assertEqual(b''.join(response.streaming_content), conteudo_pdf('TERMO_AUTORIZACAO'))
        self.assertIn('no-store', response['Cache-Control'])
        self.assertNotIn(termo.arquivo.name, self.client.get(reverse('api-documentos', args=[self.m.pk])).content.decode())

    def test_publicada_bloqueia_upload_alteracao_exclusao_api_e_admin(self):
        publicacao = self.publicar()
        self.assertEqual(self.enviar().status_code, 409)
        self.assertEqual(self.conferir(publicacao.termo, decisao='rejeitar', motivo='Tarde').status_code, 409)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.patch(f'/api/monografias/{self.m.pk}/', {'titulo': 'Alterado'}, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/monografias/{self.m.pk}/').status_code, 403)
        for model, pk in (('monografia', self.m.pk), ('banca', publicacao.banca_id), ('documentocomplementar', publicacao.termo_id), ('publicacao', publicacao.pk)):
            self.assertEqual(self.client.post(f'/admin/monografias/{model}/{pk}/change/', {'titulo': 'Alterado'}).status_code, 403)
            self.assertEqual(self.client.post(f'/admin/monografias/{model}/{pk}/delete/', {'post': 'yes'}).status_code, 403)
        self.client.post('/admin/monografias/monografia/', {'action': 'delete_selected', '_selected_action': [self.m.pk], 'post': 'yes'})
        self.assertTrue(Monografia.objects.filter(pk=self.m.pk).exists())

    def test_nao_acrescenta_avaliacao_pelo_crud_a_banca_finalizada(self):
        banca = self.m.bancas.get()
        extra = ParticipacaoBanca.objects.create(banca=banca, professor=self.coordenador, papel='SUPLENTE')
        self.client.force_login(self.admin)
        response = self.client.post('/api/avaliacoes/', {'participacao': extra.pk, 'nota': '10.00', 'parecer': 'Injetado', 'recomendacao': 'APROVADA'})
        self.assertEqual(response.status_code, 403, response.content)

    def test_ata_e_comprovante_opcionais_nao_substituem_termo(self):
        self.assertEqual(self.enviar('ATA').status_code, 403)
        ata = self.doc(self.enviar('ATA', self.orientador_user))
        self.doc(self.enviar('COMPROVANTE_CORRECAO'))
        self.assertEqual(ata.decisao, 'RECEBIDO')
        self.assertIsNone(publicar_se_elegivel(self.orientador_user, self.m.pk))
        self.assertFalse(Publicacao.objects.exists())

    def test_html_aplica_mesmo_fluxo_e_exibe_erros_e_estado(self):
        self.client.force_login(self.aluno_user)
        pagina = reverse('usuarios:documentos', args=[self.m.pk])
        self.assertContains(self.client.get(pagina), 'Anexar o termo não confirma sua assinatura')
        response = self.client.post(pagina, {'tipo': 'TERMO_AUTORIZACAO', 'arquivo': arquivo_pdf('Termo')})
        self.assertRedirects(response, pagina)
        termo = DocumentoComplementar.objects.get()
        self.client.force_login(self.coordenador_user)
        self.assertContains(self.client.get(pagina), 'Confirmar assinatura do termo')
        acao = reverse('usuarios:conferir-documento', args=[self.m.pk, termo.pk])
        self.assertEqual(self.client.post(acao, {'decisao': 'aceitar'}).status_code, 400)
        self.assertRedirects(self.client.post(acao, {'decisao': 'aceitar', 'confirmacao': 'on'}), pagina)
        self.assertContains(self.client.get(pagina), 'Baixar PDF final')
        self.assertNotContains(self.client.get(pagina), 'Enviar documento')

    def test_html_e_api_exigem_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.aluno_user)
        for rota in ('api-documentos', 'usuarios:documentos'):
            self.assertEqual(client.post(reverse(rota, args=[self.m.pk]), {'tipo': 'TERMO_AUTORIZACAO', 'arquivo': arquivo_pdf()}).status_code, 403)


class PublicacaoConcorrenteTests(CenarioPublicacao, TransactionTestCase):
    def test_duas_confirmacoes_concorrentes_publicam_uma_unica_vez(self):
        self.preparar_cenario()
        self.arquivos_temporarios()
        m = self.trabalho()
        termo = enviar_documento(self.aluno_user, m.pk, 'TERMO_AUTORIZACAO', arquivo_pdf('Termo'))

        def confirmar():
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.coordenador_user.pk)
                return conferir_documento(user, m.pk, termo.pk, decisao='aceitar', confirmacao=True)[1].pk
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda _: confirmar(), range(2)))
        self.assertEqual(len(set(resultados)), 1)
        self.assertEqual(Publicacao.objects.count(), 1)
        self.assertEqual(self.micro.call_count, 1)
        self.assertEqual(HistoricoAcao.objects.filter(acao='MONOGRAFIA_PUBLICADA').count(), 1)
