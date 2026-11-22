from django.contrib import admin

from .models import Aluno, Curso, Professor
from usuarios.admin_auditoria import AdminAuditado

admin.site.register(Aluno, AdminAuditado)
admin.site.register(Professor, AdminAuditado)
admin.site.register(Curso, AdminAuditado)
