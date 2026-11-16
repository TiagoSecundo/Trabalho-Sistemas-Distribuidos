# AllTeam Monografias

Aplicação acadêmica para organizar monografias, alunos, professores, cursos,
bancas, participantes e avaliações. O backend usa Django REST Framework e
PostgreSQL; as páginas Django existentes usam Bootstrap e consomem a API com
JavaScript nativo.

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

Se a porta 8000 estiver ocupada, use `env/bin/python manage.py runserver 8001`
e acesse <http://127.0.0.1:8001/>.

## CRUD de monografias

Os CRUDs JSON estão em `/api/`: alunos, professores, cursos, monografias,
bancas e avaliações. Membros externos e participações em bancas têm rotas
auxiliares. A referência navegável dos endpoints está em `/api/`.

Nesta etapa o acesso é administrativo. Crie uma conta Django com
`env/bin/python manage.py createsuperuser` e entre em `/entrar/`.
A mesma sessão autentica as páginas e a API. O admin Django está em `/admin/`
e a referência navegável da API em `/api/`.

Comece por professores, cursos e alunos em `/equipe/`. Depois cadastre uma
monografia e use as abas de `/monografias/` para bancas, participantes,
membros externos e avaliações. Todas as telas permitem consultar, cadastrar,
editar e excluir, respeitando os vínculos protegidos e as validações da API.

## Documentação

A pasta `docs/` é documentação local de trabalho e está excluída do Git por
decisão do projeto. Na cópia local, ela contém:

- `CRUD.md`: contrato, rotas e exemplos da API.
- `DESENVOLVIMENTO.md`: fluxo para adicionar entidades, mapeamentos, serviços e telas.
- `PENDENCIAS.md`: acompanhamento do plano de refatoração.
- `COMMITS.md`: sequência dos commits, arquivos envolvidos e validação da entrega.

O plano original está versionado em `Plano_Refatoracao_CRUD_API_Monografias.pdf`.

O CRUD atual é administrativo. Submissão, aprovação, convites, upload e
publicação são próximas entregas. Também faltam permissões acadêmicas por
papel/objeto, confirmação de convites, cálculo de resultados, catálogo público
e auditoria automática. Os modelos de documentos e histórico já existem.

## Organização e fluxo Git

As entidades ficam em `models.py` nos apps `equipe` e `monografias`.
Formulários, serializers, serviços, API e rotas ficam nos arquivos de mesmo
nome desses apps. `home` contém a página inicial e os recursos compartilhados
do navegador. O projeto continua usando templates Django e Bootstrap.

O fluxo de branches segue `main` → `develop` → `feature/<nome>`.
Trabalhos novos partem de `develop` e retornam a ela por revisão; uma entrega
estável segue para `main` pelo fluxo de release. Correções urgentes de uma
versão publicada podem usar `hotfix/<nome>`.

Os commits usam `tipo(escopo): descrição`, com tipos como `refactor`, `feat`,
`fix`, `test`, `docs` e `chore`. Cada commit descreve uma responsabilidade ou
regra de negócio, com detalhes no corpo da mensagem. Migrações acopladas são
mantidas juntas. Dados locais, ambiente virtual, uploads e `docs/` ficam fora
do versionamento.

## Testes

Para executar os testes em um banco PostgreSQL isolado:

```bash
env/bin/python scripts/postgres_local.py start --test-database
env/bin/python manage.py test --keepdb --noinput
```

Os testes ficam em `monografias/tests.py` (API e regras de negócio),
`monografias/test_migrations.py` (migrações), `home/test_interface.py`
(login e formulários) e `home/test_browser.py` (navegador).

Para incluir os testes opcionais no Chrome/Chromium:

```bash
env/bin/python -m pip install -r requirements-dev.txt
RUN_BROWSER_TESTS=1 env/bin/python manage.py test --keepdb --noinput
```

Se não houver Chrome/Chromium instalado no sistema, execute antes
`env/bin/python -m playwright install chromium`.

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
