import io
from datetime import datetime, timedelta, timezone as dt_timezone

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from monografias.models import Publicacao
from usuarios.publicacao import conferir_documento, enviar_documento
from usuarios.test_publicacao import CenarioPublicacao, arquivo_pdf


def pdf_com_texto(texto='Hiperconvergencia e observabilidade em sistemas distribuidos.'):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    seguro = texto.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream.set_data(f'BT /F1 12 Tf 72 720 Td ({seguro}) Tj ET'.encode('latin-1'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO(); writer.write(output)
    return output.getvalue()


class CenarioRepositorio(CenarioPublicacao):
    def publicar_trabalho(self, titulo='Arquiteturas de sistemas distribuídos', texto=None):
        m = self.trabalho('APROVADA_COM_RESSALVAS')
        m.titulo, m.resumo, m.palavras_chave = titulo, 'Pesquisa sobre aplicações acadêmicas e serviços digitais.', ['Sistemas distribuídos', 'Redes']
        m.save(update_fields=['titulo', 'resumo', 'palavras_chave'])
        # Em UTC é 2025; na data local da defesa ainda é 2024.
        inicio = datetime(2025, 1, 1, 1, 30, tzinfo=dt_timezone.utc)
        m.bancas.update(inicio=inicio, fim=inicio+timedelta(hours=1))
        final = pdf_com_texto(texto) if texto is not None else pdf_com_texto()
        corrigida = enviar_documento(self.aluno_user, m.pk, 'VERSAO_CORRIGIDA', arquivo_pdf(conteudo=final))
        termo = enviar_documento(self.aluno_user, m.pk, 'TERMO_AUTORIZACAO', arquivo_pdf('Termo privado'))
        conferir_documento(self.orientador_user, m.pk, corrigida.pk, decisao='aceitar', confirmacao=True)
        conferir_documento(self.coordenador_user, m.pk, termo.pk, decisao='aceitar', confirmacao=True)
        return Publicacao.objects.select_related('documento_final', 'termo', 'monografia').get(monografia=m)
