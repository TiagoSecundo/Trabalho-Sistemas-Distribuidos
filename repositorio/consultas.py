"""Única seleção de registros elegíveis à leitura anônima."""
from django.db.models import F, Q
from monografias.models import Publicacao


def publicacoes_publicas():
    return Publicacao.objects.filter(
        monografia__status_fluxo='PUBLICADA', banca__status='REALIZADA',
        banca__monografia_id=F('monografia_id'),
        termo__monografia_id=F('monografia_id'), termo__tipo='TERMO_AUTORIZACAO',
        termo__decisao='ACEITO', documento_final__monografia_id=F('monografia_id'),
        documento_final__sha256=F('sha256'),
    ).filter(
        Q(resultado_banca='APROVADA', documento_final__tipo='ORIGINAL_APROVADA')
        | Q(resultado_banca='APROVADA_COM_RESSALVAS', documento_final__tipo='VERSAO_CORRIGIDA', documento_final__decisao='ACEITO')
    ).select_related('monografia__aluno', 'monografia__orientador', 'monografia__curso', 'banca', 'documento_final')
