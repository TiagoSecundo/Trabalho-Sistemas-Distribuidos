from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import Avaliacao, Banca, DocumentoComplementar, MembroExterno, Monografia, ParticipacaoBanca, Publicacao
from .services import MonografiaService
from Curso_Django.services import OperacaoNaoPermitida


@admin.register(Monografia)
class MonografiaAdmin(admin.ModelAdmin):
    exclude = ['arquivo_pdf']

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or obj.status_fluxo in ('RASCUNHO', 'AJUSTES_SOLICITADOS'))

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (obj is None or (obj.status_fluxo == 'RASCUNHO' and obj.microservico_id is None))

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if change:
            atual = Monografia.objects.select_for_update().get(pk=obj.pk)
            try:
                MonografiaService.validar_alteracao(atual)
            except OperacaoNaoPermitida as exc:
                raise PermissionDenied(str(exc)) from exc
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        try:
            MonografiaService.excluir(obj)
        except OperacaoNaoPermitida as exc:
            raise PermissionDenied(str(exc)) from exc


class RegistroFinalProtegidoAdmin(admin.ModelAdmin):
    """Impede que o admin altere as evidências de uma decisão já encerrada."""
    def encerrado(self, obj):
        if isinstance(obj, Banca):
            return obj.status != 'PENDENTE' or obj.monografia.status_fluxo == 'PUBLICADA'
        if isinstance(obj, ParticipacaoBanca):
            return obj.banca.status != 'PENDENTE' or obj.banca.monografia.status_fluxo == 'PUBLICADA'
        return bool(obj.finalizada_em or obj.participacao.banca.monografia.status_fluxo == 'PUBLICADA')

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or not self.encerrado(obj))

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (obj is None or not self.encerrado(obj))

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if change and self.encerrado(type(obj).objects.select_for_update().get(pk=obj.pk)):
            raise PermissionDenied('O registro acadêmico já está encerrado.')
        monografia = (obj.monografia if isinstance(obj, Banca) else obj.banca.monografia
                      if isinstance(obj, ParticipacaoBanca) else obj.participacao.banca.monografia)
        monografia = Monografia.objects.select_for_update().get(pk=monografia.pk)
        if monografia.status_fluxo == 'PUBLICADA' or Publicacao.objects.filter(monografia=monografia).exists():
            raise PermissionDenied('O trabalho já foi publicado.')
        if isinstance(obj, Avaliacao) and obj.participacao.banca.participacoes.filter(avaliacao__finalizada_em__isnull=False).exists():
            raise PermissionDenied('O resultado desta banca já foi finalizado.')
        super().save_model(request, obj, form, change)


class DocumentoConsultaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        # Não chama FieldFile.url nem oferece um link direto ao armazenamento.
        return [field.name for field in self.model._meta.fields if field.name != 'arquivo']

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)


admin.site.register(Banca, RegistroFinalProtegidoAdmin)
admin.site.register(MembroExterno)
admin.site.register(ParticipacaoBanca, RegistroFinalProtegidoAdmin)
admin.site.register(Avaliacao, RegistroFinalProtegidoAdmin)
admin.site.register(DocumentoComplementar, DocumentoConsultaAdmin)
admin.site.register(Publicacao, DocumentoConsultaAdmin)
