from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.

class Equipe(models.Model):
    """Cadastro legado preservado até a classificação dos integrantes existentes."""

    name = models.CharField(max_length=200)

    fa = (
        ("Graduação", "Graduação"),
        ("Mestrado", "Mestrado"),
        ("Doutorado", "Doutorado"),
    )

    formacao_academica = models.CharField(max_length=10, choices=fa, default="Graduação")

    def __str__(self):
        return self.name


class Professor(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='professor')
    nome = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    departamento = models.CharField(max_length=200)
    area_pesquisa = models.CharField(max_length=200)

    class Meta:
        ordering = ['nome', 'pk']
        verbose_name_plural = 'professores'

    def __str__(self):
        return self.nome


class Curso(models.Model):
    nome = models.CharField(max_length=200)
    codigo = models.CharField(max_length=30, unique=True)
    coordenador = models.ForeignKey(Professor, on_delete=models.PROTECT, null=True, blank=True, related_name='cursos_coordenados')

    class Meta:
        ordering = ['nome', 'pk']

    def __str__(self):
        return self.nome


class Aluno(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='aluno')
    nome = models.CharField(max_length=200)
    matricula = models.CharField(max_length=30, unique=True)
    email = models.EmailField()
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='alunos')
    orientador_atual = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True, blank=True, related_name='alunos_orientados')

    class Meta:
        ordering = ['nome', 'pk']

    def clean(self):
        super().clean()
        if self.pk and self.monografias.exclude(curso_id=self.curso_id).exists():
            raise ValidationError({'curso': 'O curso deve coincidir com o das monografias vinculadas.'})

    def __str__(self):
        return self.nome
