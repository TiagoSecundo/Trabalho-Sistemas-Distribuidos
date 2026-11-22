import uuid

from django.db import models
from django.utils import timezone


class AvisoBanca(models.Model):
    """Outbox criada na mesma transação que efetiva o agendamento."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    banca = models.OneToOneField('monografias.Banca', on_delete=models.PROTECT, related_name='aviso')
    assunto = models.CharField(max_length=998)
    corpo = models.TextField()
    criado_em = models.DateTimeField(default=timezone.now)
    enviado_em = models.DateTimeField(null=True, blank=True)
    processado_em = models.DateTimeField(null=True, blank=True)
    proxima_tentativa = models.DateTimeField(default=timezone.now, db_index=True)
    tentativas_envio = models.PositiveIntegerField(default=0)
    falhas = models.PositiveIntegerField(default=0)
    ultimo_erro = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['criado_em', 'pk']


class EntregaAviso(models.Model):
    aviso = models.ForeignKey(AvisoBanca, on_delete=models.CASCADE, related_name='entregas')
    destinatario = models.EmailField()
    enviado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['aviso', 'destinatario'], name='aviso_destinatario_unico')]
