"""Endpoints autenticados do fluxo aluno -> orientador -> agendamento."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Curso_Django.api import Conflito
from Curso_Django.services import OperacaoNaoPermitida
from .integracao_microservico import (
    MicroservicoIndisponivel, analisar_submissao, submeter_pdf, sincronizar_orientacao,
)


class ServicoPDFIndisponivel(APIException):
    status_code = 503
    default_detail = 'O microservico de PDF esta indisponivel. Tente novamente ou sincronize o estado.'
    default_code = 'microservico_indisponivel'


def executar(funcao, *args, **kwargs):
    try:
        return funcao(*args, **kwargs)
    except DjangoValidationError as exc:
        raise ValidationError(getattr(exc, 'message_dict', {'detail': exc.messages})) from exc
    except OperacaoNaoPermitida as exc:
        raise Conflito(str(exc)) from exc
    except MicroservicoIndisponivel as exc:
        raise ServicoPDFIndisponivel(str(exc)) from exc


class SubmeterPdfView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        monografia = executar(submeter_pdf, request.user, pk, request.FILES.get('arquivo'))
        return Response({'id': monografia.pk, 'status_fluxo': monografia.status_fluxo,
                         'data_submissao': monografia.data_submissao, 'sha256': monografia.sha256})


class ParecerOrientadorView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request, pk, decisao):
        if decisao not in ('aprovar', 'ajustes'):
            raise ValidationError('Decisao desconhecida.')
        monografia = executar(analisar_submissao, request.user, pk,
                             aprovar=decisao == 'aprovar', motivo=str(request.data.get('motivo', '')))
        return Response({'id': monografia.pk, 'status_fluxo': monografia.status_fluxo})


class SincronizarSubmissaoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        monografia = executar(sincronizar_orientacao, request.user, pk)
        return Response({'id': monografia.pk, 'status_fluxo': monografia.status_fluxo,
                         'data_submissao': monografia.data_submissao, 'sha256': monografia.sha256})
