"""API de propostas, participantes e confirmações de banca (B10)."""
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError
from rest_framework import serializers, status
from equipe.models import Professor
from monografias.models import MembroExterno
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Curso_Django.api import Conflito
from Curso_Django.services import OperacaoNaoPermitida
from .agendamento import (
    adicionar_participante, cancelar_proposta, propor_banca, responder_convite_interno, retirar_participante,
)


class DadosPropostaSerializer(serializers.Serializer):
    inicio = serializers.DateTimeField()
    fim = serializers.DateTimeField()
    modalidade = serializers.ChoiceField(choices=['PRESENCIAL', 'REMOTA', 'HIBRIDA'])
    local = serializers.CharField(required=False, allow_blank=True, default='')
    link = serializers.URLField(required=False, allow_blank=True, default='')


class DadosParticipanteSerializer(serializers.Serializer):
    professor = serializers.PrimaryKeyRelatedField(queryset=Professor.objects.all(), required=False, allow_null=True)
    membro_externo = serializers.PrimaryKeyRelatedField(queryset=MembroExterno.objects.all(), required=False, allow_null=True)
    papel = serializers.ChoiceField(choices=['PRESIDENTE', 'AVALIADOR', 'SUPLENTE'], default='AVALIADOR')


class RespostaSerializer(serializers.Serializer):
    acao = serializers.ChoiceField(choices=['confirmar', 'recusar'])


def tratar(exc):
    if isinstance(exc, OperacaoNaoPermitida):
        raise Conflito(str(exc)) from exc
    if hasattr(exc, 'message_dict'):
        raise serializers.ValidationError(exc.message_dict) from exc
    raise serializers.ValidationError(exc.messages) from exc


class ProporBancaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        dados = DadosPropostaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        try:
            banca = propor_banca(request.user, pk, dados.validated_data)
        except (ModelValidationError, OperacaoNaoPermitida) as exc:
            tratar(exc)
        except IntegrityError as exc:
            raise Conflito('Já existe uma proposta ativa para este trabalho.') from exc
        return Response({'id': banca.pk, 'status': banca.status}, status=status.HTTP_201_CREATED)


class AdicionarParticipanteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        dados = DadosParticipanteSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        try:
            participante = adicionar_participante(request.user, pk, dados.validated_data)
        except (ModelValidationError, OperacaoNaoPermitida) as exc:
            tratar(exc)
        except IntegrityError as exc:
            raise Conflito('Participante já incluído nesta banca.') from exc
        return Response({'id': participante.pk, 'status': participante.convite_status}, status=status.HTTP_201_CREATED)


class ResponderConviteInternoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        dados = RespostaSerializer(data=request.data)
        dados.is_valid(raise_exception=True)
        try:
            agendada = responder_convite_interno(request.user, pk, dados.validated_data['acao'] == 'confirmar')
        except (ModelValidationError, OperacaoNaoPermitida) as exc:
            tratar(exc)
        return Response({'respondido': True, 'banca_agendada': agendada})


class RemoverParticipanteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            retirar_participante(request.user, pk)
        except (ModelValidationError, OperacaoNaoPermitida) as exc:
            tratar(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CancelarPropostaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            banca = cancelar_proposta(request.user, pk)
        except (ModelValidationError, OperacaoNaoPermitida) as exc:
            tratar(exc)
        except IntegrityError as exc:
            raise Conflito('Já existe uma proposta ativa para este trabalho.') from exc
        return Response({'id': banca.pk, 'status': banca.status})
