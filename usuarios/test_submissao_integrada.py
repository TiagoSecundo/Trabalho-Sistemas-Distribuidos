"""B09/B17: integracao do CRUD academico com microservico de PDF sem precisar de rede nos testes."""
import hashlib
import io
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from monografias.models import HistoricoAcao, Monografia
from .integracao_microservico import MicroservicoIndisponivel


CONFIG_JWT = {
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': 'chave-b09-compartilhada-com-mais-de-trinta-e-dois-caracteres',
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10),
}


class FalsoMicroservico:
    def __init__(self):
        self.registro = None
        self.chamadas = []
        self.falhar_upload = False

    def __call__(self, metodo, caminho, token, *, dados=None, arquivo=None, stream=False):
        self.chamadas.append((metodo, caminho))
        if stream:
            return io.BytesIO(b'%PDF-test')
        if metodo == 'POST' and caminho == 'monografias/':
            if self.registro is None:
                self.registro = {**dados, 'id': 81, 'aluno_id': self.aluno_id, 'status': 'RASCUNHO',
                                 'hash_sha256': '', 'submetida_em': None}
            return dict(self.registro)
        if self.registro is None:
            raise AssertionError('Tentativa sem registro remoto.')
        if metodo == 'GET' and caminho == 'monografias/81/':
            return dict(self.registro)
        if metodo == 'PATCH' and caminho == 'monografias/81/':
            self.registro.update(dados)
            return dict(self.registro)
        if metodo == 'POST' and caminho == 'monografias/81/upload/':
            if self.falhar_upload:
                raise MicroservicoIndisponivel('Falha simulada no upload.')
            arquivo.seek(0)
            self.registro['hash_sha256'] = hashlib.sha256(arquivo.read()).hexdigest()
            arquivo.seek(0)
            return dict(self.registro)
        if metodo == 'POST' and caminho == 'monografias/81/submeter/':
            self.registro.update(status='SUBMETIDA', submetida_em=timezone.now().isoformat())
            return dict(self.registro)
        if metodo == 'POST' and caminho == 'monografias/81/aprovar-orientador/':
            self.registro['status'] = 'APROVADA_ORIENTADOR'
            return dict(self.registro)
        if metodo == 'POST' and caminho == 'monografias/81/solicitar-ajustes/':
            self.registro['status'] = 'AJUSTES_SOLICITADOS'
            return dict(self.registro)
        raise AssertionError(f'Chamada remota inesperada: {metodo} {caminho}')


@override_settings(SIMPLE_JWT=CONFIG_JWT, MICROSERVICO_API_URL='http://127.0.0.1:8001/api/',
                   MICROSERVICO_TIMEOUT=5, MICROSERVICO_MAX_UPLOAD_MB=50)
class SubmissaoIntegradaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.aluno_user = User.objects.create_user('aluno-integ')
        cls.outro_aluno_user = User.objects.create_user('outro-aluno-integ')
        cls.orientador_user = User.objects.create_user('orientador-integ')
        cls.outro_prof_user = User.objects.create_user('outro-prof-integ')
        cls.orientador = Professor.objects.create(usuario=cls.orientador_user, nome='Orientador Integ',
                                                  email='orientador-integ@example.com', departamento='D', area_pesquisa='A')
        cls.outro_prof = Professor.objects.create(usuario=cls.outro_prof_user, nome='Outro Prof Integ',
                                                  email='outro-prof-integ@example.com', departamento='D', area_pesquisa='A')
        cls.curso = Curso.objects.create(nome='Curso Integração', codigo='INT')
        cls.aluno = Aluno.objects.create(usuario=cls.aluno_user, nome='Aluno Integração',
                                        matricula='INT-1', email='aluno-integ@example.com', curso=cls.curso)
        cls.outro_aluno = Aluno.objects.create(usuario=cls.outro_aluno_user, nome='Outro Aluno',
                                              matricula='INT-2', email='outro-aluno-integ@example.com', curso=cls.curso)
        cls.m = Monografia.objects.create(titulo='Trabalho Integração', resumo='Resumo', aluno=cls.aluno,
                                          curso=cls.curso, orientador=cls.orientador)

    def setUp(self):
        self.micro = FalsoMicroservico()
        self.patch_micro = patch('usuarios.integracao_microservico._requisicao', side_effect=self.micro)
        self.patch_micro.start()
        self.addCleanup(self.patch_micro.stop)
        self.micro.registro = None
        self.micro.aluno_id = self.aluno.pk

    @staticmethod
    def pdf(conteudo=b'%PDF-1.7 teste simulado\n'):
        return SimpleUploadedFile('trabalho.pdf', conteudo, content_type='application/pdf')

    def submeter(self, user=None, arquivo=None, monografia=None):
        self.client.force_login(user or self.aluno_user)
        return self.client.post(reverse('api-submeter-pdf', args=[(monografia or self.m).pk]),
                                {'arquivo': self.pdf() if arquivo is None else arquivo})

    def test_aluno_submete_e_orientador_aprova_liberando_b10(self):
        r = self.submeter()
        self.assertEqual(r.status_code, 200, r.content)
        self.m.refresh_from_db()
        self.assertEqual(self.m.microservico_id, 81)
        self.assertEqual(self.m.status_fluxo, 'SUBMETIDA')
        self.assertIsNotNone(self.m.data_submissao)
        self.assertEqual(len(self.m.sha256), 64)
        self.assertEqual(self.micro.registro['origem_id'], self.m.pk)
        self.client.force_login(self.orientador_user)
        aprovacao = self.client.post(reverse('api-aprovar-orientador', args=[self.m.pk]))
        self.assertEqual(aprovacao.status_code, 200, aprovacao.content)
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'APROVADA_ORIENTADOR')
        self.assertTrue(HistoricoAcao.objects.filter(acao='ORIENTACAO_APROVOU').exists())
        inicio = timezone.now() + timedelta(days=3)
        banca = self.client.post(reverse('api-propor-banca', args=[self.m.pk]), {
            'inicio': inicio.isoformat(), 'fim': (inicio + timedelta(hours=1)).isoformat(),
            'modalidade': 'PRESENCIAL', 'local': 'Sala 3',
        })
        self.assertEqual(banca.status_code, 201, banca.content)

    def test_sem_aprovacao_nao_agenda(self):
        self.assertEqual(self.submeter().status_code, 200)
        self.client.force_login(self.orientador_user)
        inicio = timezone.now() + timedelta(days=3)
        resposta = self.client.post(reverse('api-propor-banca', args=[self.m.pk]), {
            'inicio': inicio.isoformat(), 'fim': (inicio + timedelta(hours=1)).isoformat(),
            'modalidade': 'PRESENCIAL', 'local': 'Sala',
        })
        self.assertEqual(resposta.status_code, 409)

    def test_professor_de_outra_monografia_nao_aprova(self):
        self.assertEqual(self.submeter().status_code, 200)
        self.client.force_login(self.outro_prof_user)
        self.assertEqual(self.client.post(reverse('api-aprovar-orientador', args=[self.m.pk])).status_code, 404)
        self.assertEqual(Monografia.objects.get(pk=self.m.pk).status_fluxo, 'SUBMETIDA')

    def test_outro_aluno_nao_submete_o_trabalho(self):
        r = self.submeter(user=self.outro_aluno_user)
        self.assertEqual(r.status_code, 404)
        self.assertIsNone(self.micro.registro)

    def test_pdf_sem_assinatura_e_rejeitado_antes_do_micro(self):
        self.assertEqual(self.submeter(arquivo=self.pdf(b'conteudo falso')).status_code, 400)
        self.assertEqual(self.micro.chamadas, [])

    def test_falha_remota_mantem_vinculo_para_nova_tentativa(self):
        self.micro.falhar_upload = True
        self.assertEqual(self.submeter().status_code, 503)
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'RASCUNHO')
        self.assertEqual(self.m.microservico_id, 81)
        self.micro.falhar_upload = False
        self.assertEqual(self.submeter().status_code, 200)
        self.assertEqual(self.micro.chamadas.count(('POST', 'monografias/')), 1)

    def test_ajustes_editaveis_e_reenvio(self):
        self.assertEqual(self.submeter().status_code, 200)
        self.client.force_login(self.orientador_user)
        r = self.client.post(reverse('api-solicitar-ajustes', args=[self.m.pk]), {'motivo': 'Corrigir metodologia'})
        self.assertEqual(r.status_code, 200, r.content)
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'AJUSTES_SOLICITADOS')
        self.assertEqual(self.m.motivo_ajustes, 'Corrigir metodologia')
        self.assertEqual(self.client.get(reverse('usuarios:trabalho', args=[self.m.pk])).status_code, 200)
        self.client.force_login(self.aluno_user)
        self.assertEqual(self.client.get(reverse('usuarios:editar-rascunho', args=[self.m.pk])).status_code, 200)
        self.assertEqual(self.client.post(reverse('api-submeter-pdf', args=[self.m.pk]),
                                          {'arquivo': self.pdf(b'%PDF-2.0 versao 2')}).status_code, 200)
        self.m.refresh_from_db()
        self.assertEqual(self.m.status_fluxo, 'SUBMETIDA')
        self.assertEqual(self.m.motivo_ajustes, '')

    def test_nao_deixa_aluno_excluir_trabalho_devolvido(self):
        self.assertEqual(self.submeter().status_code, 200)
        self.client.force_login(self.orientador_user)
        self.client.post(reverse('api-solicitar-ajustes', args=[self.m.pk]), {'motivo': 'Revisar'})
        self.client.force_login(self.aluno_user)
        r = self.client.delete(reverse('meu-rascunho-detalhe', args=[self.m.pk]))
        self.assertEqual(r.status_code, 409, r.content)
        self.assertTrue(Monografia.objects.filter(pk=self.m.pk).exists())

    def test_sincronizar_recupera_decisao_remota(self):
        self.assertEqual(self.submeter().status_code, 200)
        self.micro.registro['status'] = 'APROVADA_ORIENTADOR'
        self.client.force_login(self.aluno_user)
        r = self.client.post(reverse('api-sincronizar-submissao', args=[self.m.pk]))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Monografia.objects.get(pk=self.m.pk).status_fluxo, 'APROVADA_ORIENTADOR')

    def test_remote_claim_inconsistente_bloqueado(self):
        self.assertEqual(self.submeter().status_code, 200)
        self.micro.registro['curso_id'] = 999999
        self.client.force_login(self.aluno_user)
        self.assertEqual(self.client.post(reverse('api-sincronizar-submissao', args=[self.m.pk])).status_code, 409)

    def test_pdf_so_ao_aluno_ou_orientador(self):
        self.assertEqual(self.submeter().status_code, 200)
        self.client.force_login(self.orientador_user)
        r = self.client.get(reverse('usuarios:visualizar-pdf', args=[self.m.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b''.join(r.streaming_content), b'%PDF-test')
        self.client.force_login(self.outro_prof_user)
        self.assertEqual(self.client.get(reverse('usuarios:visualizar-pdf', args=[self.m.pk])).status_code, 403)

    def test_nao_aprova_sem_submissao(self):
        self.client.force_login(self.orientador_user)
        self.assertEqual(self.client.post(reverse('api-aprovar-orientador', args=[self.m.pk])).status_code, 409)

    def test_html_mostra_acoes_corretas(self):
        self.client.force_login(self.aluno_user)
        r = self.client.get(reverse('usuarios:trabalho', args=[self.m.pk]))
        self.assertContains(r, 'Enviar PDF e submeter ao orientador')
        self.assertNotContains(r, 'Aprovar submissão')
        self.assertEqual(self.submeter().status_code, 200)
        self.client.force_login(self.orientador_user)
        r = self.client.get(reverse('usuarios:trabalho', args=[self.m.pk]))
        self.assertContains(r, 'Aprovar submissão')
        self.assertContains(r, 'Consultar PDF no microserviço')
