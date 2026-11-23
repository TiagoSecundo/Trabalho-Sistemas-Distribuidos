from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Avg, Count, F, OuterRef, Q, Subquery
from django.db.models.functions import ExtractYear

from equipe.models import Curso
from monografias.models import Banca
from .consultas import monografias_visiveis
from .roles import obter_papeis


APROVADAS = ('APROVADA', 'APROVADA_COM_RESSALVAS', 'CORRECOES_ENTREGUES', 'PUBLICADA')


def papel_estatisticas(usuario):
    papeis = obter_papeis(usuario)
    return next((papel for papel in ('Administrador', 'Coordenador') if papel in papeis), None)


def cursos_visiveis(usuario, papel):
    if papel == 'Administrador':
        return Curso.objects.all()
    if papel == 'Coordenador':
        return Curso.objects.filter(coordenador__usuario=usuario)
    return Curso.objects.none()


def trabalhos_visiveis(usuario, papel):
    return monografias_visiveis(usuario, papel).order_by()


def por_curso(trabalhos):
    return list(
        trabalhos.filter(data_submissao__isnull=False)
        .values(grupo_id=F('curso_id'), rotulo=F('curso__nome'))
        .annotate(total=Count('pk')).order_by('rotulo', 'grupo_id')
    )


def por_orientador(trabalhos):
    return list(
        trabalhos.filter(data_submissao__isnull=False)
        .values(grupo_id=F('orientador_id'), rotulo=F('orientador__nome'))
        .annotate(total=Count('pk')).order_by('rotulo', 'grupo_id')
    )


def defesas_realizadas(trabalhos):
    # Uma defesa por monografia. Em caso de duplicidade histórica, usa a banca
    # realizada mais recente por início e desempata pela maior chave primária.
    ultima_banca = Banca.objects.filter(monografia_id=OuterRef('pk'), status='REALIZADA')
    inicio = ultima_banca.order_by('-inicio', '-pk').values('inicio')[:1]
    return trabalhos.annotate(inicio_defesa=Subquery(inicio)).filter(inicio_defesa__isnull=False)


def por_ano_defesa(trabalhos):
    return list(
        defesas_realizadas(trabalhos)
        .values(ano=ExtractYear('inicio_defesa', tzinfo=ZoneInfo(settings.TIME_ZONE)))
        .annotate(total=Count('pk')).order_by('ano')
    )


def taxa_aprovacao(trabalhos):
    resultados = defesas_realizadas(trabalhos).aggregate(
        aprovadas=Count('pk', filter=Q(status_fluxo__in=APROVADAS)),
        reprovadas=Count('pk', filter=Q(status_fluxo='REPROVADA')),
    )
    total = resultados['aprovadas'] + resultados['reprovadas']
    return {
        **resultados, 'total': total,
        'percentual': round(100 * resultados['aprovadas'] / total, 2) if total else None,
    }


def tempo_medio(trabalhos):
    resultado = defesas_realizadas(trabalhos).filter(
        inicio_defesa__gte=F('data_submissao'),
    ).aggregate(total=Count('pk'), duracao=Avg(F('inicio_defesa') - F('data_submissao')))
    duracao = resultado['duracao']
    return {
        'total': resultado['total'],
        'dias': round(duracao.total_seconds() / 86400, 2) if duracao is not None else None,
    }
