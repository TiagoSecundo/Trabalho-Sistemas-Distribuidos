from django.contrib import admin
from monografias.admin import DocumentoConsultaAdmin
from .models import AvisoBanca, EntregaAviso


@admin.register(AvisoBanca)
class AvisoAdmin(DocumentoConsultaAdmin):
    list_display = ['id', 'banca', 'criado_em', 'processado_em', 'falhas', 'ultimo_erro']


@admin.register(EntregaAviso)
class EntregaAdmin(DocumentoConsultaAdmin):
    list_display = ['aviso', 'destinatario', 'enviado_em']
