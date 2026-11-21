from allauth.account.forms import SignupForm
from django import forms
from django.db import transaction

from monografias.forms import MonografiaForm
from .auditoria import registrar_acao


class CadastroContaForm(SignupForm):
    """Mantém as validações do allauth e salva conta/e-mail como uma unidade."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Nome de usuário'
        self.fields['email'].label = 'E-mail'
        self.fields['password2'].label = 'Confirme sua senha'
        for nome, campo in self.fields.items():
            campo.widget.attrs.update({
                'class': 'form-control',
                'aria-describedby': f'id_{nome}_helptext id_{nome}_errors',
            })
        self.fields['username'].widget.attrs['autocomplete'] = 'username'
        self.fields['email'].widget.attrs['autocomplete'] = 'email'

    @transaction.atomic
    def save(self, request):
        usuario = super().save(request)
        registrar_acao(usuario, usuario, 'USUARIO_CRIADO')
        return usuario


class RascunhoAlunoForm(MonografiaForm):
    class Meta(MonografiaForm.Meta):
        fields = ['titulo', 'resumo', 'palavras_chave', 'orientador', 'coorientador']


class ConfirmarConviteForm(forms.Form):
    token = forms.CharField(
        label='Código do convite', max_length=512, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'off'}),
        help_text='Cole o código recebido da coordenação para confirmar sua participação.',
    )
