from rest_framework.authentication import BasicAuthentication


class AutenticacaoBasica(BasicAuthentication):
    @staticmethod
    def requisicao_de_navegador(request):
        return (
            'Sec-Fetch-Mode' in request.headers
            or 'text/html' in request.headers.get('Accept', '').lower()
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

    def authenticate(self, request):
        # A sessão do Django determina a identidade no navegador. Basic pode
        # ficar retido após logout e não deve substituir o usuário nem o CSRF.
        if request._request.user.is_authenticated or self.requisicao_de_navegador(request):
            return None
        return super().authenticate(request)

    def authenticate_header(self, request):
        if self.requisicao_de_navegador(request):
            return None
        return super().authenticate_header(request)
