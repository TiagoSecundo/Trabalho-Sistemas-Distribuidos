from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods, require_safe

from Curso_Django import interface
from .interface import recurso


@staff_member_required(login_url='login')
@require_safe
def index(request):
    return interface.listar(request, recurso(request.GET.get('tipo', 'aluno')), 'equipe.html')


@staff_member_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def adicionar(request):
    return interface.formulario(request, recurso(request.GET.get('tipo', 'aluno')), template='adicionar_equipe.html')


@staff_member_required(login_url='login')
@require_safe
def detalhes(request, tipo, pk):
    return interface.detalhes(request, recurso(tipo), pk)


@staff_member_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def editar(request, tipo, pk):
    return interface.formulario(request, recurso(tipo), pk, 'adicionar_equipe.html')


@staff_member_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def excluir(request, tipo, pk):
    return interface.excluir(request, recurso(tipo), pk)
