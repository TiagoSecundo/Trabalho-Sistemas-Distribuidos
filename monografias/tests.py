from datetime import timedelta
from decimal import Decimal
import base64

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from equipe.models import Aluno, Curso, Professor
from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca


class CRUDAcademicoTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user('administrador', password='senha-de-teste', is_staff=True, is_superuser=True)
        cls.usuario = get_user_model().objects.create_user('aluno', password='senha-de-teste')
        cls.professor = Professor.objects.create(nome='Ana', email='ana@example.com', departamento='Computação', area_pesquisa='Redes')
        cls.outro_professor = Professor.objects.create(nome='Bruno', email='bruno@example.com', departamento='Computação', area_pesquisa='IA')
        cls.curso = Curso.objects.create(nome='Computação', codigo='CC', coordenador=cls.professor)
        cls.aluno = Aluno.objects.create(nome='Carla', matricula='2026001', email='carla@example.com', curso=cls.curso)
        cls.monografia = Monografia.objects.create(titulo='Sistemas distribuídos', resumo='Resumo', aluno=cls.aluno, curso=cls.curso, orientador=cls.professor)
        cls.inicio = timezone.now().replace(microsecond=0) + timedelta(days=7)
        cls.fim = cls.inicio + timedelta(hours=1)
        cls.banca = Banca.objects.create(monografia=cls.monografia, inicio=cls.inicio, fim=cls.fim, local='Sala 1', status='AGENDADA')
        cls.participacao = ParticipacaoBanca.objects.create(banca=cls.banca, professor=cls.professor)

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def monografia_payload(self):
        return {'titulo': 'Nova monografia', 'resumo': 'Resumo do trabalho', 'aluno': self.aluno.pk, 'curso': self.curso.pk, 'orientador': self.professor.pk, 'palavras_chave': ['Django', 'TCC']}

    def banca_payload(self, monografia=None):
        return {'monografia': monografia or self.monografia.pk, 'inicio': self.inicio.isoformat(), 'fim': self.fim.isoformat(), 'local': 'Sala 2', 'modalidade': 'PRESENCIAL'}

    def avaliacao_payload(self):
        return {'participacao': self.participacao.pk, 'nota': '8.50', 'parecer': 'Trabalho adequado.', 'recomendacao': 'APROVADA'}

    def verificar_crud(self, recurso, model, payload, campo, valor):
        url = f'/api/{recurso}/'
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data['id']
        detalhe = f'{url}{pk}/'
        self.assertEqual(self.client.get(detalhe).status_code, 200)
        lista = self.client.get(url)
        self.assertEqual(lista.status_code, 200)
        self.assertIn(pk, [item['id'] for item in lista.data['results']])
        response = self.client.put(detalhe, payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.patch(detalhe, {campo: valor}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(getattr(model.objects.get(pk=pk), campo), valor)
        response = self.client.delete(detalhe)
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(model.objects.filter(pk=pk).exists())
        self.assertEqual(self.client.get(detalhe).status_code, 404)

    def test_crud_aluno(self):
        self.verificar_crud('alunos', Aluno, {'nome': 'Daniel', 'matricula': '2026002', 'email': 'daniel@example.com', 'curso': self.curso.pk}, 'nome', 'Daniel Silva')

    def test_crud_professor(self):
        self.verificar_crud('professores', Professor, {'nome': 'Eduarda', 'email': 'eduarda@example.com', 'departamento': 'Computação', 'area_pesquisa': 'Banco de dados'}, 'nome', 'Eduarda Silva')

    def test_crud_curso(self):
        self.verificar_crud('cursos', Curso, {'nome': 'Engenharia', 'codigo': 'ENG'}, 'nome', 'Engenharia de Software')

    def test_crud_monografia_e_varios_trabalhos_por_aluno(self):
        self.verificar_crud('monografias', Monografia, self.monografia_payload(), 'titulo', 'Título atualizado')
        self.assertTrue(Monografia.objects.filter(pk=self.monografia.pk).exists())

    def test_crud_banca(self):
        monografia = Monografia.objects.create(titulo='Outra', resumo='Resumo', aluno=self.aluno, curso=self.curso, orientador=self.professor, status_fluxo='APROVADA_ORIENTADOR')
        self.verificar_crud('bancas', Banca, self.banca_payload(monografia.pk), 'local', 'Sala 3')

    def test_crud_avaliacao(self):
        self.verificar_crud('avaliacoes', Avaliacao, self.avaliacao_payload(), 'nota', Decimal('9.00'))

    def test_crud_membro_externo(self):
        self.verificar_crud('membros-externos', MembroExterno, {'nome': 'Felipe', 'email': 'felipe@example.com', 'instituicao': 'Universidade'}, 'instituicao', 'Instituto')

    def test_crud_participacao_banca(self):
        monografia = Monografia.objects.create(titulo='Outra banca', resumo='Resumo', aluno=self.aluno, curso=self.curso, orientador=self.professor, status_fluxo='APROVADA_ORIENTADOR')
        banca = Banca.objects.create(monografia=monografia, inicio=self.inicio, fim=self.fim, local='Sala 2')
        self.verificar_crud('participacoes-banca', ParticipacaoBanca, {'banca': banca.pk, 'professor': self.outro_professor.pk}, 'papel', 'PRESIDENTE')

    def test_api_exige_autenticacao_e_perfil_administrativo(self):
        for recurso in ('alunos', 'professores', 'cursos', 'monografias', 'bancas', 'avaliacoes', 'membros-externos', 'participacoes-banca'):
            with self.subTest(recurso=recurso):
                self.client.force_authenticate(None)
                self.assertEqual(self.client.get(f'/api/{recurso}/').status_code, 401)
                self.assertEqual(self.client.post(f'/api/{recurso}/', {}, format='json').status_code, 401)
                self.client.force_authenticate(self.usuario)
                self.assertEqual(self.client.get(f'/api/{recurso}/').status_code, 403)
                self.assertEqual(self.client.post(f'/api/{recurso}/', {}, format='json').status_code, 403)

    def test_autenticacao_por_sessao_exige_csrf_para_escrita(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.get('/api/cursos/').status_code, 200)
        self.assertEqual(client.post('/api/cursos/', {'nome': 'Teste', 'codigo': 'TESTE'}).status_code, 403)

    def test_formulario_da_api_aceita_csrf_valido(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.get('/api/cursos/', HTTP_ACCEPT='text/html')
        self.assertEqual(response.status_code, 200)
        token = client.cookies['csrftoken'].value
        response = client.post('/api/cursos/', {'nome': 'Curso pela API', 'codigo': 'WEB', 'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertTrue(Curso.objects.filter(codigo='WEB').exists())

    def test_autenticacao_basica_e_credencial_invalida(self):
        self.client.force_authenticate(None)
        credencial = base64.b64encode(b'administrador:senha-de-teste').decode()
        self.client.credentials(HTTP_AUTHORIZATION='Basic ' + credencial)
        self.assertEqual(self.client.get('/api/cursos/').status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION='Basic ' + base64.b64encode(b'administrador:incorreta').decode())
        self.assertEqual(self.client.get('/api/cursos/').status_code, 401)

    def test_recursos_inexistentes_retornam_404(self):
        for recurso in ('alunos', 'professores', 'cursos', 'monografias', 'bancas', 'avaliacoes', 'membros-externos', 'participacoes-banca'):
            with self.subTest(recurso=recurso):
                url = f'/api/{recurso}/999999/'
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(self.client.patch(url, {}, format='json').status_code, 404)
                self.assertEqual(self.client.delete(url).status_code, 404)

    def test_matricula_codigo_e_email_professor_unicos(self):
        casos = [
            ('alunos', {'nome': 'Outro', 'email': 'outro@example.com', 'matricula': self.aluno.matricula, 'curso': self.curso.pk}),
            ('cursos', {'nome': 'Outro', 'codigo': self.curso.codigo}),
            ('professores', {'nome': 'Outro', 'email': self.professor.email, 'departamento': 'X', 'area_pesquisa': 'Y'}),
        ]
        for recurso, payload in casos:
            with self.subTest(recurso=recurso):
                self.assertEqual(self.client.post(f'/api/{recurso}/', payload, format='json').status_code, 400)

    def test_dados_obrigatorios_e_relacionamentos_invalidos(self):
        for recurso in ('alunos', 'professores', 'cursos', 'monografias', 'bancas', 'avaliacoes'):
            self.assertEqual(self.client.post(f'/api/{recurso}/', {}, format='json').status_code, 400)
        payload = self.monografia_payload()
        payload['aluno'] = 999999
        self.assertEqual(self.client.post('/api/monografias/', payload, format='json').status_code, 400)

    def test_monografia_valida_curso_orientadores_e_palavras_chave(self):
        curso = Curso.objects.create(nome='Outro', codigo='OUTRO')
        for campo, valor in [('curso', curso.pk), ('coorientador', self.professor.pk), ('palavras_chave', 'não é lista'), ('palavras_chave', [''])]:
            with self.subTest(campo=campo, valor=valor):
                payload = self.monografia_payload()
                payload[campo] = valor
                response = self.client.post('/api/monografias/', payload, format='json')
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Monografia.objects.count(), 1)

    def test_aluno_nao_pode_trocar_curso_com_monografia_vinculada(self):
        curso = Curso.objects.create(nome='Outro', codigo='OUTRO')
        response = self.client.patch(f'/api/alunos/{self.aluno.pk}/', {'curso': curso.pk}, format='json')
        self.assertEqual(response.status_code, 400)
        self.aluno.refresh_from_db()
        self.assertEqual(self.aluno.curso_id, self.curso.pk)

    def test_campos_de_processo_nao_podem_ser_alterados_pelo_crud(self):
        for campo, valor in [('status_fluxo', 'PUBLICADA'), ('data_publicacao', '2026-11-15'), ('arquivo_pdf', 'segredo.pdf'), ('sha256', 'inventado')]:
            response = self.client.patch(f'/api/monografias/{self.monografia.pk}/', {campo: valor}, format='json')
            self.assertEqual(response.status_code, 400, response.data)

    def test_banca_valida_intervalo_local_e_unicidade(self):
        monografia = Monografia.objects.create(titulo='Outra', resumo='Resumo', aluno=self.aluno, curso=self.curso, orientador=self.professor)
        for campo, alteracao in [('fim', {'fim': self.inicio.isoformat()}), ('link', {'modalidade': 'REMOTA', 'link': ''}), ('local', {'local': ''})]:
            payload = self.banca_payload(monografia.pk)
            payload.update(alteracao)
            response = self.client.post('/api/bancas/', payload, format='json')
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn(campo, response.data)
        self.assertEqual(self.client.post('/api/bancas/', self.banca_payload(), format='json').status_code, 400)
        self.assertEqual(Banca.objects.count(), 1)

    def test_patch_banca_valida_intervalo_com_campos_existentes(self):
        response = self.client.patch(f'/api/bancas/{self.banca.pk}/', {'fim': self.inicio.isoformat()}, format='json')
        self.assertEqual(response.status_code, 400)
        self.banca.refresh_from_db()
        self.assertEqual(self.banca.fim, self.fim)

    def test_participacao_exige_um_unico_tipo_de_membro(self):
        monografia = Monografia.objects.create(titulo='Outra banca', resumo='Resumo', aluno=self.aluno, curso=self.curso, orientador=self.professor, status_fluxo='APROVADA_ORIENTADOR')
        banca = Banca.objects.create(monografia=monografia, inicio=self.inicio, fim=self.fim, local='Sala 2')
        ParticipacaoBanca.objects.create(banca=banca, professor=self.professor)
        externo = MembroExterno.objects.create(nome='Externo', email='externo@example.com', instituicao='Instituto')
        for valores in ({}, {'professor': self.professor.pk, 'membro_externo': externo.pk}, {'professor': self.professor.pk}):
            response = self.client.post('/api/participacoes-banca/', {'banca': banca.pk, **valores}, format='json')
            self.assertEqual(response.status_code, 400, response.data)
        response = self.client.post('/api/participacoes-banca/', {'banca': banca.pk, 'membro_externo': externo.pk}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn('token_hash', response.data)

    def test_avaliacao_valida_nota_e_unicidade(self):
        for nota in ('-0.01', '10.01', 'NaN', '8.555'):
            payload = self.avaliacao_payload()
            payload['nota'] = nota
            self.assertEqual(self.client.post('/api/avaliacoes/', payload, format='json').status_code, 400)
        self.assertEqual(self.client.post('/api/avaliacoes/', self.avaliacao_payload(), format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/avaliacoes/', self.avaliacao_payload(), format='json').status_code, 400)

    def test_participacao_avaliada_nao_pode_trocar_de_avaliador(self):
        self.client.post('/api/avaliacoes/', self.avaliacao_payload(), format='json')
        response = self.client.patch(f'/api/participacoes-banca/{self.participacao.pk}/', {'professor': self.outro_professor.pk}, format='json')
        self.assertEqual(response.status_code, 400)

    def test_exclusao_protege_historico_academico(self):
        self.client.post('/api/avaliacoes/', self.avaliacao_payload(), format='json')
        for recurso, instance in [('cursos', self.curso), ('professores', self.professor), ('alunos', self.aluno), ('monografias', self.monografia), ('bancas', self.banca), ('participacoes-banca', self.participacao)]:
            with self.subTest(recurso=recurso):
                self.assertEqual(self.client.delete(f'/api/{recurso}/{instance.pk}/').status_code, 409)
                self.assertTrue(type(instance).objects.filter(pk=instance.pk).exists())

    def test_publicada_banca_realizada_e_avaliacao_finalizada_nao_sao_alteradas(self):
        self.monografia.status_fluxo = 'PUBLICADA'
        self.monografia.save(update_fields=['status_fluxo'])
        self.banca.status = 'REALIZADA'
        self.banca.save(update_fields=['status'])
        avaliacao = Avaliacao.objects.create(participacao=self.participacao, nota=8, parecer='Adequado', recomendacao='APROVADA', finalizada_em=timezone.now())
        for recurso, instance, payload in [('monografias', self.monografia, {'titulo': 'Mudou'}), ('bancas', self.banca, {'local': 'Mudou'}), ('avaliacoes', avaliacao, {'nota': '9.00'})]:
            with self.subTest(recurso=recurso):
                url = f'/api/{recurso}/{instance.pk}/'
                self.assertEqual(self.client.patch(url, payload, format='json').status_code, 409)
                self.assertEqual(self.client.delete(url).status_code, 409)

    def test_constraints_tambem_protegem_gravacao_direta(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Banca.objects.create(monografia=self.monografia, inicio=self.inicio, fim=self.fim, local='Duplicada', status='AGENDADA')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ParticipacaoBanca.objects.create(banca=self.banca)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Avaliacao.objects.create(participacao=self.participacao, nota=11, parecer='Inválida', recomendacao='APROVADA')

    def test_listagem_tem_busca_ordenacao_e_paginacao(self):
        response = self.client.get('/api/professores/?search=Bruno&ordering=-nome')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.outro_professor.pk)
        Professor.objects.bulk_create([Professor(nome=f'Professor {i:02}', email=f'p{i}@example.com', departamento='D', area_pesquisa='A') for i in range(21)])
        response = self.client.get('/api/professores/')
        self.assertEqual(len(response.data['results']), 20)
        self.assertIsNotNone(response.data['next'])
        self.assertEqual(len(self.client.get('/api/professores/?page=2').data['results']), 3)

    def test_telas_legadas_protegidas_e_adaptadas(self):
        client = Client()
        self.assertEqual(client.get('/').status_code, 200)
        self.assertEqual(client.get('/equipe/').status_code, 302)
        client.force_login(self.admin)
        for url in ('/equipe/', '/equipe/adicionar/', '/equipe/adicionar/?tipo=professor', '/equipe/adicionar/?tipo=curso', '/monografias/', '/monografias/adicionar/', reverse('monografias:detalhes', args=[self.monografia.pk])):
            with self.subTest(url=url):
                self.assertEqual(client.get(url).status_code, 200)
        self.assertContains(client.get('/equipe/'), self.aluno.nome)
        self.assertContains(client.get('/monografias/'), self.professor.nome)

    def test_formulario_salva_redireciona_edita_e_exclui(self):
        client = Client()
        client.force_login(self.admin)
        payload = self.monografia_payload()
        payload['palavras_chave'] = '["Django"]'
        response = client.post('/monografias/adicionar/', payload)
        self.assertEqual(response.status_code, 302)
        monografia = Monografia.objects.get(titulo=payload['titulo'])
        self.assertRedirects(response, reverse('monografias:detalhes', args=[monografia.pk]))
        payload['titulo'] = 'Editada pelo formulário'
        self.assertEqual(client.post(reverse('monografias:editar', args=[monografia.pk]), payload).status_code, 302)
        monografia.refresh_from_db()
        self.assertEqual(monografia.titulo, payload['titulo'])
        url = reverse('monografias:excluir', args=[monografia.pk])
        self.assertEqual(client.get(url).status_code, 200)
        self.assertTrue(Monografia.objects.filter(pk=monografia.pk).exists())
        self.assertEqual(client.post(url).status_code, 302)
        self.assertFalse(Monografia.objects.filter(pk=monografia.pk).exists())

    def test_formulario_nao_ignora_validacao_do_model(self):
        client = Client()
        client.force_login(self.admin)
        payload = self.monografia_payload()
        payload['palavras_chave'] = '[]'
        payload['coorientador'] = self.professor.pk
        response = client.post('/monografias/adicionar/', payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Monografia.objects.count(), 1)

    def test_formulario_aceita_palavras_chave_opcionais(self):
        client = Client()
        client.force_login(self.admin)
        payload = self.monografia_payload()
        payload['palavras_chave'] = ''
        response = client.post('/monografias/adicionar/', payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Monografia.objects.get(titulo=payload['titulo']).palavras_chave, [])
