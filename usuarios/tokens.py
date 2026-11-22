"""Assina com a configuração vigente, sem depender do backend global em cache."""
from datetime import timedelta

from django.conf import settings
from rest_framework_simplejwt.backends import TokenBackend


def assinar_token(token):
    config = settings.SIMPLE_JWT
    token.set_exp(lifetime=config.get('ACCESS_TOKEN_LIFETIME', timedelta(minutes=10)))
    backend = TokenBackend(
        algorithm=config.get('ALGORITHM', 'HS256'),
        signing_key=config['SIGNING_KEY'],
        verifying_key=config.get('VERIFYING_KEY', ''),
        audience=config.get('AUDIENCE'),
        issuer=config.get('ISSUER'),
    )
    return backend.encode(token.payload)
