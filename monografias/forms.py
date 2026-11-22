from django import forms
import json

from .models import Avaliacao, Banca, MembroExterno, Monografia, ParticipacaoBanca


class PalavrasChaveField(forms.CharField):
    def prepare_value(self, value):
        return ', '.join(value) if isinstance(value, list) else value

    def to_python(self, value):
        value = super().to_python(value)
        if value.startswith('['):
            try:
                return json.loads(value)
            except ValueError as exc:
                raise forms.ValidationError('Informe palavras separadas por vírgula ou uma lista JSON válida.') from exc
        return [palavra.strip() for palavra in value.split(',') if palavra.strip()]

    def validate(self, value):
        super().validate(value)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() or len(item) > 100 for item in value):
            raise forms.ValidationError('Informe palavras não vazias, cada uma com no máximo 100 caracteres.')


class MonografiaForm(forms.ModelForm):
    palavras_chave = PalavrasChaveField(required=False, label='Palavras-chave', help_text='Separe por vírgulas. Exemplo: Django, TCC, sistemas distribuídos.')
    def clean_palavras_chave(self):
        palavras = self.cleaned_data['palavras_chave']
        return [] if palavras is None else palavras

    class Meta:
        model = Monografia
        fields = ['titulo', 'aluno', 'curso', 'resumo', 'palavras_chave', 'orientador', 'coorientador']
        labels = {'titulo': 'Título'}
        widgets = {'resumo': forms.Textarea(attrs={'rows': 5})}


class BancaForm(forms.ModelForm):
    class Meta:
        model = Banca
        fields = ['monografia', 'modalidade', 'inicio', 'fim', 'local', 'link']
        labels = {'inicio': 'Início', 'fim': 'Término', 'link': 'Link da reunião'}
        widgets = {
            campo: forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'})
            for campo in ('inicio', 'fim')
        }
        help_texts = {'inicio': 'Horário de São Paulo.', 'fim': 'Horário de São Paulo.', 'local': 'Obrigatório para banca presencial ou híbrida.', 'link': 'Obrigatório para banca remota ou híbrida.'}


class MembroExternoForm(forms.ModelForm):
    class Meta:
        model = MembroExterno
        fields = ['nome', 'email', 'instituicao']
        labels = {'instituicao': 'Instituição'}


class ParticipacaoBancaForm(forms.ModelForm):
    class Meta:
        model = ParticipacaoBanca
        fields = ['banca', 'professor', 'membro_externo', 'papel']
        help_texts = {'professor': 'Escolha um professor OU um membro externo.', 'membro_externo': 'Preencha somente quando o participante não for professor cadastrado.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['banca'].queryset = Banca.objects.select_related('monografia')


class AvaliacaoForm(forms.ModelForm):
    class Meta:
        model = Avaliacao
        fields = ['participacao', 'nota', 'parecer', 'recomendacao']
        labels = {'participacao': 'Participante da banca', 'recomendacao': 'Recomendação'}
        widgets = {'parecer': forms.Textarea(attrs={'rows': 5}), 'nota': forms.NumberInput(attrs={'min': 0, 'max': 10, 'step': '0.01'})}
        help_texts = {'nota': 'Nota de 0 a 10. O resultado é calculado no fechamento da banca, após todas as avaliações titulares.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['participacao'].queryset = ParticipacaoBanca.objects.select_related('banca__monografia', 'professor', 'membro_externo')
        self.fields['participacao'].label_from_instance = lambda obj: f'{obj.professor or obj.membro_externo} — {obj.banca.monografia} (banca #{obj.banca_id})'
