"""Índice público e outbox durável vinculados à versão final do B12."""
import uuid

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone


class EventoIndexacao(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    publicacao = models.OneToOneField('monografias.Publicacao', on_delete=models.CASCADE, related_name='evento_indexacao')
    sha256 = models.CharField(max_length=64)
    criado_em = models.DateTimeField(default=timezone.now)
    enviado_em = models.DateTimeField(null=True, blank=True)
    processado_em = models.DateTimeField(null=True, blank=True)
    proxima_tentativa = models.DateTimeField(default=timezone.now, db_index=True)
    tentativas_envio = models.PositiveIntegerField(default=0)
    falhas = models.PositiveIntegerField(default=0)
    ultimo_erro = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['criado_em', 'pk']


class IndicePublicacao(models.Model):
    publicacao = models.OneToOneField('monografias.Publicacao', on_delete=models.CASCADE, related_name='indice')
    sha256 = models.CharField(max_length=64)
    texto = models.TextField()
    vetor = SearchVectorField(null=True)
    indexado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [GinIndex(fields=['vetor'], name='repositorio_texto_gin')]
