from django.utils.cache import add_never_cache_headers
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from . import estatisticas


class PodeConsultarEstatisticas(BasePermission):
    def has_permission(self, request, view):
        view.papel = estatisticas.papel_estatisticas(request.user)
        return view.papel is not None


class FiltroEstatisticas(serializers.Serializer):
    curso = serializers.IntegerField(required=False, min_value=1, max_value=2**63 - 1)


class EstatisticasView(APIView):
    permission_classes = [PodeConsultarEstatisticas]
    renderer_classes = [JSONRenderer]
    indicador = None

    def get(self, request):
        filtro = FiltroEstatisticas(data=request.query_params)
        filtro.is_valid(raise_exception=True)
        trabalhos = estatisticas.trabalhos_visiveis(request.user, self.papel)
        curso = filtro.validated_data.get('curso')
        if curso is not None:
            if not estatisticas.cursos_visiveis(request.user, self.papel).filter(pk=curso).exists():
                raise NotFound('Curso não encontrado.')
            trabalhos = trabalhos.filter(curso_id=curso)
        return Response(self.indicador(trabalhos))

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        add_never_cache_headers(response)
        return response
