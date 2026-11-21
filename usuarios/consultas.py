"""Escopos compartilhados pelas páginas e pela API acadêmica."""
from django.db.models import Q

from monografias.models import Monografia
from .roles import obter_papeis


def monografias_visiveis(usuario, papel=None):
    papeis = obter_papeis(usuario)
    if papel is not None:
        papeis = [papel] if papel in papeis else []
    queryset = Monografia.objects.select_related('aluno', 'curso', 'orientador', 'coorientador')
    if 'Administrador' in papeis:
        return queryset
    filtros = Q(pk__in=[])
    if 'Aluno' in papeis:
        filtros |= Q(aluno__usuario=usuario)
    if 'Professor' in papeis:
        filtros |= Q(orientador__usuario=usuario) | Q(coorientador__usuario=usuario)
    if 'Coordenador' in papeis:
        filtros |= Q(curso__coordenador__usuario=usuario)
    return queryset.filter(filtros).distinct()
