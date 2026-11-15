# Curso Django

## Executar localmente no Ubuntu

O projeto utiliza uma instância própria do PostgreSQL instalado no sistema,
iniciada pelo usuário atual, sem `sudo`. O servidor PostgreSQL e o comando
`pg_config` precisam estar instalados. As dependências Python estão em
`requirements.txt`.

Com o ambiente virtual `env` preparado, execute na pasta do projeto:

```bash
env/bin/python -m pip install -r requirements.txt
env/bin/python scripts/postgres_local.py start
env/bin/python manage.py migrate
env/bin/python manage.py runserver
```

Acesse <http://127.0.0.1:8000/>.

O comando `start` cria o banco na primeira execução e reutiliza seus dados nas
seguintes. Após reiniciar o computador, execute `start` antes de iniciar o Django.

## Conexão PostgreSQL

Use os seguintes dados para criar uma conexão no pgAdmin ou no editor:

| Campo | Valor |
| --- | --- |
| Host | `127.0.0.1` |
| Porta | `5433` |
| Banco / maintenance database | `curso_django_dev` |
| Usuário | `curso_django_app` |

A senha de desenvolvimento está em `Curso_Django/settings.py`. O usuário da
aplicação é proprietário desse banco e pode criar as tabelas das migrações.

Os dados e logs ficam em `.postgres/`, ignorado pelo Git. Essa conexão começa
com um banco novo, sem importar os dados do banco anterior em `5432`.

Para consultar ou parar somente a instância deste projeto:

```bash
env/bin/python scripts/postgres_local.py status
env/bin/python scripts/postgres_local.py stop
```
