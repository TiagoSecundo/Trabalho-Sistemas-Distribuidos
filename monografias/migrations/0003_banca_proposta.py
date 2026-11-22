from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('monografias', '0002_dominio_academico')]

    operations = [
        migrations.AlterField(
            model_name='banca', name='status',
            field=models.CharField(
                max_length=10, editable=False, default='PENDENTE',
                choices=[('PENDENTE', 'Aguardando confirmações'), ('AGENDADA', 'Agendada'),
                         ('REALIZADA', 'Realizada'), ('CANCELADA', 'Cancelada')],
            ),
        ),
        migrations.RemoveConstraint(model_name='banca', name='banca_ativa_unica_por_monografia'),
        migrations.AddConstraint(
            model_name='banca',
            constraint=models.UniqueConstraint(
                fields=['monografia'], condition=models.Q(status__in=['PENDENTE', 'AGENDADA']),
                name='banca_ativa_unica_por_monografia',
            ),
        ),
    ]
