from django.db import transaction
from django.utils import timezone

from Curso_Django.services import OperacaoNaoPermitida, ServicoCRUD
from .models import Banca, Monografia, ParticipacaoBanca


class MonografiaService(ServicoCRUD):
    @classmethod
    def validar_alteracao(cls, instance):
        if instance.status_fluxo not in ('RASCUNHO', 'AJUSTES_SOLICITADOS') or hasattr(instance, 'publicacao'):
            raise OperacaoNaoPermitida('Somente rascunhos e trabalhos devolvidos para ajustes podem ser editados.')

    @classmethod
    @transaction.atomic
    def excluir(cls, instance):
        instance = type(instance).objects.select_for_update().get(pk=instance.pk)
        if instance.status_fluxo != 'RASCUNHO' or instance.microservico_id is not None or hasattr(instance, 'publicacao'):
            raise OperacaoNaoPermitida('Monografias ja submetidas nao podem ser excluidas.')
        return super().excluir(instance)


class BancaService(ServicoCRUD):
    @classmethod
    @transaction.atomic
    def criar(cls, model, dados):
        if model is not Banca:
            return super().criar(model, dados)
        monografia = Monografia.objects.select_for_update(of=('self',)).get(pk=dados['monografia'].pk)
        if monografia.status_fluxo != 'APROVADA_ORIENTADOR':
            raise OperacaoNaoPermitida('A monografia deve ser aprovada pelo orientador antes de propor a banca.')
        if dados['inicio'] <= timezone.now():
            raise OperacaoNaoPermitida('O início da defesa deve estar no futuro.')
        if Banca.objects.filter(monografia=monografia, status__in=['PENDENTE', 'AGENDADA']).exists():
            raise OperacaoNaoPermitida('Já existe uma proposta ou banca agendada para este trabalho.')
        return super().criar(model, {**dados, 'monografia': monografia, 'status': 'PENDENTE'})

    @classmethod
    @transaction.atomic
    def atualizar(cls, instance, dados):
        if 'monografia' in dados and dados['monografia'].pk != instance.monografia_id:
            raise OperacaoNaoPermitida('Não é permitido trocar a monografia de uma proposta.')
        if dados.get('inicio', instance.inicio) <= timezone.now():
            raise OperacaoNaoPermitida('O início da defesa deve estar no futuro.')
        return super().atualizar(instance, dados)

    @classmethod
    def validar_alteracao(cls, instance):
        if instance.status != 'PENDENTE':
            raise OperacaoNaoPermitida('Somente propostas ainda pendentes podem ser alteradas ou excluídas.')
        if ParticipacaoBanca.objects.filter(banca=instance).exclude(
            convite_status='CONVIDADO', token_hash='',
        ).exists():
            raise OperacaoNaoPermitida('Proposta com respostas ou convites emitidos não pode ser editada. Recrie a proposta.')


class AvaliacaoService(ServicoCRUD):
    @classmethod
    @transaction.atomic
    def criar(cls, model, dados):
        banca = Banca.objects.select_for_update(of=('self',)).get(pk=dados['participacao'].banca_id)
        monografia = Monografia.objects.select_for_update().get(pk=banca.monografia_id)
        if monografia.status_fluxo in ('APROVADA', 'APROVADA_COM_RESSALVAS', 'CORRECOES_ENTREGUES', 'REPROVADA', 'PUBLICADA') or banca.participacoes.filter(avaliacao__finalizada_em__isnull=False).exists():
            raise OperacaoNaoPermitida('Não é permitido acrescentar avaliações após o fechamento da banca.')
        return super().criar(model, dados)

    @classmethod
    def validar_alteracao(cls, instance):
        if instance.finalizada_em:
            raise OperacaoNaoPermitida('Uma avaliação finalizada não pode ser alterada ou excluída.')


class ParticipacaoBancaService(ServicoCRUD):
    """Protege o CRUD legado: uma banca agendada não recebe novos convidados."""

    @classmethod
    @transaction.atomic
    def criar(cls, model, dados):
        banca = Banca.objects.select_for_update(of=('self',)).get(pk=dados['banca'].pk)
        if banca.status != 'PENDENTE':
            raise OperacaoNaoPermitida('Inclua participantes antes da confirmação final do agendamento.')
        return super().criar(model, {**dados, 'banca': banca})

    @classmethod
    def validar_alteracao(cls, instance):
        if instance.banca.status != 'PENDENTE':
            raise OperacaoNaoPermitida('Não altere os membros de bancas já agendadas.')
        if instance.convite_status != 'CONVIDADO' or instance.token_hash:
            raise OperacaoNaoPermitida('Convite já enviado ou respondido. Use as ações acadêmicas da proposta.')

    @classmethod
    @transaction.atomic
    def atualizar(cls, instance, dados):
        if 'banca' in dados and dados['banca'].pk != instance.banca_id:
            raise OperacaoNaoPermitida('Não é permitido transferir participantes entre bancas.')
        return super().atualizar(instance, dados)
