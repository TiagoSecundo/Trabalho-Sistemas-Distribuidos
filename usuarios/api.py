from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import serializers, generics
from django.db.models import Q

from monografias.models import Monografia

from .roles import obter_papeis


class MinhaContaView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario = request.user

        return Response({
            'id': usuario.id,
            'username': usuario.username,
            'email': usuario.email,
            'papeis': obter_papeis(usuario)
        })

class MonografiaResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Monografia
        fields = [
            'id',
            'titulo',
            'status_fluxo'
        ]

class MinhasMonografiasView(generics.ListAPIView):

    permission_classes = [IsAuthenticated]

    serializer_class = MonografiaResumoSerializer

    def get_queryset(self):
        usuario = self.request.user
        papeis = obter_papeis(usuario)

        monografias = Monografia.objects.all()

        if 'Administrador' in papeis:
            return monografias

        filtros = Q(pk__in=[])

        if 'Aluno' in papeis:
            filtros |= Q(aluno__usuario=usuario)

        if 'Professor' in papeis:
            filtros |= Q(orientador__usuario=usuario)
            filtros |= Q(coorientador__usuario=usuario)

        if 'Coordenador' in papeis:
            filtros |= Q(
                curso__coordenador__usuario=usuario
            )

        return monografias.filter(filtros).distinct()