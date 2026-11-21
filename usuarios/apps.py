from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class AdministracaoConfig(AdminConfig):
    default_site = 'usuarios.admin_site.AdministracaoAcademica'


class UsuariosConfig(AppConfig):
    name = 'usuarios'

    def ready(self):
        from . import signals  # noqa: F401
