"""Arquivos privados: nomes opacos e acesso exclusivamente pelas views autorizadas."""
import uuid

from django.core.files.storage import FileSystemStorage


class ArmazenamentoPrivado(FileSystemStorage):
    def url(self, name):
        raise ValueError('Documentos privados não possuem URL direta de armazenamento.')


def caminho_documento(instance, filename):
    return f'documentos/{instance.monografia_id}/{uuid.uuid4().hex}.pdf'
