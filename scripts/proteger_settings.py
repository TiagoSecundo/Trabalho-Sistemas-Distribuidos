"""Migra settings legados para env sem copiar segredos existentes para o patch.

ATENÇÃO: crie .env com a senha ORIGINAL do banco antes de executar.
Execute uma vez na raiz: python scripts/proteger_settings.py
"""
from pathlib import Path
import re

base = Path(__file__).resolve().parent.parent
p = base / 'Curso_Django' / 'settings.py'
s = p.read_text(encoding='utf-8')
if 'load_dotenv(BASE_DIR / ".env")' in s:
    raise SystemExit('Configuração já adaptada. Não é necessário executar novamente.')
if not re.search(r'(?m)^SECRET_KEY\s*=', s):
    raise SystemExit('Chave não encontrada. Não foi alterado.')
if not re.search(r"(?m)^\s*'PASSWORD'\s*:", s):
    raise SystemExit('Senha do banco não encontrada. Não foi alterado.')
if "MIDDLEWARE = [" not in s:
    raise SystemExit('Middleware não encontrado. Não foi alterado.')

s = s.replace('from pathlib import Path', 'from pathlib import Path\nimport os\nfrom dotenv import load_dotenv', 1)
s = s.replace("BASE_DIR = Path(__file__).resolve().parent.parent", 'BASE_DIR = Path(__file__).resolve().parent.parent\nload_dotenv(BASE_DIR / ".env")', 1)
s = re.sub(r'(?m)^SECRET_KEY\s*=.*$', 'SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]', s, count=1)
s = re.sub(r'(?m)^DEBUG\s*=.*$', 'DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"', s, count=1)
s = re.sub(r'(?m)^ALLOWED_HOSTS\s*=.*$', 'ALLOWED_HOSTS = [x.strip() for x in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if x.strip()]', s, count=1)
s = re.sub(r"(?m)^(\s*'PASSWORD'\s*:)\s*.*$", r'\1 os.environ["POSTGRES_PASSWORD"],', s, count=1)
s = s.replace("'allauth.account.middleware.AccountMiddleware',", "'allauth.account.middleware.AccountMiddleware',\n    'usuarios.middleware.RedeAdministrativaMiddleware',", 1)
s += """\n# Camada adicional de segurança. Reverse proxy deve impor HTTPS no ambiente real.\nSECURE_SSL_REDIRECT = not DEBUG\nSESSION_COOKIE_SECURE = not DEBUG\nCSRF_COOKIE_SECURE = not DEBUG\nSESSION_COOKIE_HTTPONLY = True\nSESSION_COOKIE_SAMESITE = 'Lax'\nCSRF_COOKIE_SAMESITE = 'Lax'\nSECURE_HSTS_SECONDS = 3600 if not DEBUG else 0\nSECURE_HSTS_INCLUDE_SUBDOMAINS = False\nSECURE_HSTS_PRELOAD = False\nSECURE_CONTENT_TYPE_NOSNIFF = True\nX_FRAME_OPTIONS = 'DENY'\nADMIN_NETWORK_RESTRICTION_ENABLED = os.environ.get(\n    'ADMIN_NETWORK_RESTRICTION_ENABLED', '0' if DEBUG else '1'\n) == '1'\nADMIN_ALLOWED_CIDRS = tuple(x.strip() for x in os.environ.get('ADMIN_ALLOWED_CIDRS', '').split(',') if x.strip())\n"""
p.write_text(s, encoding='utf-8')
print('settings.py convertido. Verifique o diff e não faça commit do arquivo .env.')
