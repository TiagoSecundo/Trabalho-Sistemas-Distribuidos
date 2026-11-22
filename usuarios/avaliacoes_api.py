"""Ações de avaliação (B11) sem ampliar o CRUD administrativo."""
from decimal import Decimal

from django.core.exceptions import ValidationError as ModelValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Curso_Django.api import Conflito
from Curso_Django.services import OperacaoNaoPermitida
from monografias.models import Avaliacao, ParticipacaoBanca
from .services import (
    finalizar_resultado_banca, registrar_avaliacao_propria, registrar_defesa_realizada,
)


class DadosAvaliacaoSerializer(serializers.Serializer):
    nota = serializers.DecimalField(max_digits=4, decimal_places=2,
                                     min_value=Decimal('0'), max_value=Decimal('10'))
    parecer = serializers.CharField(allow_blank=False)
    recomendacao = serializers.ChoiceField(choices=Avaliacao.RECOMENDACOES)


def _erro_validacao(exc):
    if hasattr(exc, 'message_dict'):
        return serializers.ValidationError(exc.message_dict)
    return serializers.ValidationError(exc.messages)


class RegistrarDefesaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            banca = registrar_defesa_realizada(request.user, pk)
        except ModelValidationError as exc:
            raise _erro_validacao(exc) from exc
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc
        return Response({'banca_id': banca.pk, 'status': banca.status,
                         'status_fluxo': 'DEFESA_REALIZADA'})


class MinhaAvaliacaoView(APIView):
    permission_classes = [IsAuthenticated]

    def _participacao(self, request, pk):
        return get_object_or_404(
            ParticipacaoBanca, pk=pk, professor__usuario=request.user,
        )

    def get(self, request, pk):
        participacao = self._participacao(request, pk)
        avaliacao = Avaliacao.objects.filter(participacao=participacao).first()
        if avaliacao is None:
            return Response({'participacao_id': pk, 'avaliacao': None})
        return Response({
            'participacao_id': pk,
            'avaliacao': {'nota': str(avaliacao.nota), 'parecer': avaliacao.parecer,
                          'recomendacao': avaliacao.recomendacao,
                          'finalizada_em': avaliacao.finalizada_em},
        })

    def post(self, request, pk):
        self._participacao(request, pk)  # evita expor registros alheios
        entrada = DadosAvaliacaoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            avaliacao, criada = registrar_avaliacao_propria(request.user, pk, entrada.validated_data)
        except ModelValidationError as exc:
            raise _erro_validacao(exc) from exc
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc
        return Response({
            'id': avaliacao.pk, 'participacao_id': pk,
            'nota': str(avaliacao.nota), 'parecer': avaliacao.parecer,
            'recomendacao': avaliacao.recomendacao,
        }, status=status.HTTP_201_CREATED if criada else status.HTTP_200_OK)


class FinalizarBancaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            media, resultado = finalizar_resultado_banca(request.user, pk)
        except ModelValidationError as exc:
            raise _erro_validacao(exc) from exc
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc
        return Response({'banca_id': pk, 'media': str(media), 'resultado': resultado})
