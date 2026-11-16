from Curso_Django.services import OperacaoNaoPermitida, ServicoCRUD


class MonografiaService(ServicoCRUD):
    @classmethod
    def validar_alteracao(cls, instance):
        if instance.status_fluxo != 'RASCUNHO':
            raise OperacaoNaoPermitida('Somente rascunhos podem ser editados ou excluídos neste cadastro.')


class BancaService(ServicoCRUD):
    @classmethod
    def validar_alteracao(cls, instance):
        if instance.status != 'AGENDADA':
            raise OperacaoNaoPermitida('Uma banca realizada ou cancelada não pode ser alterada ou excluída.')


class AvaliacaoService(ServicoCRUD):
    @classmethod
    def validar_alteracao(cls, instance):
        if instance.finalizada_em:
            raise OperacaoNaoPermitida('Uma avaliação finalizada não pode ser alterada ou excluída.')
