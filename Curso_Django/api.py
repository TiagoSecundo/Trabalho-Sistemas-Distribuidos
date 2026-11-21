from copy import copy

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from rest_framework import serializers, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated

from .services import OperacaoNaoPermitida, ServicoCRUD
from usuarios.auditoria import registrar_acao
from usuarios.permissions import IsAdministrador


class Conflito(APIException):
    status_code = 409
    default_detail = 'A operação conflita com registros vinculados ou com o estado atual.'
    default_code = 'conflito'


class ModelSerializerValidado(serializers.ModelSerializer):
    """Reutiliza as validações dos models também na entrada JSON."""

    service_class = ServicoCRUD

    def create(self, validated_data):
        return self.service_class.criar(self.Meta.model, validated_data)

    def update(self, instance, validated_data):
        return self.service_class.atualizar(instance, validated_data)

    def to_internal_value(self, data):
        if isinstance(data, dict):
            permitidos = {name for name, field in self.fields.items() if not field.read_only}
            invalidos = set(data) - permitidos - {'csrfmiddlewaretoken'}
            if invalidos:
                raise serializers.ValidationError({name: 'Campo desconhecido ou somente leitura.' for name in sorted(invalidos)})
        return super().to_internal_value(data)

    def validate(self, attrs):
        instance = copy(self.instance) if self.instance else self.Meta.model()
        for name, value in attrs.items():
            setattr(instance, name, value)
        try:
            instance.full_clean()
        except ModelValidationError as exc:
            errors = exc.message_dict if hasattr(exc, 'message_dict') else {'non_field_errors': exc.messages}
            if '__all__' in errors:
                errors['non_field_errors'] = errors.pop('__all__')
            raise serializers.ValidationError(errors) from exc
        return attrs


class CRUDViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdministrador]

    def perform_create(self, serializer):
        with transaction.atomic():
            self.salvar(serializer)
            registrar_acao(self.request.user, serializer.instance, 'CRUD_CRIACAO')

    def perform_update(self, serializer):
        with transaction.atomic():
            self.salvar(serializer)
            registrar_acao(self.request.user, serializer.instance, 'CRUD_ATUALIZACAO')

    def salvar(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError as exc:
            raise Conflito('Já existe um registro equivalente ou um vínculo foi alterado. Atualize os dados e tente novamente.') from exc
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc
        except ModelValidationError as exc:
            raise serializers.ValidationError(getattr(exc, 'message_dict', exc.messages)) from exc

    def perform_destroy(self, instance):
        try:
            with transaction.atomic():
                self.serializer_class.service_class.excluir(instance)
                registrar_acao(self.request.user, instance, 'CRUD_EXCLUSAO')
        except ProtectedError as exc:
            raise Conflito('Este registro está em uso e não pode ser excluído.') from exc
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc
