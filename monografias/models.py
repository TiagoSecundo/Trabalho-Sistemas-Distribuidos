from django.db import models

from equipe.models import Equipe

# Create your models here.
class Monografia(models.Model):
    titulo = models.CharField(max_length=200)
    discente = models.OneToOneField(Equipe, on_delete=models.CASCADE)
    data_publicacao = models.DateField()
    resumo = models.TextField()
    orientador = models.ForeignKey(Equipe, on_delete=models.CASCADE, null=True, blank=True,related_name='orientador')
    coorientador = models.ForeignKey(Equipe, on_delete=models.CASCADE, null=True, blank=True, related_name='coorientador')

    def __str__(self): #serve para retornar o nome do objeto quando for chamado, por exemplo, no admin do django
        return self.titulo