"""Consulta acadêmica; escritas passam pelos serviços com ator autenticado."""
from django.contrib import admin
from usuarios.admin_auditoria import AdminAuditado
from .models import Avaliacao, Banca, DocumentoComplementar, MembroExterno, Monografia, ParticipacaoBanca, Publicacao


class DocumentoConsultaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields
                if f.name not in ('arquivo', 'arquivo_pdf', 'token_hash', 'avaliacao_token_hash')]

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)


# Mantém os nomes importados pelos testes de proteção da publicação.
MonografiaAdmin = DocumentoConsultaAdmin
RegistroFinalProtegidoAdmin = DocumentoConsultaAdmin
for modelo in (Monografia, Banca, ParticipacaoBanca, Avaliacao, DocumentoComplementar, Publicacao):
    admin.site.register(modelo, DocumentoConsultaAdmin)
admin.site.register(MembroExterno, AdminAuditado)
