from django.test import SimpleTestCase, override_settings


@override_settings(SECURE_SSL_REDIRECT=False,
                   ADMIN_ALLOWED_NETWORKS=['127.0.0.1/32', '::1/128', '192.168.3.188/24'],
                   ADMIN_TRUSTED_PROXIES=[])
class RedeAdministrativaTests(SimpleTestCase):
    def test_bloqueia_todos_os_perimetros_inclusive_sem_login(self):
        for url in ('/admin/login/', '/equipe/', '/monografias/', '/api/cursos/', '/api/avaliacoes/1/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, REMOTE_ADDR='203.0.113.9').status_code, 403)

    def test_rede_local_e_loopback_passam_para_autenticacao(self):
        for ip in ('127.0.0.1', '::1', '192.168.3.188', '192.168.3.1'):
            self.assertEqual(self.client.get('/equipe/', REMOTE_ADDR=ip).status_code, 302)

    def test_cabecalho_forjado_sem_proxy_nao_autoriza(self):
        self.assertEqual(self.client.get('/equipe/', REMOTE_ADDR='203.0.113.9',
            HTTP_X_FORWARDED_FOR='192.168.3.188').status_code, 403)

    @override_settings(ADMIN_TRUSTED_PROXIES=['10.0.0.0/24'])
    def test_proxy_confiavel_usa_primeiro_salto_nao_confiavel(self):
        self.assertEqual(self.client.get('/equipe/', REMOTE_ADDR='10.0.0.2',
            HTTP_X_FORWARDED_FOR='192.168.3.188, 10.0.0.1').status_code, 302)
        self.assertEqual(self.client.get('/equipe/', REMOTE_ADDR='10.0.0.2',
            HTTP_X_FORWARDED_FOR='192.168.3.188, 203.0.113.9').status_code, 403)
        for cadeia in ('', 'desconhecido', '192.168.3.188:80'):
            self.assertEqual(self.client.get('/equipe/', REMOTE_ADDR='10.0.0.2',
                HTTP_X_FORWARDED_FOR=cadeia).status_code, 403)

    @override_settings(ADMIN_ALLOWED_NETWORKS=[])
    def test_lista_vazia_bloqueia(self):
        self.assertEqual(self.client.get('/equipe/').status_code, 403)

    def test_ip_invalido_bloqueia(self):
        self.assertEqual(self.client.get('/equipe/', REMOTE_ADDR='invalido').status_code, 403)

    def test_painel_academico_e_repositorio_nao_exigem_rede(self):
        self.assertEqual(self.client.get('/usuarios/painel/', REMOTE_ADDR='203.0.113.9').status_code, 302)
        self.assertEqual(self.client.get('/repositorio/', REMOTE_ADDR='203.0.113.9').status_code, 200)
