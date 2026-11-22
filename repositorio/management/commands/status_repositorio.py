from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from repositorio.models import EventoIndexacao, IndicePublicacao


class Command(BaseCommand):
    help = 'Mostra progresso da indexação e falhas, sem expor credenciais ou conteúdo dos PDFs.'

    def handle(self, *args, **options):
        contagem = EventoIndexacao.objects.aggregate(
            total=Count('pk'),
            indexados=Count('pk', filter=Q(processado_em__isnull=False)),
            pendentes=Count('pk', filter=Q(processado_em__isnull=True, falhas__lt=settings.REPOSITORIO_MAX_TENTATIVAS)),
            falhas=Count('pk', filter=Q(processado_em__isnull=True, falhas__gte=settings.REPOSITORIO_MAX_TENTATIVAS)),
        )
        for nome, quantidade in contagem.items():
            self.stdout.write(f'{nome}: {quantidade}')
        self.stdout.write(f'PDFs sem camada de texto: {IndicePublicacao.objects.filter(texto="").count()}')
        for evento in EventoIndexacao.objects.filter(processado_em__isnull=True).exclude(ultimo_erro='')[:20]:
            self.stdout.write(f'Evento {evento.pk}: {evento.ultimo_erro}; falhas: {evento.falhas}; envios: {evento.tentativas_envio}')
