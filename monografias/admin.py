from django.contrib import admin

from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca


@admin.register(Monografia)
class MonografiaAdmin(admin.ModelAdmin):
    exclude = ['arquivo_pdf']


admin.site.register(Banca)
admin.site.register(MembroExterno)
admin.site.register(ParticipacaoBanca)
admin.site.register(Avaliacao)
