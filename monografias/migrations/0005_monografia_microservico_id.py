from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('monografias', '0004_token_avaliacao_externa')]

    operations = [
        migrations.AddField(
            model_name='monografia',
            name='microservico_id',
            field=models.PositiveIntegerField(null=True, blank=True, unique=True, editable=False),
        ),
        migrations.AddField(
            model_name='monografia',
            name='motivo_ajustes',
            field=models.TextField(blank=True, editable=False),
        ),
    ]
