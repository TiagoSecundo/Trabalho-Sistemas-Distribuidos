from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from equipe.models import Aluno, Curso, Professor
from .arquivos import ArmazenamentoPrivado, caminho_documento


class Monografia(models.Model):
    STATUS = (
        ('RASCUNHO', 'Rascunho'),
        ('SUBMETIDA', 'Submetida'),
        ('EM_ANALISE_ORIENTADOR', 'Em análise pelo orientador'),
        ('AJUSTES_SOLICITADOS', 'Ajustes solicitados'),
        ('APROVADA_ORIENTADOR', 'Aprovada pelo orientador'),
        ('BANCA_AGENDADA', 'Banca agendada'),
        ('DEFESA_REALIZADA', 'Defesa realizada'),
        ('REPROVADA', 'Reprovada'),
        ('APROVADA_COM_RESSALVAS', 'Aprovada com ressalvas'),
        ('CORRECOES_ENTREGUES', 'Correções entregues'),
        ('APROVADA', 'Aprovada'),
        ('PUBLICADA', 'Publicada'),
    )

    titulo = models.CharField(max_length=200)
    resumo = models.TextField()
    palavras_chave = models.JSONField(default=list, blank=True)
    aluno = models.ForeignKey(Aluno, on_delete=models.PROTECT, related_name='monografias')
    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='monografias')
    orientador = models.ForeignKey(Professor, on_delete=models.PROTECT, related_name='monografias_orientadas')
    coorientador = models.ForeignKey(Professor, on_delete=models.PROTECT, null=True, blank=True, related_name='monografias_coorientadas')
    status_fluxo = models.CharField(max_length=30, choices=STATUS, default='RASCUNHO', editable=False)
    data_submissao = models.DateTimeField(null=True, blank=True, editable=False)
    data_publicacao = models.DateField(null=True, blank=True, editable=False)
    arquivo_pdf = models.FileField(upload_to='monografias/', blank=True, validators=[FileExtensionValidator(['pdf'])])
    sha256 = models.CharField(max_length=64, blank=True, editable=False)
    # Vinculo entre PKs independentes: uma monografia do principal corresponde a uma do microservico.
    microservico_id = models.PositiveIntegerField(null=True, blank=True, unique=True, editable=False)
    motivo_ajustes = models.TextField(blank=True, editable=False)

    class Meta:
        ordering = ['-pk']
        constraints = [
            models.CheckConstraint(condition=~models.Q(orientador=models.F('coorientador')), name='monografia_orientadores_distintos'),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.aluno_id and self.curso_id and self.aluno.curso_id != self.curso_id:
            errors['curso'] = 'O curso deve ser o mesmo do aluno.'
        if self.orientador_id and self.orientador_id == self.coorientador_id:
            errors['coorientador'] = 'Orientador e coorientador devem ser professores diferentes.'
        if not isinstance(self.palavras_chave, list) or any(
            not isinstance(palavra, str) or not palavra.strip() for palavra in self.palavras_chave
        ):
            errors['palavras_chave'] = 'Informe uma lista de palavras-chave não vazias.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.titulo


class Banca(models.Model):
    MODALIDADES = (('PRESENCIAL', 'Presencial'), ('REMOTA', 'Remota'), ('HIBRIDA', 'Híbrida'))
    STATUS = (('PENDENTE', 'Aguardando confirmações'), ('AGENDADA', 'Agendada'), ('REALIZADA', 'Realizada'), ('CANCELADA', 'Cancelada'))

    monografia = models.ForeignKey(Monografia, on_delete=models.PROTECT, related_name='bancas')
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    local = models.CharField(max_length=255, blank=True)
    link = models.URLField(blank=True)
    modalidade = models.CharField(max_length=10, choices=MODALIDADES, default='PRESENCIAL')
    status = models.CharField(max_length=10, choices=STATUS, default='PENDENTE', editable=False)

    class Meta:
        ordering = ['inicio', 'pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(fim__gt=models.F('inicio')), name='banca_intervalo_valido'),
            models.UniqueConstraint(fields=['monografia'], condition=models.Q(status__in=['PENDENTE', 'AGENDADA']), name='banca_ativa_unica_por_monografia'),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.inicio and self.fim and self.fim <= self.inicio:
            errors['fim'] = 'O término deve ser posterior ao início.'
        if self.modalidade in ('PRESENCIAL', 'HIBRIDA') and not self.local.strip():
            errors['local'] = 'Informe o local da banca.'
        if self.modalidade in ('REMOTA', 'HIBRIDA') and not self.link:
            errors['link'] = 'Informe o link da banca.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        horario = timezone.localtime(self.inicio).strftime('%d/%m/%Y %H:%M') if self.inicio else 'Horário não informado'
        return f'{self.monografia} — {horario}'


class MembroExterno(models.Model):
    nome = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    instituicao = models.CharField(max_length=200)

    class Meta:
        ordering = ['nome', 'pk']

    def __str__(self):
        return self.nome


class ParticipacaoBanca(models.Model):
    PAPEIS = (('PRESIDENTE', 'Presidente'), ('AVALIADOR', 'Avaliador'), ('SUPLENTE', 'Suplente'))
    CONVITE_STATUS = (('CONVIDADO', 'Convidado'), ('CONFIRMADO', 'Confirmado'), ('RECUSADO', 'Recusado'))

    banca = models.ForeignKey(Banca, on_delete=models.PROTECT, related_name='participacoes')
    professor = models.ForeignKey(Professor, on_delete=models.PROTECT, null=True, blank=True, related_name='participacoes_banca')
    membro_externo = models.ForeignKey(MembroExterno, on_delete=models.PROTECT, null=True, blank=True, related_name='participacoes_banca')
    papel = models.CharField(max_length=10, choices=PAPEIS, default='AVALIADOR')
    convite_status = models.CharField(max_length=10, choices=CONVITE_STATUS, default='CONVIDADO', editable=False)
    confirmado_em = models.DateTimeField(null=True, blank=True, editable=False)
    token_hash = models.CharField(max_length=64, blank=True, editable=False)
    expira_em = models.DateTimeField(null=True, blank=True, editable=False)
    # Código de avaliação separado do código de confirmação do convite.
    avaliacao_token_hash = models.CharField(max_length=64, blank=True, editable=False)
    avaliacao_expira_em = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['pk']
        verbose_name_plural = 'participações em bancas'
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(professor__isnull=False, membro_externo__isnull=True) | models.Q(professor__isnull=True, membro_externo__isnull=False)),
                name='participacao_exatamente_um_membro',
            ),
            models.UniqueConstraint(fields=['banca', 'professor'], name='participacao_professor_unico'),
            models.UniqueConstraint(fields=['banca', 'membro_externo'], name='participacao_externo_unico'),
        ]

    def clean(self):
        super().clean()
        if bool(self.professor_id) == bool(self.membro_externo_id):
            raise ValidationError('Informe um professor ou um membro externo, exclusivamente.')
        if self.pk and Avaliacao.objects.filter(participacao_id=self.pk).exists():
            original = type(self).objects.get(pk=self.pk)
            if any(getattr(self, field) != getattr(original, field) for field in ('banca_id', 'professor_id', 'membro_externo_id', 'papel')):
                raise ValidationError('Uma participação avaliada não pode trocar de banca, avaliador ou papel.')

    def __str__(self):
        return f'{self.professor or self.membro_externo} — banca {self.banca_id}'


class Avaliacao(models.Model):
    RECOMENDACOES = (('APROVADA', 'Aprovada'), ('APROVADA_COM_RESSALVAS', 'Aprovada com ressalvas'), ('REPROVADA', 'Reprovada'))

    participacao = models.OneToOneField(ParticipacaoBanca, on_delete=models.PROTECT, related_name='avaliacao')
    nota = models.DecimalField(max_digits=4, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(10)])
    parecer = models.TextField()
    recomendacao = models.CharField(max_length=25, choices=RECOMENDACOES)
    registrada_em = models.DateTimeField(auto_now_add=True)
    finalizada_em = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-pk']
        verbose_name_plural = 'avaliações'
        constraints = [
            models.CheckConstraint(condition=models.Q(nota__gte=0, nota__lte=10), name='avaliacao_nota_entre_zero_e_dez'),
        ]

    def __str__(self):
        return f'Avaliação de {self.participacao}'


class DocumentoComplementar(models.Model):
    TIPOS = (('ATA', 'Ata'), ('TERMO_AUTORIZACAO', 'Termo de autorização'), ('COMPROVANTE_CORRECAO', 'Comprovante de correção'), ('VERSAO_CORRIGIDA', 'Versão corrigida'), ('ORIGINAL_APROVADA', 'Cópia da submissão aprovada'))
    DECISOES = (('PENDENTE', 'Aguardando conferência'), ('ACEITO', 'Conferido e aceito'), ('REJEITADO', 'Rejeitado'), ('RECEBIDO', 'Recebido'))

    monografia = models.ForeignKey(Monografia, on_delete=models.PROTECT, related_name='documentos')
    tipo = models.CharField(max_length=25, choices=TIPOS)
    arquivo = models.FileField(upload_to=caminho_documento, storage=ArmazenamentoPrivado(), validators=[FileExtensionValidator(['pdf'])])
    sha256 = models.CharField(max_length=64, blank=True, editable=False)
    enviado_em = models.DateTimeField(auto_now_add=True)
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='documentos_enviados')
    nome_original = models.CharField(max_length=255, blank=True)
    tamanho_bytes = models.PositiveBigIntegerField(default=0, editable=False)
    origem_microservico_id = models.PositiveIntegerField(null=True, blank=True, editable=False)
    # Legado não é implicitamente validado nem escolhido como versão corrente.
    vigente = models.BooleanField(default=False, editable=False)
    decisao = models.CharField(max_length=10, choices=DECISOES, default='PENDENTE', editable=False)
    conferido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='documentos_conferidos', editable=False)
    conferido_em = models.DateTimeField(null=True, blank=True, editable=False)
    motivo = models.TextField(blank=True, editable=False)

    class Meta:
        ordering = ['-enviado_em', '-pk']
        constraints = [models.UniqueConstraint(fields=['monografia', 'tipo'], condition=models.Q(vigente=True), name='documento_vigente_unico_por_tipo')]

    def __str__(self):
        return f'{self.get_tipo_display()} — {self.monografia}'


class Publicacao(models.Model):
    """Registro único e imutável da decisão e dos arquivos efetivamente publicados."""
    monografia = models.OneToOneField(Monografia, on_delete=models.PROTECT, related_name='publicacao')
    banca = models.ForeignKey(Banca, on_delete=models.PROTECT, related_name='publicacoes')
    documento_final = models.ForeignKey(DocumentoComplementar, on_delete=models.PROTECT, related_name='publicacoes_como_final')
    termo = models.ForeignKey(DocumentoComplementar, on_delete=models.PROTECT, related_name='publicacoes_como_termo')
    publicado_em = models.DateTimeField(default=timezone.now, editable=False)
    publicado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='publicacoes_academicas', editable=False)
    sha256 = models.CharField(max_length=64, editable=False)
    resultado_banca = models.CharField(max_length=30, editable=False)
    media_banca = models.DecimalField(max_digits=4, decimal_places=2, editable=False)

    def __str__(self):
        return f'Publicação — {self.monografia}'


class HistoricoAcao(models.Model):
    ator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='acoes_academicas')
    objeto = models.CharField(max_length=200)
    acao = models.CharField(max_length=100)
    data_hora = models.DateTimeField(auto_now_add=True)
    detalhes = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-data_hora', '-pk']
        verbose_name_plural = 'históricos de ações'

    def __str__(self):
        return f'{self.acao} — {self.objeto}'
