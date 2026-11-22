"""API de avaliação de membros externos com código temporário e uso único."""
from django.core.exceptions import ValidationError as ModelValidationError
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Curso_Django.api import Conflito
from Curso_Django.services import OperacaoNaoPermitida
from .avaliacoes_api import DadosAvaliacaoSerializer, _erro_validacao
from .avaliacao_externa import emitir_codigo_avaliacao_externa, registrar_avaliacao_externa


class DadosAvaliacaoExternaSerializer(DadosAvaliacaoSerializer):
    codigo = serializers.CharField(max_length=512, trim_whitespace=False, write_only=True)


class EmitirCodigoAvaliacaoExternaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            participacao, codigo = emitir_codigo_avaliacao_externa(request.user, pk)
        except ModelValidationError as exc:
            raise _erro_validacao(exc) from exc
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc
        return Response({'codigo': codigo, 'expira_em': participacao.avaliacao_expira_em})


class RegistrarAvaliacaoExternaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, pk):
        entrada = DadosAvaliacaoExternaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            avaliacao, criada = registrar_avaliacao_externa(
                pk, entrada.validated_data['codigo'], entrada.validated_data,
            )
        except ModelValidationError as exc:
            raise _erro_validacao(exc) from exc
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc
        return Response({'id': avaliacao.pk, 'participacao_id': pk,
                         'nota': str(avaliacao.nota), 'recomendacao': avaliacao.recomendacao},
                        status=status.HTTP_201_CREATED if criada else status.HTTP_200_OK)
