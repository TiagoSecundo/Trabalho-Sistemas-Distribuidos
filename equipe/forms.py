from django import forms
from .models import Aluno, Curso, Professor


class AlunoForm(forms.ModelForm):
    class Meta:
        model = Aluno
        fields = ['nome', 'matricula', 'email', 'curso', 'orientador_atual']
        labels = {'matricula': 'Matrícula'}


class ProfessorForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ['nome', 'email', 'departamento', 'area_pesquisa']
        labels = {'area_pesquisa': 'Área de pesquisa'}


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nome', 'codigo', 'coordenador']
        labels = {'codigo': 'Código'}
