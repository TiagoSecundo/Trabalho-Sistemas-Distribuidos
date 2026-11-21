# AllTeam Monografias

Aplicação acadêmica para organizar monografias, alunos, professores, cursos,
bancas, participantes e avaliações. Usa Django, Django REST Framework,
PostgreSQL, django-allauth e páginas Django com Bootstrap e JavaScript nativo.

Documentação revisada em **20/11/2026**, após `5f7857b` (PR #3), a entrega
dos painéis por perfil, a limpeza do legado, as correções de login/cadastro e a
revisão de permissões conforme o escopo anexado. O plano original continua em
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
| `MICROSERVICO_JWT_SIGNING_KEY` | Chave compartilhada de 32+ caracteres para emitir JWT ao microserviço; necessária apenas para essa rota |

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
acadêmicos e `Administradores`, mas não atribui usuários, permissões Django ou vínculos acadêmicos.
`migrate` também aplica as migrações do django-allauth; o app `usuarios` não
introduziu tabelas próprias nesta entrega.

Após reiniciar o computador, execute `start` novamente. Depois de um pull,
atualize dependências, preserve/preencha `.env`, execute `start`, `migrate`,
`configurar_grupos` e `check` antes de iniciar o servidor. A dependência
`djangorestframework-simplejwt` veio do PR #4; reinstale `requirements.txt`
após atualizar a branch.

## Acesso e papéis

| Entrada | Comportamento atual |
| --- | --- |
| `/accounts/signup/` e `/accounts/login/` | Cadastro e login django-allauth, por usuário ou e-mail, com confirmação de e-mail opcional |
| `/usuarios/painel/` | Abre o painel do perfil disponível; destino padrão do login allauth |
| `/entrar/` e `/api-auth/login/` | Mesmo login allauth para todos os perfis; aceita usuário/e-mail e preserva `next` local |
| `/sair/`, `/accounts/logout/` e `/api-auth/logout/` | Logout por POST com CSRF; retorna à tela de login para trocar de conta |
| `/admin/` | Administração Django |
| `/api/` | Referência navegável por perfil, com identidade, recursos acadêmicos e CRUDs administrativos conforme autorização |

O backend de e-mail atual escreve as mensagens no terminal; não envia e-mail
real. A confirmação de e-mail não é exigida para entrar; mensagens geradas podem ser
consultadas no console durante o desenvolvimento.
Criar conta no allauth não cria Aluno/Professor nem concede um papel acadêmico.

O formulário de `/accounts/signup/` usa o layout do projeto e salva a conta em
`auth_user`, o e-mail do allauth e a auditoria na mesma transação. Senhas
divergentes/fracas, usuário ou e-mail já utilizados aparecem junto aos campos;
o formulário preserva usuário/e-mail e limpa as senhas. Após salvar, mostra
**Conta criada com sucesso** no painel. A conta também aparece em
**Contas e acessos** (`/admin/auth/user/`, conforme as permissões do administrador).
Esse cadastro funciona por POST com CSRF, inclusive sem JavaScript.

Para o acesso administrativo local:

```bash
env/bin/python manage.py createsuperuser
```

Os perfis acadêmicos são calculados pelos vínculos cadastrados pela
administração. `is_staff` sozinho **não concede o papel Administrador**.

| Papel | Requisitos para conta ativa |
| --- | --- |
| Aluno | `Aluno.usuario` vinculado à conta |
| Professor | `Professor.usuario` vinculado à conta |
| Coordenador | Professor da conta indicado em `Curso.coordenador` |
| Administrador | `is_superuser=True` ou grupo explícito `Administradores` |

Para liberar o acesso após o cadastro/login:

1. Entre como administrador e abra **Cadastros → Alunos** ou **Professores**.
2. Crie/edite o cadastro acadêmico, selecione **Conta de acesso** e salve.
3. Para coordenador, selecione o professor em **Cursos → Coordenador**.
4. A conta vinculada recebe o perfil na próxima requisição ao painel/API,
   sem precisar recriar o login ou adicionar grupos acadêmicos manualmente.

O cadastro público não permite escolher privilégios. Grupos `Alunos`,
`Professores` e `Coordenadores` são mantidos por compatibilidade; sozinhos não
liberam acesso, e não são necessários quando há vínculo. Remover o vínculo
revoga o papel correspondente. Administrador pode acumular papéis acadêmicos.
O acesso a `/admin/` exige também `is_staff` e as permissões de model do Django;
professor/aluno marcado apenas como staff não entra nessa administração.

O login do sistema, os aliases `/entrar/` e `/api-auth/login/` usam a mesma
tela allauth, com destino padrão `/usuarios/painel/`. A API navegável oferece
links para entrar, acessar o painel e sair da mesma sessão. `/api/` reconhece
todos os perfis; os oito CRUDs e suas telas exigem Administrador. Os recursos acadêmicos
em `/api/usuarios/` mantêm a autorização por papel e vínculo.

A sessão tem prioridade sobre HTTP Basic e exige CSRF nas escritas. Requisições
de navegador ignoram Basic retido e não abrem o diálogo nativo de credenciais;
clientes como Postman/curl sem sessão continuam usando Basic. `/admin/` mantém
o login próprio da administração Django, com a mesma verificação do papel.
Recuperação de senha completa e identidade entre serviços continuam pendentes.

## Telas dos perfis

Entre em `/accounts/login/` e abra **Meu painel**. O painel padrão prioriza
Administrador, Coordenador, Professor e Aluno, conforme os papéis disponíveis.
Quem acumula papéis acadêmicos alterna entre eles pela navegação do painel.

| Perfil e rota | Funções disponíveis |
| --- | --- |
| Aluno — `/usuarios/painel/aluno/` | Próprios trabalhos, busca/status/paginação, contadores, próximas bancas e criação/edição/exclusão de rascunhos |
| Professor — `/usuarios/painel/professor/` | Orientações/coorientações, filtro por vínculo, participações em bancas não canceladas e convites externos quando é o orientador principal |
| Coordenador — `/usuarios/painel/coordenador/` | Trabalhos/bancas dos cursos coordenados e emissão de convites externos elegíveis |
| Administrador — `/usuarios/painel/administrador/` | Visão geral, cadastros e links da gestão; administração de contas conforme permissões Django |

Sem vínculo acadêmico ou papel administrativo, a conta recebe uma orientação para solicitar a associação à
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
| `GET /api/usuarios/monografias/` | Resumo dos trabalhos do aluno, orientados/coorientados e participações em bancas do professor, do curso coordenado ou todos para Administrador |
| `GET/POST /api/usuarios/rascunhos/` | Lista de trabalhos próprios e criação de rascunho pelo aluno |
| `GET/PATCH/DELETE /api/usuarios/rascunhos/{id}/` | Consulta própria; alteração/exclusão apenas em `RASCUNHO` |
| `POST /api/usuarios/convites/{id}/emitir/` | Emissão de token de participação externa pelo orientador principal, coordenação do curso ou Administrador |
| `POST /api/usuarios/convites/{id}/confirmar/` | Confirmação sem conta, com token válido e limitado à participação |
| `POST /api/usuarios/token-microservico/` | Emissão de JWT curto para o papel acadêmico escolhido na sessão; exige CSRF e chave compartilhada configurada |

Na criação acadêmica, aluno e curso vêm do servidor. O token externo tem
hash persistido, validade e bloqueio de nova confirmação após o aceite.
Seu `{id}` é o ID da participação, não da banca. A emissão exige monografia
aprovada pelo orientador ou com banca agendada, banca `AGENDADA` e participação
`CONVIDADO`. Ainda não há ação de submissão/aprovação para alcançar esses
estados pela aplicação; o teste prepara esse estado diretamente no banco.

A rota de JWT recebida do PR #4 aceita somente sessão autenticada e POST com
CSRF. Para uma conta com mais de um papel, envie `role=aluno`, `orientador`,
`coordenador` ou `admin` conforme o perfil autorizado; para um único papel,
`role` é opcional. A resposta traz `access` (Bearer) e validade de dez minutos.
Sem `MICROSERVICO_JWT_SIGNING_KEY` válida, responde 503; o restante do sistema
continua funcionando. O verificador do microserviço precisa usar a mesma chave
e as mesmas regras de assinatura. A emissão foi testada localmente, mas chamadas
reais entre serviços, revogação de tokens e sincronização de dados ainda faltam.

A auditoria registra login/logout, escritas dos CRUDs REST e formulários HTML,
rascunhos acadêmicos e emissão/confirmação de convites. Falta completar os
fluxos acadêmicos, a consulta autorizada do histórico e sua política de retenção.

Continuam pendentes submissão, aprovação/devolução, disponibilidade e quórum de
banca, recusa e convites internos, avaliação pelo próprio participante,
fechamento de resultado, upload/download de PDF, publicação e catálogo público.
Os painéis já atendem às funções disponíveis no principal; o percurso completo
depende desses processos e da integração descrita em B17. O PR #4 adicionou
o emissor JWT local, sem comprovar o consumo do token pelo microserviço.

## Documentação e organização

A documentação canônica é versionada na raiz, consolidando as cópias enviadas
pela equipe:

- [CRUD.md](CRUD.md): contratos, exemplos, telas, convites e auditoria.
- [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md): configuração, arquitetura e extensão.
- [PENDENCIAS.md](PENDENCIAS.md): backlog B01–B17 e pendências do microserviço.
- [ESCOPO_E_ACESSOS.md](ESCOPO_E_ACESSOS.md): comparação com o enunciado anexado e matriz de acesso.
- [COMMITS.md](COMMITS.md): histórico, validação e limpeza desta entrega.

`docs/` continua ignorada pelo Git, com cópias locais e o documento recebido
`PENDENCIAS_ATUALIZADO.md`. A decisão desse documento de não criar telas foi
substituída pelo pedido de entregar os perfis. E-mail opcional foi mantido.
O enunciado anexado exige IP/VPN institucional; esse controle continua ausente
e está registrado como pendência, apesar da retirada anterior pela equipe. O relatório do microserviço foi incorporado ao backlog
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
| `home/test_interface.py` | Login compartilhado, formulários administrativos, API e respostas HTML |
| `usuarios/tests.py` | Identidade, visibilidade do aluno e restrição administrativa |
| `usuarios/tests_security.py` | Papéis/vínculos, rascunhos próprios, tokens e auditoria |
| `usuarios/test_interface.py` | Painéis, acesso por perfil/objeto, e-mail opcional, HTML, CSRF e auditoria |
| `usuarios/test_login_api.py` | Dez testes de login por perfil/rota, troca de usuário, sessão/Basic, CSRF, API navegável e redirects |
| `usuarios/test_papeis.py` | Separação de staff/admin, vínculos, revogação, coordenação, bancas e convites do orientador |
| `usuarios/test_cadastro.py` | Oito testes de cadastro, persistência, validação, CSRF, privilégios, rollback e integração com usuários |
| `home/test_browser.py` e `usuarios/test_browser.py` | Seis testes opcionais no navegador para os CRUDs, perfis, troca de conta e cadastro público |

Após o merge do PR #4, a suíte completa passou com **115 testes**, incluindo
seis fluxos Chrome, sem
falhas ou testes ignorados. Há cobertura do cadastro até o vínculo acadêmico e
o login com a nova conta, staff sem privilégios administrativos, revogação,
isolamento por curso/trabalho, participações em bancas e convite do orientador.
Consulte [COMMITS.md](COMMITS.md). O microserviço separado não foi executado ou
integrado nesta revisão.

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
