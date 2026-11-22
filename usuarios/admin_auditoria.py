from django.contrib import admin

from .auditoria import registrar_acao


class AdminAuditado(admin.ModelAdmin):
    def log_addition(self, request, obj, message):
        super().log_addition(request, obj, message)
        registrar_acao(request.user, obj, 'ADMIN_CRIACAO')

    def log_change(self, request, obj, message):
        super().log_change(request, obj, message)
        registrar_acao(request.user, obj, 'ADMIN_ATUALIZACAO')

    def log_deletions(self, request, queryset):
        for obj in queryset:
            registrar_acao(request.user, obj, 'ADMIN_EXCLUSAO')
        return super().log_deletions(request, queryset)
