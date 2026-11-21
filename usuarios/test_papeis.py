"""Regressões do escopo: staff, vínculos acadêmicos e fronteiras de acesso."""
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import RequestFactory, TestCase
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from monografias.models import Banca, HistoricoAcao, MembroExterno, Monografia, ParticipacaoBanca
from usuarios.roles import obter_papeis


class PapeisEscopoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser('gestor-escopo', password='senha-escopo-123')
        cls.staff = User.objects.create_user('staff-sem-papel', is_staff=True)
        cls.docente = User.objects.create_user('docente-staff', password='senha-escopo-123', is_staff=True)
        cls.aluno_user = User.objects.create_user('aluno-escopo', is_staff=True)
        cls.prof = Professor.objects.create(usuario=cls.docente, nome='Orientadora', email='docente@escopo.example', departamento='D', area_pesquisa='A')
        cls.outro_prof = Professor.objects.create(nome='Outra orientação', email='outra@escopo.example', departamento='D', area_pesquisa='A')
        cls.curso = Curso.objects.create(nome='Sistemas de Informação', codigo='ESC')
        cls.outro_curso = Curso.objects.create(nome='Outro curso', codigo='OUTESC')
        cls.aluno = Aluno.objects.create(usuario=cls.aluno_user, nome='Aluno', matricula='ESC001', email='aluno@escopo.example', curso=cls.curso)
        cls.outro_aluno = Aluno.objects.create(nome='Outro aluno', matricula='ESC002', email='outro@escopo.example', curso=cls.outro_curso)
        cls.orientada = Monografia.objects.create(titulo='Minha orientação', resumo='R', aluno=cls.aluno, curso=cls.curso, orientador=cls.prof, status_fluxo='APROVADA_ORIENTADOR')
        cls.avaliada = Monografia.objects.create(titulo='Minha participação como avaliador', resumo='R', aluno=cls.outro_aluno, curso=cls.outro_curso, orientador=cls.outro_prof, status_fluxo='APROVADA_ORIENTADOR')
        cls.privada = Monografia.objects.create(titulo='Trabalho sem vínculo', resumo='R', aluno=cls.outro_aluno, curso=cls.outro_curso, orientador=cls.outro_prof)
        cls.banca = Banca.objects.create(monografia=cls.avaliada, inicio=timezone.now()+timedelta(days=5), fim=timezone.now()+timedelta(days=5, hours=1), local='Sala')
        ParticipacaoBanca.objects.create(banca=cls.banca, professor=cls.prof)
        externo = MembroExterno.objects.create(nome='Convidado', email='ext@escopo.example', instituicao='Instituição')
        cls.convite = ParticipacaoBanca.objects.create(banca=cls.banca, membro_externo=externo)
        banca_orientada = Banca.objects.create(monografia=cls.orientada, inicio=timezone.now()+timedelta(days=6), fim=timezone.now()+timedelta(days=6, hours=1), local='Sala')
        cls.convite_orientado = ParticipacaoBanca.objects.create(banca=banca_orientada, membro_externo=externo)

    def test_staff_nao_libera_nenhum_crud_administrativo(self):
        self.client.force_login(self.staff)
        self.assertEqual(obter_papeis(self.staff), [])
        for recurso in ('alunos', 'professores', 'cursos', 'monografias', 'bancas', 'membros-externos', 'participacoes-banca', 'avaliacoes'):
            for metodo, sufixo in (('get', ''), ('post', ''), ('patch', '1/'), ('delete', '1/')):
                with self.subTest(recurso=recurso, metodo=metodo):
                    response = getattr(self.client, metodo)(f'/api/{recurso}/{sufixo}', content_type='application/json')
                    self.assertEqual(response.status_code, 403)
        for rota in ('/equipe/', '/monografias/', '/usuarios/painel/administrador/'):
            self.assertEqual(self.client.get(rota).status_code, 403)
        self.assertNotContains(self.client.get('/'), 'Acessar cadastros')

    def test_professor_staff_recebe_painel_docente_e_nao_admin(self):
        self.client.force_login(self.docente)
        self.assertEqual(self.client.get('/api/usuarios/me/').json()['papeis'], ['Professor'])
        response = self.client.get('/usuarios/painel/')
        self.assertContains(response, 'Orientações e bancas')
        self.assertContains(response, 'Minhas participações')
        self.assertNotContains(response, 'Gerenciar cadastros')
        self.assertNotContains(response, 'href="/equipe/"')
        self.assertNotIn('alunos', self.client.get('/api/').json())
        self.assertEqual(self.client.get('/api/alunos/').status_code, 403)
        self.assertEqual(self.client.get('/usuarios/painel/administrador/').status_code, 403)

    def test_aluno_staff_continua_aluno_e_so_ve_trabalhos_proprios(self):
        self.client.force_login(self.aluno_user)
        self.assertEqual(obter_papeis(self.aluno_user), ['Aluno'])
        self.assertContains(self.client.get('/usuarios/painel/'), 'Meu percurso acadêmico')
        dados = self.client.get('/api/usuarios/monografias/').json()['results']
        self.assertEqual([item['id'] for item in dados], [self.orientada.pk])
        self.assertEqual(self.client.get(f'/usuarios/trabalhos/{self.privada.pk}/').status_code, 404)
        self.assertEqual(self.client.get('/api/alunos/').status_code, 403)

    def test_grupos_academicos_sem_vinculo_nao_concedem_acesso(self):
        for nome in ('Alunos', 'Professores', 'Coordenadores'):
            self.staff.groups.add(Group.objects.create(name=nome))
        self.assertEqual(obter_papeis(self.staff), [])

    def test_grupo_administradores_e_explicito_e_nao_apaga_papel_academico(self):
        grupo = Group.objects.create(name='Administradores')
        self.docente.groups.add(grupo)
        self.assertEqual(obter_papeis(self.docente), ['Professor', 'Administrador'])
        self.client.force_login(self.docente)
        self.assertEqual(self.client.get('/api/alunos/').status_code, 200)
        self.docente.groups.remove(grupo)
        self.assertEqual(self.client.get('/api/alunos/').status_code, 403)
        self.admin.is_active = False
        self.admin.save(update_fields=['is_active'])
        self.assertEqual(obter_papeis(self.admin), [])

    def test_admin_django_tambem_exige_papel_administrativo(self):
        self.docente.user_permissions.add(Permission.objects.get(codename='view_aluno'))
        request = RequestFactory().get('/admin/')
        request.user = self.docente
        self.assertFalse(admin.site.has_permission(request))
        self.client.force_login(self.docente)
        self.assertEqual(self.client.get('/admin/equipe/aluno/').status_code, 302)
        request.user = self.admin
        self.assertTrue(admin.site.has_permission(request))
        self.client.logout()
        response = self.client.post('/admin/login/?next=/admin/', {'username': self.docente.username, 'password': 'senha-escopo-123', 'next': '/admin/'})
        self.assertContains(response, 'Esta conta não possui acesso administrativo.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_coordenacao_depende_do_curso_e_revoga_na_troca(self):
        self.curso.coordenador = self.prof
        self.curso.save(update_fields=['coordenador'])
        self.assertEqual(obter_papeis(self.docente), ['Professor', 'Coordenador'])
        self.client.force_login(self.docente)
        response = self.client.get('/usuarios/painel/coordenador/')
        self.assertContains(response, self.orientada.titulo)
        self.assertNotContains(response, self.avaliada.titulo)
        self.assertEqual(self.client.get(f'/usuarios/trabalhos/{self.avaliada.pk}/?perfil=coordenador').status_code, 404)
        self.curso.coordenador = self.outro_prof
        self.curso.save(update_fields=['coordenador'])
        self.assertEqual(self.client.get('/usuarios/painel/coordenador/').status_code, 403)

    def test_participacao_libera_leitura_e_filtro_mas_nao_outros_trabalhos(self):
        self.client.force_login(self.docente)
        dados = self.client.get('/api/usuarios/monografias/').json()['results']
        self.assertEqual({item['id'] for item in dados}, {self.orientada.pk, self.avaliada.pk})
        self.assertEqual(self.client.get(f'/usuarios/trabalhos/{self.avaliada.pk}/?perfil=professor').status_code, 200)
        self.assertEqual(self.client.get(f'/usuarios/trabalhos/{self.privada.pk}/').status_code, 404)
        response = self.client.get('/usuarios/painel/professor/?vinculo=bancas')
        self.assertEqual([item.pk for item in response.context['pagina']], [self.avaliada.pk])
        response = self.client.get('/usuarios/painel/professor/?vinculo=orientacoes')
        self.assertEqual([item.pk for item in response.context['pagina']], [self.orientada.pk])
        self.banca.status = 'CANCELADA'
        self.banca.save(update_fields=['status'])
        self.assertEqual(self.client.get(f'/usuarios/trabalhos/{self.avaliada.pk}/').status_code, 404)

    def test_orientador_pode_emitir_convite_sem_ser_coordenador(self):
        self.client.force_login(self.docente)
        response = self.client.post(f'/api/usuarios/convites/{self.convite_orientado.pk}/emitir/')
        self.assertEqual(response.status_code, 200, response.content)
        response = self.client.post(f'/usuarios/convites/{self.convite_orientado.pk}/emitir/')
        self.assertContains(response, 'codigo-convite')
        self.assertTrue(HistoricoAcao.objects.filter(ator=self.docente, acao='CONVITE_EXTERNO_EMITIDO').exists())

    def test_avaliador_e_coorientador_nao_podem_emitir_convite(self):
        self.client.force_login(self.docente)
        for coorientador in (None, self.prof):
            self.avaliada.coorientador = coorientador
            self.avaliada.save(update_fields=['coorientador'])
            self.assertEqual(self.client.post(f'/api/usuarios/convites/{self.convite.pk}/emitir/').status_code, 403)
            self.assertEqual(self.client.get(f'/usuarios/convites/{self.convite.pk}/emitir/').status_code, 404)

    def test_vincular_conta_pelo_formulario_libera_perfil_imediatamente(self):
        self.client.force_login(self.admin)
        dados = {'nome': 'Aluno vinculado', 'matricula': 'ESC003', 'email': 'vinculo@escopo.example', 'curso': self.curso.pk, 'usuario': self.staff.pk}
        pagina = self.client.get('/equipe/adicionar/?tipo=aluno')
        self.assertContains(pagina, 'id_usuario')
        response = self.client.post('/equipe/adicionar/?tipo=aluno', dados)
        self.assertEqual(response.status_code, 302, response.content)
        aluno = Aluno.objects.get(usuario=self.staff)
        self.assertTrue(HistoricoAcao.objects.filter(ator=self.admin, objeto=f'equipe.Aluno:{aluno.pk}', acao='CRUD_CRIACAO').exists())
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/api/usuarios/me/').json()['papeis'], ['Aluno'])
        self.assertEqual(self.client.patch(f'/api/alunos/{aluno.pk}/', {'usuario': self.admin.pk}, content_type='application/json').status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.patch(f'/api/alunos/{aluno.pk}/', {'usuario': None}, content_type='application/json').status_code, 200)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get('/api/usuarios/me/').json()['papeis'], [])
        self.assertEqual(self.client.get('/usuarios/painel/aluno/').status_code, 403)

    def test_conta_ja_vinculada_nao_pode_ser_duplicada(self):
        self.client.force_login(self.admin)
        response = self.client.post('/api/professores/', {'nome': 'Duplicado', 'usuario': self.docente.pk, 'email': 'duplicado@escopo.example', 'departamento': 'D', 'area_pesquisa': 'A'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Professor.objects.filter(usuario=self.docente).count(), 1)
