from equipe.models import Aluno, Professor, Curso


def obter_papeis(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return []

    if usuario.is_staff:
        return ['Administrador']

    grupos = set(
        usuario.groups.values_list('name', flat=True)
    )

    papeis = []

    if (
        'Alunos' in grupos
        and Aluno.objects.filter(usuario=usuario).exists()
    ):
        papeis.append('Aluno')

    if (
        'Professores' in grupos
        and Professor.objects.filter(usuario=usuario).exists()
    ):
        papeis.append('Professor')

    if (
        'Coordenadores' in grupos
        and Professor.objects.filter(usuario=usuario).exists()
        and Curso.objects.filter(
            coordenador__usuario=usuario
        ).exists()
    ):
        papeis.append('Coordenador')

    return papeis