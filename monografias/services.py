from Curso_Django.services import OperacaoNaoPermitida, ServicoCRUD


class MonografiaService(ServicoCRUD):
    @classmethod
    def validar_alteracao(cls, instance):
        if instance.status_fluxo != 'RASCUNHO':
            raise OperacaoNaoPermitida('Somente rascunhos podem ser editados ou excluídos neste cadastro.')
