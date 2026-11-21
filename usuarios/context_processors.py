from .roles import eh_administrador


def acesso(request):
    return {'acesso_administrativo': eh_administrador(request.user)}
