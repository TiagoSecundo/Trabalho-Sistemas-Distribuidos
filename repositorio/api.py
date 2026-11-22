"""API anônima de leitura, sem reutilizar serializers administrativos."""
from django.contrib.postgres.search import SearchQuery
from django.core.paginator import EmptyPage, Paginator
from django.db.models import F, Q
from django.db.models.functions import ExtractYear, Lower
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from equipe.models import Curso, Professor
from usuarios.publicacao import abrir_documento_verificado
from usuarios.submissao_api import executar
from .consultas import publicacoes_publicas

ORDENACOES = {
    '-data_defesa': ('-banca__inicio', '-pk'),
    'data_defesa': ('banca__inicio', 'pk'),
    'titulo': (Lower('monografia__titulo'), 'pk'),
    '-titulo': (Lower('monografia__titulo').desc(), '-pk'),
    '-data_publicacao': ('-publicado_em', '-pk'),
}


class FiltrosSerializer(serializers.Serializer):
    busca = serializers.CharField(max_length=200, required=False)
    titulo = serializers.CharField(max_length=200, required=False)
    autor = serializers.CharField(max_length=200, required=False)
    orientador = serializers.IntegerField(min_value=1, required=False)
    curso = serializers.IntegerField(min_value=1, required=False)
    ano_defesa = serializers.IntegerField(min_value=1900, max_value=9998, required=False)
    palavras_chave = serializers.CharField(max_length=300, required=False)
    ordering = serializers.ChoiceField(choices=list(ORDENACOES), default='-data_defesa')
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50, default=12)

    def validate_palavras_chave(self, value):
        termos = [t.strip() for t in value.split(',') if t.strip()]
        if not termos or len(termos) > 10:
            raise serializers.ValidationError('Informe de uma a dez palavras-chave separadas por vírgulas.')
        return termos


def validar_filtros(params):
    invalidos = set(params) - set(FiltrosSerializer().fields) - {'format'}
    if invalidos:
        raise serializers.ValidationError({k: 'Filtro desconhecido.' for k in sorted(invalidos)})
    repetidos = [k for k in params if len(params.getlist(k)) > 1]
    if repetidos:
        raise serializers.ValidationError({k: 'Informe este filtro apenas uma vez.' for k in repetidos})
    serializer = FiltrosSerializer(data={k: v for k, v in params.items() if v.strip() and k != 'format'})
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def filtrar_publicacoes(filtros):
    qs = publicacoes_publicas()
    for campo, lookup in (('titulo', 'monografia__titulo__icontains'), ('autor', 'monografia__aluno__nome__icontains'),
                          ('orientador', 'monografia__orientador_id'), ('curso', 'monografia__curso_id')):
        if campo in filtros:
            qs = qs.filter(**{lookup: filtros[campo]})
    if 'ano_defesa' in filtros:
        qs = qs.annotate(ano_local=ExtractYear('banca__inicio', tzinfo=timezone.get_default_timezone())).filter(ano_local=filtros['ano_defesa'])
    for termo in filtros.get('palavras_chave', []):
        qs = qs.filter(monografia__palavras_chave__icontains=termo)
    if busca := filtros.get('busca'):
        qs = qs.filter(
            Q(monografia__titulo__icontains=busca) | Q(monografia__resumo__icontains=busca)
            | Q(monografia__aluno__nome__icontains=busca) | Q(monografia__orientador__nome__icontains=busca)
            | Q(monografia__palavras_chave__icontains=busca)
            | Q(indice__vetor=SearchQuery(busca, config='portuguese', search_type='websearch'), indice__sha256=F('sha256'))
        )
    return qs.order_by(*ORDENACOES[filtros['ordering']])


def dados_publicos(publicacao):
    m = publicacao.monografia
    defesa = timezone.localtime(publicacao.banca.inicio, timezone.get_default_timezone())
    return {
        'id': m.pk, 'titulo': m.titulo, 'resumo': m.resumo, 'palavras_chave': m.palavras_chave,
        'autor': m.aluno.nome, 'orientador': {'id': m.orientador_id, 'nome': m.orientador.nome},
        'curso': {'id': m.curso_id, 'nome': m.curso.nome}, 'data_defesa': defesa.isoformat(),
        'ano_defesa': defesa.year, 'data_publicacao': publicacao.publicado_em,
        'arquivo': {'url': reverse('repositorio-api:arquivo', args=[m.pk]),
                    'download': reverse('repositorio-api:arquivo', args=[m.pk])+'?download=1',
                    'sha256': publicacao.sha256, 'tamanho_bytes': publicacao.documento_final.tamanho_bytes},
        'url': reverse('repositorio:detalhe', args=[m.pk]),
    }


class LeituraPublica(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    http_method_names = ['get', 'head', 'options']

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-cache'
        return response


class MonografiasPublicas(LeituraPublica):
    def get(self, request):
        filtros = validar_filtros(request.query_params)
        paginator = Paginator(filtrar_publicacoes(filtros), filtros['page_size'])
        try:
            pagina = paginator.page(filtros['page'])
        except EmptyPage as exc:
            raise NotFound('Página não encontrada.') from exc

        def link(numero):
            params = request.query_params.copy()
            params['page'] = numero
            return request.path+'?'+params.urlencode()

        return Response({'count': paginator.count, 'page': pagina.number, 'pages': paginator.num_pages,
            'next': link(pagina.next_page_number()) if pagina.has_next() else None,
            'previous': link(pagina.previous_page_number()) if pagina.has_previous() else None,
            'results': [dados_publicos(p) for p in pagina]})


class MonografiaPublica(LeituraPublica):
    def get(self, request, pk):
        return Response(dados_publicos(get_object_or_404(publicacoes_publicas(), monografia_id=pk)))


class CursosPublicos(LeituraPublica):
    def get(self, request):
        ids = publicacoes_publicas().values('monografia__curso_id')
        return Response(list(Curso.objects.filter(pk__in=ids).order_by(Lower('nome'), 'pk').values('id', 'nome')))


class OrientadoresPublicos(LeituraPublica):
    def get(self, request):
        ids = publicacoes_publicas().values('monografia__orientador_id')
        return Response(list(Professor.objects.filter(pk__in=ids).order_by(Lower('nome'), 'pk').values('id', 'nome')))


class ArquivoPublico(LeituraPublica):
    def get(self, request, pk):
        if request.query_params.get('download', '0') not in ('0', '1'):
            raise serializers.ValidationError({'download': 'Use 1 para baixar ou 0 para ler.'})
        publicacao = get_object_or_404(publicacoes_publicas(), monografia_id=pk)
        arquivo = executar(abrir_documento_verificado, publicacao.documento_final)
        resposta = FileResponse(arquivo, content_type='application/pdf',
            as_attachment=request.query_params.get('download') == '1', filename=f'monografia-{pk}.pdf')
        resposta['X-Content-Type-Options'] = 'nosniff'
        resposta['Content-Security-Policy'] = 'sandbox'
        return resposta
