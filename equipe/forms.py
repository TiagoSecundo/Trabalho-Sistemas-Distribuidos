from django import forms
from .models import Aluno, Curso, Professor


class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ['nome', 'usuario', 'matricula', 'email', 'curso', 'orientador_atual']
        labels = {'matricula': 'Matrícula', 'usuario': 'Conta de acesso'}
        help_texts = {'usuario': 'Vincule a conta criada no cadastro para liberar o painel de aluno. Deixe vazio se ainda não houver conta.'}


class ProfessorForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ['nome', 'usuario', 'email', 'departamento', 'area_pesquisa']
        labels = {'area_pesquisa': 'Área de pesquisa', 'usuario': 'Conta de acesso'}
        help_texts = {'usuario': 'Este vínculo libera o painel de professor. Para liberar a coordenação, selecione este professor como coordenador do curso.'}


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nome', 'codigo', 'coordenador']
        labels = {'codigo': 'Código'}
