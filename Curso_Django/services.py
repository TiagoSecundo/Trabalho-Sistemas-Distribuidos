from django.db import transaction


class OperacaoNaoPermitida(Exception):
    """Conflito entre uma operação e o estado persistido do registro."""


class ServicoCRUD:
    @classmethod
    def validar_alteracao(cls, instance):
        pass

    @classmethod
    @transaction.atomic
    def criar(cls, model, dados):
        instance = model(**dados)
        instance.full_clean()
        instance.save()
        return instance

    @classmethod
    @transaction.atomic
    def atualizar(cls, instance, dados):
        instance = type(instance).objects.select_for_update().get(pk=instance.pk)
        cls.validar_alteracao(instance)
        for campo, valor in dados.items():
            setattr(instance, campo, valor)
        instance.full_clean()
        instance.save()
        return instance

    @classmethod
    @transaction.atomic
    def excluir(cls, instance):
        instance = type(instance).objects.select_for_update().get(pk=instance.pk)
        cls.validar_alteracao(instance)
        instance.delete()
