"""Cria grupos acadêmicos de maneira idempotente. Não atribui privilégios automaticamente."""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Cria grupos acadêmicos e Administradores, sem atribuir usuários ou permissões.'

    def handle(self, *args, **options):
        for nome in ('Alunos', 'Professores', 'Coordenadores', 'Administradores'):
            _, criado = Group.objects.get_or_create(name=nome)
            self.stdout.write(f'{nome}: {"criado" if criado else "já existia"}')
