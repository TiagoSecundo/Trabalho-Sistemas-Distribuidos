"""Executa consultas Django fora do event loop privado do Playwright sync."""
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from django.db import connections


def banco(funcao, *args, **kwargs):
    def executar():
        try:
            return funcao(*args, **kwargs)
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(executar).result()


def fora_do_loop(funcao):
    @wraps(funcao)
    def executar(*args, **kwargs):
        return banco(funcao, *args, **kwargs)
    return executar
