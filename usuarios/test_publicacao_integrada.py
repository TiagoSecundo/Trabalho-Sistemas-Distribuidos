"""B09→B12 com HTTP/JWT real. Exige microserviço e banco REMOTO descartáveis.

RUN_B12_INTEGRATION=1 B12_MICROSERVICO_URL=... B12_JWT_SIGNING_KEY=... habilitam
os testes. Registros vinculados remotos ficam no ambiente isolado até descartá-lo.
"""
import hashlib
import os
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest import skipUnless
from uuid import uuid4

from django.test import TransactionTestCase, override_settings, tag
from django.urls import reverse
from django.utils import timezone

from monografias.models import Banca, Monografia, ParticipacaoBanca, Publicacao
from .integracao_microservico import _requisicao, _token, analisar_submissao, submeter_pdf
from .publicacao import conferir_documento, enviar_documento
from .services import finalizar_resultado_banca, registrar_avaliacao_propria, registrar_defesa_realizada
from .test_publicacao import CenarioPublicacao, arquivo_pdf, conteudo_pdf


@tag('integration')
@skipUnless(os.environ.get('RUN_B12_INTEGRATION') == '1', 'Requer microserviço real isolado; veja documentação B12.')
class PublicacaoIntegradaTests(CenarioPublicacao, TransactionTestCase):
    def setUp(self):
        self.preparar_cenario()
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        config = override_settings(MEDIA_ROOT=temp.name,
            MICROSERVICO_API_URL=os.environ['B12_MICROSERVICO_URL'],
            SIMPLE_JWT={'ALGORITHM': 'HS256', 'SIGNING_KEY': os.environ['B12_JWT_SIGNING_KEY'],
                        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10)})
        config.enable()
        self.addCleanup(config.disable)

    def preparar_defesa(self, resultado):
        original = conteudo_pdf('Integração real '+uuid4().hex)
        m = Monografia.objects.create(titulo='Publicação integrada '+uuid4().hex, resumo='Teste B12',
                                     aluno=self.aluno, curso=self.curso, orientador=self.orientador)
        submeter_pdf(self.aluno_user, m.pk, arquivo_pdf(conteudo=original))
        analisar_submissao(self.orientador_user, m.pk, aprovar=True)
        m.refresh_from_db()
        self.assertEqual(m.status_fluxo, 'APROVADA_ORIENTADOR')
        self.assertEqual(m.sha256, hashlib.sha256(original).hexdigest())
        # Fixture temporal da banca; realização, avaliação e fechamento usam B11.
        inicio = timezone.now()-timedelta(days=1)
        banca = Banca.objects.create(monografia=m, inicio=inicio, fim=inicio+timedelta(hours=1), status='AGENDADA', local='Sala de teste')
        p = ParticipacaoBanca.objects.create(banca=banca, professor=self.orientador, convite_status='CONFIRMADO', papel='PRESIDENTE')
        registrar_defesa_realizada(self.orientador_user, banca.pk)
        registrar_avaliacao_propria(self.orientador_user, p.pk, {'nota': '8.00', 'parecer': 'Parecer de teste', 'recomendacao': resultado})
        finalizar_resultado_banca(self.orientador_user, banca.pk)
        return m, original

    def test_publicacao_original_copia_pdf_real_por_http_jwt(self):
        m, original = self.preparar_defesa('APROVADA')
        termo = enviar_documento(self.aluno_user, m.pk, 'TERMO_AUTORIZACAO', arquivo_pdf('Termo de teste'))
        _, publicacao = conferir_documento(self.coordenador_user, m.pk, termo.pk, decisao='aceitar', confirmacao=True)
        self.assertEqual(publicacao.sha256, hashlib.sha256(original).hexdigest())
        self.assertEqual(publicacao.documento_final.origem_microservico_id, m.microservico_id)
        self.client.force_login(self.aluno_user)
        resposta = self.client.get(reverse('api-documento-arquivo', args=[m.pk, publicacao.documento_final_id]))
        self.assertEqual(b''.join(resposta.streaming_content), original)
        m.refresh_from_db()
        self.assertEqual(m.status_fluxo, 'PUBLICADA')

    def test_correcao_publicada_preserva_original_no_microservico(self):
        m, original = self.preparar_defesa('APROVADA_COM_RESSALVAS')
        corrigido = conteudo_pdf('Versão final corrigida '+uuid4().hex)
        correcao = enviar_documento(self.aluno_user, m.pk, 'VERSAO_CORRIGIDA', arquivo_pdf(conteudo=corrigido))
        termo = enviar_documento(self.aluno_user, m.pk, 'TERMO_AUTORIZACAO', arquivo_pdf('Termo de teste'))
        conferir_documento(self.coordenador_user, m.pk, termo.pk, decisao='aceitar', confirmacao=True)
        self.assertFalse(Publicacao.objects.exists())
        _, publicacao = conferir_documento(self.orientador_user, m.pk, correcao.pk, decisao='aceitar', confirmacao=True)
        self.assertEqual(publicacao.sha256, hashlib.sha256(corrigido).hexdigest())
        remoto = _requisicao('GET', f'monografias/{m.microservico_id}/', _token(self.aluno_user, m, 'aluno'))
        self.assertEqual(remoto['hash_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(remoto['status'], 'APROVADA_ORIENTADOR')
        self.assertEqual(publicacao.documento_final_id, correcao.pk)
