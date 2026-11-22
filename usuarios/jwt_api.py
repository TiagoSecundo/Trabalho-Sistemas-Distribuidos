"""Emissão de JWT para integração com o microserviço."""

from django.conf import settings
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_simplejwt.tokens import AccessToken

from equipe.models import Aluno, Curso, Professor
from monografias.models import HistoricoAcao
from .roles import obter_papeis
from .tokens import assinar_token


class TokenMicroservicoView(APIView):

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    http_method_names = ['post', 'options']

    PAPEIS_TOKEN = {
        'Aluno': 'aluno',
        'Professor': 'orientador',
        'Coordenador': 'coordenador',
        'Administrador': 'admin',
    }

    def post(self, request):
        usuario = request.user

        if not usuario.is_active:
            raise PermissionDenied('Conta inativa.')

        # Identifica os perfis permitidos para o usuário
        permitidos = [
            self.PAPEIS_TOKEN[p]
            for p in obter_papeis(usuario)
            if p in self.PAPEIS_TOKEN
        ]

        if not permitidos:
            raise PermissionDenied('Usuário sem perfil autorizado.')

        papel = request.data.get('role')

        if papel is None:
            if len(permitidos) != 1:
                raise ValidationError({
                    'role': 'Informe o perfil desejado.',
                    'permitidos': permitidos,
                })
            papel = permitidos[0]

        elif not isinstance(papel, str) or papel not in permitidos:
            raise PermissionDenied('Perfil não autorizado.')

        # Confere se a chave JWT foi configurada
        chave = settings.SIMPLE_JWT.get('SIGNING_KEY', '')

        if not isinstance(chave, str) or len(chave) < 32:
            return Response(
                {'detail': 'Chave JWT não configurada.'},
                status=503,
            )

        # Busca os vínculos acadêmicos no banco
        aluno = None
        professor = None
        cursos_ids = []

        if papel == 'aluno':
            aluno = Aluno.objects.filter(
                usuario=usuario
            ).first()

            if aluno is None:
                raise PermissionDenied('Aluno sem vínculo acadêmico.')

        if papel in ('orientador', 'coordenador'):
            professor = Professor.objects.filter(
                usuario=usuario
            ).first()

            if professor is None:
                raise PermissionDenied('Professor sem vínculo acadêmico.')

        if papel == 'coordenador':
            cursos_ids = list(
                Curso.objects.filter(
                    coordenador__usuario=usuario
                ).values_list('id', flat=True)
            )

            if not cursos_ids:
                raise PermissionDenied('Coordenador sem curso vinculado.')

        # Gera o token JWT
        token = AccessToken.for_user(usuario)

        token['role'] = papel
        token['aluno_id'] = aluno.pk if aluno else None
        token['professor_id'] = professor.pk if professor else None
        token['curso_id'] = aluno.curso_id if aluno else None
        token['orientador_id'] = (
            aluno.orientador_atual_id if aluno else None
        )
        token['curso_ids'] = cursos_ids

        # Registra a emissão no histórico de auditoria
        HistoricoAcao.objects.create(
            ator=usuario,
            objeto=f'Usuario:{usuario.pk}',
            acao='TOKEN_MICROSSERVICO_EMITIDO',
            detalhes={'role': papel},
        )

        resposta = Response({
            'access': assinar_token(token),
            'token_type': 'Bearer',
            'role': papel,
            'expires_in': int(
                settings.SIMPLE_JWT[
                    'ACCESS_TOKEN_LIFETIME'
                ].total_seconds()
            ),
        })

        resposta['Cache-Control'] = 'no-store'
        resposta['Pragma'] = 'no-cache'

        return resposta
