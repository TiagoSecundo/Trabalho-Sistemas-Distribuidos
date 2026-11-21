"""Endpoints acadêmicos independentes do CRUD administrativo."""
from django.core.exceptions import ValidationError as ModelValidationError
from django.db.models.deletion import ProtectedError
from rest_framework import generics, serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from equipe.models import Aluno
from monografias.models import Monografia
from monografias.serializers import MonografiaSerializer
from Curso_Django.api import CRUDViewSet, Conflito
from Curso_Django.services import OperacaoNaoPermitida
from .consultas import monografias_visiveis
from .permissions import IsAcademicoOuAdministrador, IsDonoMonografia
from .roles import obter_papeis
from .services import confirmar_convite_externo, emitir_convite_externo, excluir_rascunho, salvar_rascunho


class MinhaContaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario = request.user
        return Response({
            'id': usuario.pk, 'username': usuario.get_username(),
            'email': usuario.email, 'papeis': obter_papeis(usuario),
        })


class MonografiaResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Monografia
        fields = ['id', 'titulo', 'status_fluxo']


class MinhasMonografiasView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAcademicoOuAdministrador]
    serializer_class = MonografiaResumoSerializer

    def get_queryset(self):
        return monografias_visiveis(self.request.user)


class RascunhoAlunoSerializer(MonografiaSerializer):
    class Meta(MonografiaSerializer.Meta):
        read_only_fields = list(MonografiaSerializer.Meta.read_only_fields) + ['aluno', 'curso']

    def validate(self, attrs):
        if self.instance is None:
            aluno = Aluno.objects.select_related('curso').get(usuario=self.context['request'].user)
            attrs.update(aluno=aluno, curso=aluno.curso)
        return super().validate(attrs)

    def create(self, validated_data):
        return salvar_rascunho(self.context['request'].user, validated_data)

    def update(self, instance, validated_data):
        return salvar_rascunho(self.context['request'].user, validated_data, instance)


class RascunhoAlunoViewSet(CRUDViewSet):
    permission_classes = [IsAuthenticated, IsDonoMonografia]
    serializer_class = RascunhoAlunoSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return monografias_visiveis(self.request.user, 'Aluno')

    def perform_create(self, serializer):
        # O serviço registra o evento acadêmico na mesma transação da escrita.
        self.salvar(serializer)

    def perform_update(self, serializer):
        self.salvar(serializer)

    def perform_destroy(self, instance):
        try:
            excluir_rascunho(self.request.user, instance)
        except (OperacaoNaoPermitida, ProtectedError) as exc:
            raise Conflito('Monografia não pode ser excluída neste estado.') from exc


class EmitirConviteExternoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            participacao, token = emitir_convite_externo(request.user, pk)
        except ModelValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        return Response({'token': token, 'expira_em': participacao.expira_em})


class ConfirmarConviteExternoView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, pk):
        confirmar_convite_externo(pk, request.data.get('token'))
        return Response({'confirmado': True})
