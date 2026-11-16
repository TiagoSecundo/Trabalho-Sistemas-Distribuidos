from datetime import date
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class MigracaoDominioTests(TransactionTestCase):
    """Verifica a migração real, inclusive sua proteção contra perda do legado."""

    origem = [('monografias', '0001_initial')]
    destino = [('monografias', '0002_dominio_academico')]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.origem)
        self.apps_antigos = executor.loader.project_state(self.origem).apps

    def tearDown(self):
        self.apps_antigos.get_model('monografias', 'Monografia').objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_migracao_com_banco_vazio_preserva_integrante_legado(self):
        Equipe = self.apps_antigos.get_model('equipe', 'Equipe')
        integrante = Equipe.objects.create(name='Integrante anterior', formacao_academica='Graduação')
        executor = MigrationExecutor(connection)
        executor.migrate(self.destino)
        apps = executor.loader.project_state(self.destino).apps
        self.assertTrue(apps.get_model('equipe', 'Equipe').objects.filter(pk=integrante.pk).exists())
        self.assertEqual(apps.get_model('monografias', 'Monografia').objects.count(), 0)
        self.assertEqual(apps.get_model('equipe', 'Aluno').objects.count(), 0)
        # O schema antigo já foi removido: o teardown não pode consultá-lo.
        self.apps_antigos = apps

    def test_migracao_recusa_converter_vinculos_sem_mapeamento(self):
        Equipe = self.apps_antigos.get_model('equipe', 'Equipe')
        Monografia = self.apps_antigos.get_model('monografias', 'Monografia')
        integrante = Equipe.objects.create(name='Autor anterior', formacao_academica='Graduação')
        monografia = Monografia.objects.create(titulo='Trabalho anterior', discente=integrante, data_publicacao=date(2026, 1, 1), resumo='Preservar')
        with self.assertRaisesMessage(RuntimeError, 'mapeamento'):
            MigrationExecutor(connection).migrate(self.destino)
        self.assertEqual(Monografia.objects.get(pk=monografia.pk).discente_id, integrante.pk)
