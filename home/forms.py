from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginAdministrativoForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError('Esta área exige uma conta administrativa. Solicite acesso ao responsável pelo projeto.', code='sem_permissao')
