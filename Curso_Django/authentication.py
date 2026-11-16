from rest_framework.authentication import BasicAuthentication


class AutenticacaoBasica(BasicAuthentication):
    def authenticate_header(self, request):
        # Chamadas fetch usam a sessão e precisam mostrar o erro na página,
        # sem abrir o diálogo nativo de HTTP Basic do navegador.
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None
        return super().authenticate_header(request)
