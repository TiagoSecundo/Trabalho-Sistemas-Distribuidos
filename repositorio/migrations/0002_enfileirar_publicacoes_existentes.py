from django.db import migrations


def enfileirar(apps, schema_editor):
    Publicacao = apps.get_model('monografias', 'Publicacao')
    Evento = apps.get_model('repositorio', 'EventoIndexacao')
    alias = schema_editor.connection.alias
    for publicacao in Publicacao.objects.using(alias).filter(monografia__status_fluxo='PUBLICADA').iterator():
        Evento.objects.using(alias).get_or_create(publicacao_id=publicacao.pk, defaults={'sha256': publicacao.sha256})


class Migration(migrations.Migration):
    dependencies = [('repositorio', '0001_initial')]
    operations = [migrations.RunPython(enfileirar, migrations.RunPython.noop)]
