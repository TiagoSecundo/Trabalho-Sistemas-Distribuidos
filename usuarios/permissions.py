"""Autorização por papel e vínculo acadêmico (análogo ao @PreAuthorize)."""
from rest_framework.permissions import BasePermission
from .roles import eh_administrador, obter_papeis


class IsAdministrador(BasePermission):
    def has_permission(self, request, view):
        return eh_administrador(request.user)


class IsAluno(BasePermission):
    def has_permission(self, request, view):
        return 'Aluno' in obter_papeis(request.user)


class IsProfessor(BasePermission):
    def has_permission(self, request, view):
        return 'Professor' in obter_papeis(request.user)


class IsCoordenador(BasePermission):
    def has_permission(self, request, view):
        return 'Coordenador' in obter_papeis(request.user)


class IsAcademicoOuAdministrador(BasePermission):
    def has_permission(self, request, view):
        return bool(obter_papeis(request.user))


class IsDonoMonografia(BasePermission):
    """Use com views que chamam check_object_permissions/get_object()."""
    def has_permission(self, request, view):
        return 'Aluno' in obter_papeis(request.user)

    def has_object_permission(self, request, view, obj):
        return obj.aluno.usuario_id == request.user.pk


class IsOrientadorMonografia(BasePermission):
    def has_permission(self, request, view):
        return 'Professor' in obter_papeis(request.user)

    def has_object_permission(self, request, view, obj):
        return obj.orientador.usuario_id == request.user.pk


class IsCoordenadorMonografia(BasePermission):
    def has_permission(self, request, view):
        return 'Coordenador' in obter_papeis(request.user)

    def has_object_permission(self, request, view, obj):
        return obj.curso.coordenador_id is not None and obj.curso.coordenador.usuario_id == request.user.pk


class IsProfessorAvaliador(BasePermission):
    """Autoriza um professor apenas em sua própria participação/avaliação."""
    def has_permission(self, request, view):
        return 'Professor' in obter_papeis(request.user)

    def has_object_permission(self, request, view, obj):
        # A view pode receber Avaliacao ou ParticipacaoBanca.
        participacao = getattr(obj, 'participacao', obj)
        return participacao.professor_id is not None and participacao.professor.usuario_id == request.user.pk
