from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods, require_safe

from Curso_Django import interface
from .interface import recurso


@staff_member_required(login_url='login')
@require_safe
def index(request, tipo='monografias'):
    return interface.listar(request, recurso(tipo), 'monografias.html')


@staff_member_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def adicionar(request, tipo='monografias'):
    return interface.formulario(request, recurso(tipo), template='adicionar_monografia.html')


@staff_member_required(login_url='login')
@require_safe
def detalhes(request, pk, tipo='monografias'):
    return interface.detalhes(request, recurso(tipo), pk, 'detalhes.html')


@staff_member_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def editar(request, pk, tipo='monografias'):
    return interface.formulario(request, recurso(tipo), pk, 'adicionar_monografia.html')


@staff_member_required(login_url='login')
@require_http_methods(['GET', 'POST'])
def excluir(request, pk, tipo='monografias'):
    return interface.excluir(request, recurso(tipo), pk, 'confirmar_exclusao.html')
