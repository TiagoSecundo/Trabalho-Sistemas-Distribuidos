"""Gerencia uma instância PostgreSQL exclusiva deste projeto, sem sudo."""

import argparse
import os
from pathlib import Path
import pwd
import shlex
import shutil
import subprocess
import sys

import psycopg2
from psycopg2 import sql

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from Curso_Django.settings import DATABASES

LOCAL_DIR = PROJECT_DIR / '.postgres'
DATA_DIR = LOCAL_DIR / 'data'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start', 'stop', 'status'))
    parser.add_argument('--test-database', action='store_true', help='Prepara também o banco isolado para manage.py test --keepdb.')
    args = parser.parse_args()
    if args.test_database and args.action != 'start':
        parser.error('--test-database só pode ser usado com start.')

    pg_config = shutil.which('pg_config')
    if not pg_config:
        parser.error('PostgreSQL não encontrado: instale o servidor PostgreSQL local.')
    bin_dir = Path(subprocess.check_output([pg_config, '--bindir'], text=True).strip())
    pg_ctl = [str(bin_dir / 'pg_ctl'), '-D', str(DATA_DIR)]
    if not (bin_dir / 'initdb').is_file():
        parser.error(f'Servidor PostgreSQL não encontrado em {bin_dir}.')

    initialized = (DATA_DIR / 'PG_VERSION').is_file()
    running = initialized and subprocess.run(
        [*pg_ctl, 'status'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0

    if args.action == 'status':
        print('PostgreSQL do projeto ativo.' if running else 'PostgreSQL do projeto parado.')
        return
    if args.action == 'stop':
        if running:
            subprocess.run([*pg_ctl, 'stop', '-m', 'fast', '-w', '-t', '30'], check=True)
        else:
            print('PostgreSQL do projeto já está parado.')
        return

    cfg = DATABASES['default']
    if cfg['HOST'] != '127.0.0.1':
        parser.error('Este script gerencia somente a conexão local em 127.0.0.1.')
    admin_user = pwd.getpwuid(os.getuid()).pw_name
    LOCAL_DIR.mkdir(mode=0o700, exist_ok=True)
    if not initialized:
        subprocess.run([
            str(bin_dir / 'initdb'), '-D', str(DATA_DIR), '-U', admin_user,
            '--encoding=UTF8', '--auth-local=peer', '--auth-host=scram-sha-256',
            '--no-instructions',
        ], check=True)
    if not running:
        options = shlex.join([
            '-h', '127.0.0.1', '-p', str(cfg['PORT']), '-k', str(LOCAL_DIR),
            '-c', 'unix_socket_permissions=0700',
        ])
        subprocess.run([
            *pg_ctl, 'start', '-l', str(LOCAL_DIR / 'server.log'),
            '-o', options, '-w', '-t', '30',
        ], check=True)

    # O administrador local usa a identidade do sistema via socket (peer).
    # A aplicação usa um usuário próprio com senha, sem privilégios administrativos.
    conn = psycopg2.connect(
        dbname='postgres', user=admin_user, host=str(LOCAL_DIR),
        port=cfg['PORT'], connect_timeout=5,
    )
    try:
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (cfg['USER'],))
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD %s')
                    .format(sql.Identifier(cfg['USER'])), (cfg['PASSWORD'],),
                )
            cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (cfg['NAME'],))
            if cursor.fetchone() is None:
                cursor.execute(
                    sql.SQL('CREATE DATABASE {} OWNER {}').format(
                        sql.Identifier(cfg['NAME']), sql.Identifier(cfg['USER']),
                    ),
                )
            if args.test_database:
                test_name = 'test_' + cfg['NAME']
                cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (test_name,))
                if cursor.fetchone() is None:
                    cursor.execute(
                        sql.SQL('CREATE DATABASE {} OWNER {}').format(
                            sql.Identifier(test_name), sql.Identifier(cfg['USER']),
                        ),
                    )
                print(f'Banco de testes {test_name} pronto para manage.py test --keepdb.')
    finally:
        conn.close()

    conn = psycopg2.connect(
        dbname=cfg['NAME'], user=cfg['USER'], password=cfg['PASSWORD'],
        host=cfg['HOST'], port=cfg['PORT'], connect_timeout=5,
    )
    conn.close()
    print(f"Banco {cfg['NAME']} pronto em {cfg['HOST']}:{cfg['PORT']}.")


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError, psycopg2.Error) as exc:
        print(f'Falha ao gerenciar o PostgreSQL: {exc}', file=sys.stderr)
        print(f'Consulte o log: {LOCAL_DIR / "server.log"}', file=sys.stderr)
        sys.exit(1)
