from django.db import models

# Create your models here.

class Equipe(models.Model):
    name = models.CharField(max_length=200)

    fa = (
        ("Graduação", "Graduação"),
        ("Mestrado", "Mestrado"),
        ("Doutorado", "Doutorado"),
    )

    formacao_academica = models.CharField(max_length=10, choices=fa, default="Graduação")

    def __str__(self):
        return self.name
