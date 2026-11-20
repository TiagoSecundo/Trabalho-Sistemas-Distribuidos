"""Utilitário compartilhado para auditoria dos CRUDs, sem registrar credenciais."""
from monografias.models import HistoricoAcao


def registrar_acao(ator, objeto, acao):
    referencia = f'{objeto._meta.label}:{objeto.pk}'
    HistoricoAcao.objects.create(
        ator=ator if getattr(ator, 'is_authenticated', False) else None,
        objeto=referencia,
        acao=acao,
        detalhes={'modelo': objeto._meta.label, 'id': objeto.pk},
    )
