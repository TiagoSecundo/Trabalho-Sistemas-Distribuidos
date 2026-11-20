from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .roles import obter_papeis


@login_required
def painel(request):
    usuario = request.user

    context = {
        'usuario': usuario,
        'papeis': obter_papeis(usuario),
    }

    return render(
        request,
        'usuarios/painel.html',
        context
    )