"""Perímetro administrativo por rede, independente da autenticação."""
from ipaddress import ip_address, ip_network

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse


def _pertence(endereco, redes):
    return any(endereco in rede for rede in redes)


class RedeAdministrativaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Configuração inválida interrompe a inicialização, sem liberar acesso.
        self.redes = [ip_network(r.strip(), strict=False) for r in settings.ADMIN_ALLOWED_NETWORKS if r.strip()]
        self.proxies = [ip_network(r.strip(), strict=False) for r in settings.ADMIN_TRUSTED_PROXIES if r.strip()]

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        from Curso_Django.api import CRUDViewSet
        from usuarios.roles import eh_administrador
        classe = getattr(view_func, 'cls', None)
        administrativo = (
            bool(set(request.resolver_match.app_names) & {'admin', 'equipe', 'monografias'})
            or (isinstance(classe, type) and issubclass(classe, CRUDViewSet))
            or (eh_administrador(request.user) and request.path.startswith(('/usuarios/', '/api/usuarios/')))
        )
        if not administrativo:
            return None
        try:
            cliente = ip_address(request.META.get('REMOTE_ADDR', ''))
            if _pertence(cliente, self.proxies):
                cadeia = request.META.get('HTTP_X_FORWARDED_FOR', '')
                if not cadeia or len(cadeia) > 2048:
                    raise ValueError('Proxy sem cadeia válida.')
                # O proxy precisa sobrescrever/anexar o IP real. Ignora tudo à
                # esquerda do primeiro salto não confiável, impedindo spoofing.
                saltos = [ip_address(s.strip()) for s in cadeia.split(',')]
                while saltos and _pertence(cliente, self.proxies):
                    cliente = saltos.pop()
            if _pertence(cliente, self.redes):
                return None
        except ValueError:
            pass
        mensagem = 'A área administrativa exige acesso pela rede autorizada ou VPN.'
        if request.path.startswith('/api/'):
            return JsonResponse({'detail': mensagem}, status=403)
        return HttpResponseForbidden(mensagem, content_type='text/plain; charset=utf-8')
