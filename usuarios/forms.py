from allauth.account.forms import SignupForm
from django import forms
from django.db import transaction

from monografias.forms import MonografiaForm
from monografias.models import Avaliacao
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


class AvaliacaoPropriaForm(forms.ModelForm):
    """O avaliador não escolhe participante nem banca: vêm da sessão e da URL."""

    class Meta:
        model = Avaliacao
        fields = ['nota', 'parecer', 'recomendacao']
        labels = {'nota': 'Nota (0 a 10)', 'parecer': 'Parecer', 'recomendacao': 'Recomendação'}
        widgets = {
            'nota': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10', 'step': '0.01'}),
            'parecer': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'recomendacao': forms.Select(attrs={'class': 'form-select'}),
        }
