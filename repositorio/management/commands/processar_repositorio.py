import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from repositorio.mensageria import conectar, consumir_disponiveis, despachar_pendentes, preparar_canal
from repositorio.models import EventoIndexacao


class Command(BaseCommand):
    help = 'Publica a outbox B13 e consome PDFs finais para indexação via RabbitMQ.'

    def add_arguments(self, parser):
        parser.add_argument('--uma-vez', action='store_true', help='Executa um ciclo limitado e encerra.')
        parser.add_argument('--repetir-falhas', action='store_true', help='Reagenda eventos que esgotaram as tentativas.')

    def handle(self, *args, **options):
        if not settings.RABBITMQ_URL:
            raise CommandError('Configure RABBITMQ_URL no .env deste projeto.')
        if options['repetir_falhas']:
            total = EventoIndexacao.objects.filter(processado_em__isnull=True, falhas__gte=settings.REPOSITORIO_MAX_TENTATIVAS).update(
                falhas=0, enviado_em=None, proxima_tentativa=timezone.now(), ultimo_erro='')
            self.stdout.write(f'Eventos reagendados: {total}')
        while True:
            conexao = None
            try:
                conexao = conectar()
                canal = preparar_canal(conexao)
                self.stdout.write('Worker do repositório conectado ao RabbitMQ.')
                while True:
                    enviados = despachar_pendentes(canal)
                    processados = consumir_disponiveis(conexao, canal)
                    if enviados or processados or options['uma_vez']:
                        self.stdout.write(f'Eventos enviados: {enviados}; mensagens processadas: {processados}.')
                    if options['uma_vez']:
                        return
                    conexao.sleep(2)
            except KeyboardInterrupt:
                return
            except Exception as exc:
                mensagem = f'Worker indisponível ({type(exc).__name__}); eventos permanecem na outbox.'
                if options['uma_vez']:
                    raise CommandError(mensagem) from None
                self.stderr.write(mensagem)
            finally:
                if conexao and conexao.is_open:
                    conexao.close()
            time.sleep(5)
