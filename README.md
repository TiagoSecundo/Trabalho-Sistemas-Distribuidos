# AllTeam Monografias

Aplicação acadêmica para organizar monografias, alunos, professores, cursos,
bancas, participantes e avaliações. Usa Django, Django REST Framework,
PostgreSQL, django-allauth e páginas Django com Bootstrap e JavaScript nativo.

Documentação revisada em **20/11/2026**, após `5f7857b` (PR #3), a entrega
dos painéis por perfil e a limpeza do legado. O plano original continua em
[Plano_Refatoracao_CRUD_API_Monografias.pdf](Plano_Refatoracao_CRUD_API_Monografias.pdf);
o estado atual de B01–B17 está em [PENDENCIAS.md](PENDENCIAS.md).

## Executar localmente no Ubuntu

O ambiente verificado usa Python 3.12, Django 6.0.4 e PostgreSQL 16. O servidor
PostgreSQL e `pg_config` precisam estar instalados. O script do projeto gerencia
uma instância local pelo usuário atual, sem `sudo`, na porta 5433.

Se ainda não existir o ambiente virtual, crie-o:

```bash
python3 -m venv env
```

Instale ou atualize as dependências, inclusive depois de puxar alterações:

```bash
env/bin/python -m pip install -r requirements.txt
```

### Configuração do .env

Somente se ainda não houver `.env`, copie o modelo:

```bash
cp .env.example .env
```

Preencha os valores na raiz do projeto:

| Variável | Configuração local |
| --- | --- |
| `DJANGO_SECRET_KEY` | Chave aleatória própria deste ambiente, mantida entre execuções |
| `POSTGRES_PASSWORD` | Senha do usuário `curso_django_app` no banco local existente |
| `DJANGO_DEBUG` | `1` para desenvolvimento HTTP local |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` |

Para gerar a chave e copiá-la para `DJANGO_SECRET_KEY`:

```bash
env/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Coloque a chave entre aspas simples no `.env`. Não mantenha os valores
`SUBSTITUA_...`. Em um banco novo, escolha uma senha local: o script usa esse
valor ao criar o usuário. Em banco existente, use a senha já configurada;
alterar `.env` não altera a senha do usuário PostgreSQL.

`Curso_Django/settings.py` carrega o arquivo com `python-dotenv`. Variáveis já
exportadas no terminal têm precedência. `.env` é ignorado pelo Git e não vem
no pull. Sem `DJANGO_SECRET_KEY` ou `POSTGRES_PASSWORD`, a configuração falha
com `KeyError`. Sem as dependências novas, ocorre `ModuleNotFoundError` para
`dotenv` ou `allauth`. Com `DJANGO_DEBUG` ausente ou `0`, o código ativa
redirecionamento para HTTPS e cookies seguros; para o servidor local use `1`.

### Banco e servidor

Com o `.env` preenchido:

```bash
env/bin/python scripts/postgres_local.py start
env/bin/python manage.py migrate
env/bin/python manage.py configurar_grupos
env/bin/python manage.py check
env/bin/python manage.py runserver
```

Acesse <http://127.0.0.1:8000/>. Se necessário, use `runserver 8001` e a porta
8001 no navegador. O comando `configurar_grupos` é idempotente: cria os grupos
acadêmicos, mas não atribui usuários, permissões Django ou vínculos acadêmicos.
`migrate` também aplica as migrações do django-allauth; o app `usuarios` não
introduziu tabelas próprias nesta entrega.

Após reiniciar o computador, execute `start` novamente. Depois de um pull,
atualize dependências, preserve/preencha `.env`, execute `start`, `migrate`,
`configurar_grupos` e `check` antes de iniciar o servidor.

## Acesso e papéis

| Entrada | Comportamento atual |
| --- | --- |
| `/accounts/signup/` e `/accounts/login/` | Cadastro e login django-allauth, por usuário ou e-mail, com confirmação de e-mail opcional |
| `/usuarios/painel/` | Abre o painel do perfil disponível; destino padrão do login allauth |
| `/entrar/` e `/sair/` | Login administrativo legado e logout por POST; login sem `next` válido segue para `/monografias/` |
| `/admin/` | Administração Django |
| `/api/` e `/api-auth/login/` | Referência navegável dos oito CRUDs administrativos e login do DRF |

O backend de e-mail atual escreve as mensagens no terminal; não envia e-mail
real. A confirmação de e-mail não é exigida para entrar; mensagens geradas podem ser
consultadas no console durante o desenvolvimento.
Criar conta no allauth não cria Aluno/Professor nem concede um papel acadêmico.

Para o acesso administrativo local:

```bash
env/bin/python manage.py createsuperuser
```

Para um usuário acadêmico, atribua o grupo no admin e vincule a conta ao
cadastro correspondente. A resolução em `usuarios/roles.py` exige:

| Papel | Requisitos |
| --- | --- |
| Aluno | Grupo `Alunos` e `Aluno.usuario` vinculado |
| Professor | Grupo `Professores` e `Professor.usuario` vinculado |
| Coordenador | Grupo `Coordenadores`, vínculo com Professor e indicação em `Curso.coordenador` |
| Administrador | Usuário ativo com `is_staff=True`; esse papel tem precedência na resolução |

Oito CRUDs em `/api/` e suas telas continuam restritos a staff. Os acessos
acadêmicos usam `/api/usuarios/`, conforme a tabela abaixo. Login legado,
admin e Basic Auth continuam disponíveis: a política entre esses acessos e a recuperação de senha ainda precisam ser
consolidadas. A navbar já oferece painel e logout para qualquer conta autenticada.

## Telas dos perfis

Entre em `/accounts/login/` e abra **Meu painel**. O painel padrão prioriza
Administrador, Coordenador, Professor e Aluno, conforme os papéis disponíveis.
Quem acumula papéis acadêmicos alterna entre eles pela navegação do painel.

| Perfil e rota | Funções disponíveis |
| --- | --- |
| Aluno — `/usuarios/painel/aluno/` | Próprios trabalhos, busca/status/paginação, contadores, próximas bancas e criação/edição/exclusão de rascunhos |
| Professor — `/usuarios/painel/professor/` | Orientações e coorientações, detalhes e bancas vinculadas |
| Coordenador — `/usuarios/painel/coordenador/` | Trabalhos/bancas dos cursos coordenados e emissão de convites externos elegíveis |
| Administrador — `/usuarios/painel/administrador/` | Visão geral, cadastros e links da gestão; administração de contas conforme permissões Django |

Sem grupo/vínculo, a conta recebe uma orientação para solicitar a associação à
administração. Ocultar links não é a proteção: as views verificam papel e
objeto, e as consultas de HTML/API compartilham o escopo acadêmico.

As páginas de rascunho ficam em `/usuarios/rascunhos/novo/`,
`/usuarios/rascunhos/{id}/editar/` e `/usuarios/rascunhos/{id}/excluir/`.
O detalhe está em `/usuarios/trabalhos/{id}/`. Alterações usam a API com
JavaScript; POST HTML também funciona, com os mesmos serviços e auditoria.

Convites elegíveis são emitidos pelos detalhes do trabalho ou em
`/usuarios/convites/{participacao_id}/emitir/`. O emissor recebe endereço e código
para entrega manual. O externo acessa `/usuarios/convites/{participacao_id}/`
e informa o código, sem conta. O código não é colocado na URL; não há envio
automático de e-mail. Essas telas não implementam submissão, aprovação,
avaliação, publicação ou integração do microserviço.

## Funcionalidades entregues

Os oito CRUDs administrativos cobrem alunos, professores, cursos, monografias,
bancas, participações, membros externos e avaliações. Possuem validação,
busca, paginação, ordenação, exclusão protegida e telas integradas à API.
Comece por `/equipe/` e depois use `/monografias/` e suas abas.

Os commits de autenticação acrescentaram:

| Rota | Entrega |
| --- | --- |
| `GET /api/usuarios/me/` | Identidade e papéis da conta autenticada |
| `GET /api/usuarios/monografias/` | Resumo dos trabalhos do aluno, orientados/coorientados do professor, do curso coordenado ou todos para staff |
| `GET/POST /api/usuarios/rascunhos/` | Lista de trabalhos próprios e criação de rascunho pelo aluno |
| `GET/PATCH/DELETE /api/usuarios/rascunhos/{id}/` | Consulta própria; alteração/exclusão apenas em `RASCUNHO` |
| `POST /api/usuarios/convites/{id}/emitir/` | Emissão de token de participação externa pela coordenação do curso ou staff |
| `POST /api/usuarios/convites/{id}/confirmar/` | Confirmação sem conta, com token válido e limitado à participação |

Na criação acadêmica, aluno e curso vêm do servidor. O token externo tem
hash persistido, validade e bloqueio de nova confirmação após o aceite.
Seu `{id}` é o ID da participação, não da banca. A emissão exige monografia
aprovada pelo orientador ou com banca agendada, banca `AGENDADA` e participação
`CONVIDADO`. Ainda não há ação de submissão/aprovação para alcançar esses
estados pela aplicação; o teste prepara esse estado diretamente no banco.

A auditoria registra login/logout, escritas dos CRUDs REST e formulários HTML,
rascunhos acadêmicos e emissão/confirmação de convites. Falta completar os
fluxos acadêmicos, a consulta autorizada do histórico e sua política de retenção.

Continuam pendentes submissão, aprovação/devolução, disponibilidade e quórum de
banca, recusa e convites internos, avaliação pelo próprio participante,
fechamento de resultado, upload/download de PDF, publicação e catálogo público.
Os painéis já atendem às funções disponíveis no principal; o percurso completo
depende desses processos e da integração descrita em B17.

## Documentação e organização

A documentação canônica é versionada na raiz, consolidando as cópias enviadas
pela equipe:

- [CRUD.md](CRUD.md): contratos, exemplos, telas, convites e auditoria.
- [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md): configuração, arquitetura e extensão.
- [PENDENCIAS.md](PENDENCIAS.md): backlog B01–B17 e pendências do microserviço.
- [COMMITS.md](COMMITS.md): histórico, validação e limpeza desta entrega.

`docs/` continua ignorada pelo Git, com cópias locais e o documento recebido
`PENDENCIAS_ATUALIZADO.md`. A decisão desse documento de não criar telas foi
substituída pelo pedido atual de entregar os perfis. E-mail opcional e retirada
de IP/VPN foram mantidos. O relatório do microserviço foi incorporado ao backlog
como evidência recebida, sem declarar integração ou execução local desse serviço.

`equipe` e `monografias` mantêm os models; `usuarios` contém papéis, consultas,
serviços acadêmicos, API e telas; `home` contém início e recursos compartilhados.
`Curso_Django` é a configuração única. Foram removidos o pacote `cursodjango`,
o alias `requeriments.txt`, o conversor/patch de segurança obsoletos, esqueletos
vazios e cópias numeradas dos documentos. `db.sqlite3.backup` fica apenas local.
As migrações e `Equipe` foram preservadas porque ainda sustentam a transição do legado.

O fluxo recomendado continua `main` → `develop` → `feature/<nome>`, com commits
`tipo(escopo): descrição`. A branch `develop` local ainda tem a base antiga
`abf487f`; esta entrega parte da `main` atual e é integrada nela após validação.
Detalhes dos commits e do merge ficam em [COMMITS.md](COMMITS.md).

## Testes

Com dependências e `.env` configurados, prepare o banco separado e execute:

```bash
env/bin/python scripts/postgres_local.py start --test-database
env/bin/python manage.py test --keepdb --noinput
env/bin/python manage.py makemigrations --check --dry-run
env/bin/python manage.py check
```

Use `--keepdb`: o usuário da aplicação não tem permissão de criar/remover
bancos. O script prepara `test_curso_django_dev`; não use o banco da aplicação
para fixtures ou limpeza de testes.

| Arquivo | Cobertura |
| --- | --- |
| `monografias/tests.py` | Oito CRUDs, regras, sessão/Basic, CSRF e integridade |
| `monografias/test_migrations.py` | Migração vazia e bloqueio de conversão do legado sem mapeamento |
| `home/test_interface.py` | Login administrativo, formulários, API e respostas HTML |
| `usuarios/tests.py` | Identidade, visibilidade do aluno e restrição administrativa |
| `usuarios/tests_security.py` | Papéis/vínculos, rascunhos próprios, tokens e auditoria |
| `usuarios/test_interface.py` | Painéis, acesso por perfil/objeto, e-mail opcional, HTML, CSRF e auditoria |
| `home/test_browser.py` e `usuarios/test_browser.py` | Quatro testes opcionais no navegador para os CRUDs administrativos e perfis |

A validação desta entrega teve **78 testes aprovados, sem testes ignorados**,
com Django/PostgreSQL e os fluxos de navegador (`RUN_BROWSER_TESTS=1`). `check` passou e não há alterações de migração.
Consulte [COMMITS.md](COMMITS.md) para os resultados finais. O microserviço
separado não foi executado ou integrado nesta revisão.

Para executar também os testes de navegador:

```bash
env/bin/python -m pip install -r requirements-dev.txt
RUN_BROWSER_TESTS=1 env/bin/python manage.py test --keepdb --noinput
```

Se não houver Chrome/Chromium instalado, execute antes
`env/bin/python -m playwright install chromium`.

## Conexão PostgreSQL

| Campo | Valor |
| --- | --- |
| Host | `127.0.0.1` |
| Porta | `5433` |
| Banco / maintenance database | `curso_django_dev` |
| Usuário | `curso_django_app` |
| Senha | `POSTGRES_PASSWORD` do `.env` local |

Dados e logs ficam em `.postgres/`, ignorado pelo Git. Essa instância é
independente de um banco anterior na porta 5432; o script não importa dados
nem redefine a senha de um usuário já existente.

```bash
env/bin/python scripts/postgres_local.py status
env/bin/python scripts/postgres_local.py stop
```
