from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from .roles import eh_administrador


class LoginAdministrativoForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not eh_administrador(user):
            raise ValidationError('Esta conta não possui acesso administrativo.', code='invalid_login')


class AdministracaoAcademica(AdminSite):
    login_form = LoginAdministrativoForm

    def has_permission(self, request):
        return super().has_permission(request) and eh_administrador(request.user)
