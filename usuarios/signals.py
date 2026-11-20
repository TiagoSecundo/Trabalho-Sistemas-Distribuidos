"""Auditoria de autenticação sem persistir senha, sessão ou token."""
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from monografias.models import HistoricoAcao


@receiver(user_logged_in, dispatch_uid='monografias_login_audit')
def registrar_login(sender, request, user, **kwargs):
    HistoricoAcao.objects.create(
        ator=user, objeto=f'Usuario:{user.pk}', acao='LOGIN', detalhes={}
    )


@receiver(user_logged_out, dispatch_uid='monografias_logout_audit')
def registrar_logout(sender, request, user, **kwargs):
    if user is not None:
        HistoricoAcao.objects.create(
            ator=user, objeto=f'Usuario:{user.pk}', acao='LOGOUT', detalhes={}
        )
