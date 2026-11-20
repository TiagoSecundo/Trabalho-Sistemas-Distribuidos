"""Cria grupos acadêmicos de maneira idempotente. Não atribui privilégios automaticamente."""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Cria os grupos Alunos, Professores e Coordenadores.'

    def handle(self, *args, **options):
        for nome in ('Alunos', 'Professores', 'Coordenadores'):
            _, criado = Group.objects.get_or_create(name=nome)
            self.stdout.write(f'{nome}: {"criado" if criado else "já existia"}')
