"""API privada do B12; o catálogo público pertence ao B13."""
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from monografias.models import DocumentoComplementar, Monografia, Publicacao
from .publicacao import (
    TIPOS_ENVIAVEIS, abrir_documento_verificado, conferir_documento, enviar_documento, exigir_acesso,
)
from .submissao_api import executar


class EnvioDocumentoSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=TIPOS_ENVIAVEIS)
    arquivo = serializers.FileField()


class ConferenciaDocumentoSerializer(serializers.Serializer):
    decisao = serializers.ChoiceField(choices=('aceitar', 'rejeitar'))
    confirmacao = serializers.BooleanField(default=False)
    motivo = serializers.CharField(max_length=2000, allow_blank=True, default='')


def dados_documento(documento):
    return {
        'id': documento.pk, 'monografia_id': documento.monografia_id, 'tipo': documento.tipo,
        'nome_original': documento.nome_original, 'sha256': documento.sha256,
        'tamanho_bytes': documento.tamanho_bytes, 'enviado_por': documento.enviado_por_id,
        'enviado_em': documento.enviado_em, 'vigente': documento.vigente,
        'decisao': documento.decisao, 'conferido_por': documento.conferido_por_id,
        'conferido_em': documento.conferido_em, 'motivo': documento.motivo,
        'origem_microservico_id': documento.origem_microservico_id,
        'download': reverse('api-documento-arquivo', args=[documento.monografia_id, documento.pk]),
    }


def dados_publicacao(publicacao):
    if publicacao is None:
        return None
    return {
        'id': publicacao.pk, 'monografia_id': publicacao.monografia_id,
        'banca_id': publicacao.banca_id, 'documento_final_id': publicacao.documento_final_id,
        'termo_id': publicacao.termo_id, 'sha256': publicacao.sha256,
        'publicado_em': publicacao.publicado_em, 'publicado_por': publicacao.publicado_por_id,
        'resultado_banca': publicacao.resultado_banca, 'media_banca': str(publicacao.media_banca),
        'download_final': reverse('api-documento-arquivo', args=[publicacao.monografia_id, publicacao.documento_final_id]),
    }


def monografia_documental(usuario, pk):
    monografia = get_object_or_404(Monografia.objects.select_related('aluno', 'orientador', 'curso__coordenador'), pk=pk)
    exigir_acesso(usuario, monografia)
    return monografia


def resposta_arquivo(usuario, pk, documento_id):
    monografia = monografia_documental(usuario, pk)
    documento = get_object_or_404(DocumentoComplementar, monografia=monografia, pk=documento_id)
    arquivo = executar(abrir_documento_verificado, documento)
    resposta = FileResponse(arquivo, as_attachment=True, filename=f'{documento.tipo.lower()}-{documento.pk}.pdf', content_type='application/pdf')
    resposta['Cache-Control'] = 'private, no-store'
    resposta['X-Content-Type-Options'] = 'nosniff'
    return resposta


@method_decorator(never_cache, name='dispatch')
class DocumentosView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        monografia = monografia_documental(request.user, pk)
        return Response({'monografia_id': pk, 'status_fluxo': monografia.status_fluxo,
                         'documentos': [dados_documento(d) for d in monografia.documentos.all()],
                         'publicacao': dados_publicacao(Publicacao.objects.filter(monografia=monografia).first())})

    def post(self, request, pk):
        entrada = EnvioDocumentoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        documento = executar(enviar_documento, request.user, pk, **entrada.validated_data)
        return Response(dados_documento(documento), status=201)


@method_decorator(never_cache, name='dispatch')
class ConferirDocumentoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request, pk, documento_id):
        entrada = ConferenciaDocumentoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        documento, publicacao = executar(conferir_documento, request.user, pk, documento_id, **entrada.validated_data)
        return Response({'documento': dados_documento(documento), 'publicacao': dados_publicacao(publicacao)})


@method_decorator(never_cache, name='dispatch')
class DocumentoArquivoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, documento_id):
        return resposta_arquivo(request.user, pk, documento_id)
