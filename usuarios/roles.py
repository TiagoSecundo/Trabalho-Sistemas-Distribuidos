"""Papéis acadêmicos vêm dos vínculos; staff não é autorização de negócio."""
from equipe.models import Aluno, Professor, Curso


def eh_administrador(usuario):
    return bool(
        usuario.is_authenticated and usuario.is_active
        and (usuario.is_superuser or usuario.groups.filter(name='Administradores').exists())
    )


def obter_papeis(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return []

    papeis = []
    if Aluno.objects.filter(usuario=usuario).exists():
        papeis.append('Aluno')
    if Professor.objects.filter(usuario=usuario).exists():
        papeis.append('Professor')
    if Curso.objects.filter(coordenador__usuario=usuario).exists():
        papeis.append('Coordenador')
    if eh_administrador(usuario):
        papeis.append('Administrador')
    return papeis


def pode_convidar_para_banca(usuario, monografia):
    papeis = obter_papeis(usuario)
    return (
        'Administrador' in papeis
        or ('Professor' in papeis and monografia.orientador.usuario_id == usuario.pk)
        or ('Coordenador' in papeis and monografia.curso.coordenador_id is not None
            and monografia.curso.coordenador.usuario_id == usuario.pk)
    )
