"""Tokens escopados ao convite externo (hash persistido; segredo retornado uma vez)."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from django.utils import timezone


def emitir_token(participacao):
    token = secrets.token_urlsafe(32)
    participacao.token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
    # Renovar o token se a defesa for reagendada. Prazo finito, não permanente.
    participacao.expira_em = min(
        max(timezone.now() + timedelta(days=7), participacao.banca.fim + timedelta(days=2)),
        timezone.now() + timedelta(days=90),
    )
    participacao.save(update_fields=['token_hash', 'expira_em'])
    return token


def validar_token(participacao, token):
    if not isinstance(token, str) or len(token) > 512 or not token:
        return False
    if not participacao.token_hash or not participacao.expira_em:
        return False
    if participacao.expira_em <= timezone.now():
        return False
    digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
    return hmac.compare_digest(participacao.token_hash, digest)
