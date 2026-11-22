from django.core.management.base import BaseCommand
from notificacoes.models import AvisoBanca, EntregaAviso


class Command(BaseCommand):
    help = 'Resumo da outbox de avisos, sem imprimir destinatários ou credenciais.'

    def handle(self, *args, **options):
        self.stdout.write(f'Avisos pendentes: {AvisoBanca.objects.filter(processado_em__isnull=True).count()}')
        self.stdout.write(f'Avisos concluídos: {AvisoBanca.objects.filter(processado_em__isnull=False).count()}')
        self.stdout.write(f'Avisos com falha: {AvisoBanca.objects.filter(processado_em__isnull=True, falhas__gte=3).count()}')
        self.stdout.write(f'Entregas confirmadas: {EntregaAviso.objects.filter(enviado_em__isnull=False).count()}')
