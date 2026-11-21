"""Endpoints acadêmicos independentes do CRUD administrativo legado."""
from django.conf import settings
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, serializers, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, ValidationError

from equipe.models import Aluno, Curso, Professor
from monografias.models import HistoricoAcao, Monografia, ParticipacaoBanca
from monografias.serializers import MonografiaSerializer
from monografias.services import MonografiaService
from Curso_Django.api import Conflito
from Curso_Django.services import OperacaoNaoPermitida
from .convites import emitir_token, validar_token
from .permissions import IsAcademicoOuAdministrador, IsDonoMonografia
from .roles import obter_papeis
from rest_framework_simplejwt.tokens import AccessToken



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
            'access': str(token),
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


class MinhaContaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        usuario = request.user
        return Response({
            'id': usuario.pk,
            'username': usuario.get_username(),
            'email': usuario.email,
            'papeis': obter_papeis(usuario),
        })


class MonografiaResumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Monografia
        fields = ['id', 'titulo', 'status_fluxo']


class MinhasMonografiasView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAcademicoOuAdministrador]
    serializer_class = MonografiaResumoSerializer

    def get_queryset(self):
        usuario = self.request.user
        papeis = obter_papeis(usuario)
        queryset = Monografia.objects.all()
        if 'Administrador' in papeis:
            return queryset
        filtros = Q(pk__in=[])
        if 'Aluno' in papeis:
            filtros |= Q(aluno__usuario=usuario)
        if 'Professor' in papeis:
            filtros |= Q(orientador__usuario=usuario) | Q(coorientador__usuario=usuario)
        if 'Coordenador' in papeis:
            filtros |= Q(curso__coordenador__usuario=usuario)
        return queryset.filter(filtros).distinct()


class RascunhoAlunoSerializer(MonografiaSerializer):
    """Aluno NÃO pode escolher o dono nem alterar estados via JSON."""
    class Meta(MonografiaSerializer.Meta):
        read_only_fields = list(MonografiaSerializer.Meta.read_only_fields) + ['aluno', 'curso']

    def validate(self, attrs):
        if self.instance is None:
            usuario = self.context['request'].user
            # Os vínculos vêm sempre do servidor, nunca do corpo do POST.
            aluno = Aluno.objects.select_related('curso').get(usuario=usuario)
            attrs['aluno'] = aluno
            attrs['curso'] = aluno.curso
        return super().validate(attrs)


class RascunhoAlunoViewSet(viewsets.ModelViewSet):
    """CRUD acadêmico apenas dos próprios TCCs; mudanças somente em RASCUNHO."""
    permission_classes = [IsAuthenticated, IsDonoMonografia]
    serializer_class = RascunhoAlunoSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Monografia.objects.select_related('aluno', 'curso', 'orientador').filter(
            aluno__usuario=self.request.user
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            HistoricoAcao.objects.create(
                ator=self.request.user, objeto=f'Monografia:{instance.pk}',
                acao='RASCUNHO_CRIADO', detalhes={'monografia_id': instance.pk}
            )

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                instance = serializer.save()  # MonografiaService bloqueia não-rascunhos
                HistoricoAcao.objects.create(
                    ator=self.request.user, objeto=f'Monografia:{instance.pk}',
                    acao='RASCUNHO_ALTERADO', detalhes={'monografia_id': instance.pk}
                )
        except OperacaoNaoPermitida as exc:
            raise Conflito(str(exc)) from exc

    def perform_destroy(self, instance):
        try:
            with transaction.atomic():
                MonografiaService.excluir(instance)  # nunca chamar instance.delete() diretamente
                HistoricoAcao.objects.create(
                    ator=self.request.user, objeto=f'Monografia:{instance.pk}',
                    acao='RASCUNHO_EXCLUIDO', detalhes={'monografia_id': instance.pk}
                )
        except (OperacaoNaoPermitida, ProtectedError) as exc:
            raise Conflito('Monografia não pode ser excluída neste estado.') from exc


class EmitirConviteExternoView(APIView):
    """Token aleatório entregue uma única vez ao emissor autorizado, nunca armazenado em claro."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        with transaction.atomic():
            participacao = get_object_or_404(
                ParticipacaoBanca.objects.select_for_update(
                    of=('self',)
                ).select_related(
                    'banca__monografia__curso__coordenador',
                    'membro_externo'
                ),
                pk=pk,
            )
            curso = participacao.banca.monografia.curso
            coordenador = curso.coordenador
            autorizado = request.user.is_staff or (
                'Coordenador' in obter_papeis(request.user)
                and coordenador is not None
                and coordenador.usuario_id == request.user.pk
            )
            if not autorizado:
                raise PermissionDenied('Apenas a coordenação deste curso ou administração pode emitir o convite.')
            if participacao.membro_externo_id is None:
                raise ValidationError({'participacao': 'Esta participação não é de membro externo.'})
            if participacao.banca.monografia.status_fluxo not in ('APROVADA_ORIENTADOR', 'BANCA_AGENDADA'):
                raise ValidationError({'monografia': 'A submissão precisa ser aprovada pelo orientador.'})
            if participacao.banca.status != 'AGENDADA' or participacao.convite_status != 'CONVIDADO':
                raise ValidationError({'convite': 'Esta participação não está aguardando convite.'})
            token = emitir_token(participacao)
            HistoricoAcao.objects.create(
                ator=request.user, objeto=f'ParticipacaoBanca:{participacao.pk}',
                acao='CONVITE_EXTERNO_EMITIDO', detalhes={'participacao_id': participacao.pk}
            )
        # Em produção: entregar por e-mail/evento seguro, por HTTPS. Não logar o token.
        return Response({'token': token, 'expira_em': participacao.expira_em})


class ConfirmarConviteExternoView(APIView):
    """Externo confirma sem conta permanente, exclusivamente por token."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, pk):
        token = request.data.get('token')
        with transaction.atomic():
            participacao = get_object_or_404(
                ParticipacaoBanca.objects.select_for_update(), pk=pk
            )
            if (
                participacao.membro_externo_id is None
                or participacao.convite_status != 'CONVIDADO'
                or participacao.banca.status != 'AGENDADA'
                or not validar_token(participacao, token)
            ):
                raise PermissionDenied('Convite inválido, expirado ou já confirmado.')
            participacao.convite_status = 'CONFIRMADO'
            participacao.confirmado_em = timezone.now()
            participacao.save(update_fields=['convite_status', 'confirmado_em'])
            HistoricoAcao.objects.create(
                ator=None, objeto=f'ParticipacaoBanca:{participacao.pk}',
                acao='CONVITE_EXTERNO_CONFIRMADO', detalhes={'participacao_id': participacao.pk}
            )
        return Response({'confirmado': True})
