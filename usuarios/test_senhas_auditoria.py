import re

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.test import TestCase

from monografias.models import HistoricoAcao
from equipe.models import Curso


class SenhaAuditoriaTests(TestCase):
    def test_validadores_rejeitam_senhas_fracas(self):
        user = get_user_model()(username='fulano', email='fulano@example.com')
        for senha in ('abc', '123456789', 'password', 'fulano'):
            with self.subTest(senha=senha), self.assertRaises(ValidationError):
                validate_password(senha, user)
        validate_password('UmaSenha-Longa_83!paraTeste', user)

    def test_recuperacao_allauth_troca_senha_e_invalida_token(self):
        user = get_user_model().objects.create_user('recuperacao', email='recuperacao@example.test', password='SenhaInicial-123!')
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        resposta = self.client.post('/accounts/password/reset/', {'email': user.email})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r'https?://[^\s]+/accounts/password/reset/key/[^\s]+', mail.outbox[0].body).group(0)
        from urllib.parse import urlparse
        caminho = urlparse(link).path
        tela = self.client.get(caminho, follow=True)
        destino = tela.redirect_chain[-1][0] if tela.redirect_chain else caminho
        self.assertEqual(tela.status_code, 200)
        resposta = self.client.post(destino, {'password1': 'NovaSenha-Longa_93!teste', 'password2': 'NovaSenha-Longa_93!teste'})
        self.assertEqual(resposta.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NovaSenha-Longa_93!teste'))
        self.assertFalse(user.check_password('SenhaInicial-123!'))
        self.client.logout()
        repetido = self.client.get(caminho, follow=True)
        self.assertNotContains(repetido, 'name="password1"')

    def test_admin_e_api_registram_ator_acao_data_e_id_na_exclusao(self):
        admin = get_user_model().objects.create_superuser('admin-auditoria', 'admin@example.test', 'Senha-123!teste')
        self.client.force_login(admin)
        resposta = self.client.post('/admin/equipe/curso/add/', {'nome': 'Curso auditado', 'codigo': 'AUD', '_save': 'Salvar'})
        self.assertEqual(resposta.status_code, 302)
        curso = Curso.objects.get(codigo='AUD')
        self.assertTrue(HistoricoAcao.objects.filter(ator=admin, acao='ADMIN_CRIACAO', detalhes__id=curso.pk).exists())
        pk = curso.pk
        self.assertEqual(self.client.delete(f'/api/cursos/{pk}/').status_code, 204)
        evento = HistoricoAcao.objects.get(acao='CRUD_EXCLUSAO')
        self.assertEqual(evento.ator, admin)
        self.assertEqual(evento.detalhes['id'], pk)
        self.assertEqual(set(evento.detalhes), {'modelo', 'id'})
