from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .roles import eh_administrador


def administrador_required(view):
    @login_required
    @wraps(view)
    def protegida(request, *args, **kwargs):
        if not eh_administrador(request.user):
            raise PermissionDenied('Esta área exige acesso administrativo.')
        return view(request, *args, **kwargs)

    return protegida
