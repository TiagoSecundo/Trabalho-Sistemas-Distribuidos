from rest_framework.permissions import BasePermission
from .roles import obter_papeis


class IsAluno(BasePermission):
    def has_permission(self, request, view):
        return 'Aluno' in obter_papeis(request.user)


class IsProfessor(BasePermission):
    def has_permission(self, request, view):
        return 'Professor' in obter_papeis(request.user)


class IsCoordenador(BasePermission):
    def has_permission(self, request, view):
        return 'Coordenador' in obter_papeis(request.user)