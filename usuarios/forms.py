from django import forms

from monografias.forms import MonografiaForm


class RascunhoAlunoForm(MonografiaForm):
    class Meta(MonografiaForm.Meta):
        fields = ['titulo', 'resumo', 'palavras_chave', 'orientador', 'coorientador']


class ConfirmarConviteForm(forms.Form):
    token = forms.CharField(
        label='Código do convite', max_length=512, strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'off'}),
        help_text='Cole o código recebido da coordenação para confirmar sua participação.',
    )
