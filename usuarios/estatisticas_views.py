from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

from .estatisticas import cursos_visiveis, papel_estatisticas


@never_cache
@login_required
@require_safe
def dashboard(request):
    papel = papel_estatisticas(request.user)
    if papel is None:
        raise PermissionDenied
    return render(request, 'usuarios/estatisticas.html', {
        'cursos': cursos_visiveis(request.user, papel),
    })
