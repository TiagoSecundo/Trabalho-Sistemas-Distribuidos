from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe
from .api import dados_publicos
from .consultas import publicacoes_publicas


@require_safe
def catalogo(request):
    return render(request, 'repositorio/catalogo.html')


@require_safe
def detalhe(request, pk):
    publicacao = get_object_or_404(publicacoes_publicas(), monografia_id=pk)
    return render(request, 'repositorio/detalhe.html', {'trabalho': dados_publicos(publicacao)})
