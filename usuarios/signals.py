"""Auditoria de autenticação sem persistir senha, sessão ou token."""
from allauth.account.signals import user_signed_up
from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from monografias.models import HistoricoAcao


@receiver(user_signed_up, dispatch_uid='monografias_cadastro_confirmado')
def confirmar_cadastro(sender, request, user, **kwargs):
    messages.success(request, 'Conta criada com sucesso. Seu cadastro foi salvo e você já pode acessar o sistema.')


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
