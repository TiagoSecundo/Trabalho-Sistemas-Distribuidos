from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('monografias', '0003_banca_proposta')]

    operations = [
        migrations.AddField(
            model_name='participacaobanca',
            name='avaliacao_token_hash',
            field=models.CharField(max_length=64, blank=True, editable=False),
        ),
        migrations.AddField(
            model_name='participacaobanca',
            name='avaliacao_expira_em',
            field=models.DateTimeField(null=True, blank=True, editable=False),
        ),
    ]
