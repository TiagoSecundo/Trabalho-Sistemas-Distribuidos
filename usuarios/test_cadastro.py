"""Cadastro público, persistência da identidade e integração com usuários."""
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from equipe.models import Aluno, Professor
from monografias.models import HistoricoAcao


@override_settings(ACCOUNT_RATE_LIMITS=False)
class CadastroTests(TestCase):
    def dados(self, **alteracoes):
        return {
            'username': 'nova-conta', 'email': 'nova@cadastro.example',
            'password1': 'Conta-academica-2026!', 'password2': 'Conta-academica-2026!',
            **alteracoes,
        }

    def test_cadastro_persiste_conta_senha_email_e_aparece_no_crud_de_usuarios(self):
        response = self.client.post('/accounts/signup/', self.dados(), follow=True)
        self.assertRedirects(response, '/usuarios/painel/')
        self.assertContains(response, 'Conta criada com sucesso')
        usuario = get_user_model().objects.get(username='nova-conta')
        self.assertTrue(usuario.check_password(self.dados()['password1']))
        self.assertNotEqual(usuario.password, self.dados()['password1'])
        self.assertTrue(EmailAddress.objects.filter(user=usuario, email='nova@cadastro.example', primary=True).exists())
        evento = HistoricoAcao.objects.get(ator=usuario, acao='USUARIO_CRIADO')
        self.assertEqual(evento.detalhes, {'modelo': 'auth.User', 'id': usuario.pk})
        self.assertEqual(self.client.get('/api/usuarios/me/').json()['id'], usuario.pk)
        self.client.post('/sair/')
        response = self.client.post('/accounts/login/', {'login': usuario.email, 'password': self.dados()['password1']})
        self.assertRedirects(response, '/usuarios/painel/')
        admin = get_user_model().objects.create_superuser('admin-cadastro', 'admin@cadastro.example', 'Senha-admin-2026!')
        self.client.force_login(admin)
        response = self.client.get('/admin/auth/user/?q=nova-conta')
        self.assertContains(response, 'nova-conta')
        self.assertContains(response, f'/admin/auth/user/{usuario.pk}/change/')

    def test_tela_integrada_ao_projeto_com_formulario_e_erros_visiveis(self):
        response = self.client.get('/accounts/signup/')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'action="/accounts/signup/"')
        self.assertContains(response, 'csrfmiddlewaretoken')
        self.assertContains(response, '/accounts/login/')
        response = self.client.post('/accounts/signup/', self.dados(password2='Senha-divergente-2026!'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('password2', response.context['form'].errors)
        self.assertContains(response, 'Confira os campos indicados')
        self.assertContains(response, 'value="nova-conta"')
        self.assertContains(response, 'value="nova@cadastro.example"')
        self.assertNotContains(response, 'value="Conta-academica-2026!"')
        self.assertFalse(get_user_model().objects.filter(username='nova-conta').exists())

    def test_duplicados_nao_criam_ou_sobrescrevem_usuario(self):
        usuario = get_user_model().objects.create_user('existente', 'existente@cadastro.example', 'Senha-anterior-2026!')
        for dados, campo in ((self.dados(username='existente'), 'username'), (self.dados(email=usuario.email), 'email')):
            with self.subTest(campo=campo):
                response = self.client.post('/accounts/signup/', dados)
                self.assertEqual(response.status_code, 200)
                self.assertIn(campo, response.context['form'].errors)
                self.assertEqual(get_user_model().objects.count(), 1)
        usuario.refresh_from_db()
        self.assertTrue(usuario.check_password('Senha-anterior-2026!'))

    def test_cadastro_publico_nao_concede_privilegios(self):
        self.client.post('/accounts/signup/', self.dados(is_staff='true', is_superuser='true', perfil='Administrador', groups=['Coordenadores']))
        usuario = get_user_model().objects.get(username='nova-conta')
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(usuario.groups.exists())
        self.assertFalse(Aluno.objects.filter(usuario=usuario).exists())
        self.assertFalse(Professor.objects.filter(usuario=usuario).exists())
        self.assertEqual(self.client.get('/api/alunos/').status_code, 403)

    def test_cadastro_exige_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.get('/accounts/signup/')
        self.assertEqual(client.post('/accounts/signup/', self.dados()).status_code, 403)
        self.assertFalse(get_user_model().objects.exists())
        response = client.post('/accounts/signup/', self.dados(), HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertRedirects(response, '/usuarios/painel/')

    def test_senha_fraca_e_campos_vazios_nao_criam_conta(self):
        for dados in ({}, self.dados(password1='123', password2='123')):
            with self.subTest(vazio=not dados):
                response = self.client.post('/accounts/signup/', dados)
                self.assertContains(response, 'Sua conta ainda não foi criada')
                self.assertTrue(response.context['form'].errors)
                self.assertFalse(get_user_model().objects.exists())

    def test_cadastro_e_atomico_se_auditoria_falhar(self):
        with patch('usuarios.forms.registrar_acao', side_effect=RuntimeError('Falha de teste')):
            with self.assertRaises(RuntimeError):
                self.client.post('/accounts/signup/', self.dados())
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(EmailAddress.objects.exists())
        self.assertFalse(HistoricoAcao.objects.exists())

    def test_cadastro_nao_redireciona_para_site_externo(self):
        response = self.client.post('/accounts/signup/?next=https://example.com/', self.dados())
        self.assertRedirects(response, '/usuarios/painel/')
