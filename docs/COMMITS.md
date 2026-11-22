# Registro dos commits e das entregas

## Entrega local de interface, B12 e B13 — 22/11/2026

Base: `aca1766`, após atualizar `origin` e conferir a integração anterior.
A entrega é registrada na branch `feature/publicacao-repositorio-b12-b13`
e integrada à `main` com merge `--no-ff`, conforme pedido do integrante.
O push ao remoto não foi solicitado.

Conteúdo: telas iniciais/contas, documentos privados e publicação automática
B12, catálogo/API anônimos B13, indexação PostgreSQL por RabbitMQ com outbox,
migrações, testes e instruções de operação. Os documentos canônicos foram
preservados em `docs/` e incluídos no versionamento por exceções explícitas
no `.gitignore`. `.env`, arquivos enviados, bancos e credenciais ficam fora do Git.

Evidências anteriores ao commit: suíte padrão com **216 testes encontrados,
201 aprovados e 15 opcionais ignorados**; B13 com **20 testes de backend,
2 de navegador e 3 de RabbitMQ real** aprovados. B12 teve **24 testes de
regras, 2 de navegador e 2 de integração HTTP/JWT real** aprovados.
Os ajustes finais de detalhe via API e correspondência de hash do índice
foram verificados com testes direcionados. Migrações aplicadas, `check`,
consistência de migrações, sintaxe JavaScript e `git diff --check` aprovados.

Consulte os hashes com `git log --first-parent --oneline main` e
`git log --oneline feature/publicacao-repositorio-b12-b13 -1`.
A revisão do novo backlog da Parte 1 começa após esse merge, em entrega separada.

Registro canônico versionado, consolidado em **20/11/2026**. A entrega dos
perfis parte de `5f7857b` (PR #3). As seções da refatoração e autenticação
preservam o histórico anterior; o resultado dos painéis e da limpeza está
no fim deste documento. `docs/COMMITS.md` é apenas uma cópia local.

## Estado observado antes desta entrega

| Referência local | Commit | Situação |
| --- | --- | --- |
| `main` e `origin/main` | `5f7857b` | Merge do PR #3 de autenticação |
| `origin/feature/autenticacao` | `0178003` | E-mail opcional e documentos recebidos |
| `feature/refatoracao-crud-monografias` e sua referência origin | `70b1cb9` | Série de refatoração já integrada pelo PR #1 |
| `develop` | `abf487f` | Base antiga; não recebeu as integrações observadas em main |

O registro considera as referências já disponíveis nesta cópia do repositório;
não pressupõe atualização de branches além desse histórico. A recomendação de
Gitflow continua válida, mas os merges observados foram feitos diretamente em
`main`. O histórico anterior documenta as entregas; os commits desta revisão são
registrados após a validação dos painéis.

## Linha do tempo

| Data | Commit(s) | Entrega |
| --- | --- | --- |
| 10/11/2026 | `74e3114` | Primeiro commit |
| 15/11/2026 | `abf487f` | Configuração inicial do PostgreSQL |
| 15/11/2026 | `00ff6c8` a `70b1cb9` | 11 commits de refatoração, CRUD, interface, testes e documentação |
| 15/11/2026 | `14543ac` | Merge do PR #1, `feature/refatoracao-crud-monografias` |
| 20/11/2026 | `39d076d` | Alteracoes autenticacao |
| 20/11/2026 | `fda173a` | finalizando autenticacao |
| 20/11/2026 | `9d04dc0` | Merge do PR #2, `feature/autenticacao` |
| 20/11/2026 | `0178003`, `5f7857b` | E-mail opcional, documentos e merge do PR #3 |

## Série de refatoração de 15/11

A implementação partiu de `abf487f` e foi organizada em 11 commits na branch
`feature/refatoracao-crud-monografias`. O texto a seguir preserva o registro
por responsabilidade. Ambiente virtual, PostgreSQL, uploads e docs/ ficaram
fora dessa série; o PDF original foi versionado com o README.

## Critério de separação

Primeiro foram isolados arquivos locais e refatorações de infraestrutura/modelagem.
As duas migrações relacionadas foram mantidas no mesmo commit para preservar
suas dependências. Os CRUDs foram separados por área de negócio: cadastros
acadêmicos, monografias, bancas/participações e avaliações. A integração das telas,
os testes e as instruções de execução foram registrados depois.

Arquivos compartilhados de serializers, serviços e router foram adicionados
incrementalmente ao índice. Os fontes finais do workspace foram preservados;
as consultas e os templates antigos receberam adaptações mínimas no commit
de modelagem até a entrada da nova interface. Foram removidas apenas linhas
vazias excedentes no fim de quatro arquivos, identificadas pelo git diff --check.

## Sequência dos 11 commits de refatoração

| Ordem | Commit | Responsabilidade |
| --- | --- | --- |
| 1 | `00ff6c8` | chore(git): manter docs e arquivos locais fora do versionamento |
| 2 | `5a499de` | refactor(core): unificar dependencias e preparar a base dos CRUDs |
| 3 | `f67bd16` | refactor(dominio): corrigir entidades e proteger vinculos academicos |
| 4 | `1b0c85d` | feat(academico): disponibilizar CRUD de alunos professores e cursos |
| 5 | `dc0a87c` | feat(monografias): disponibilizar CRUD de trabalhos e orientacoes |
| 6 | `adfa801` | feat(bancas): cadastrar bancas participantes e membros externos |
| 7 | `d51dc40` | feat(avaliacoes): registrar notas pareceres e recomendacoes |
| 8 | `443a028` | feat(web): integrar os oito CRUDs as paginas de gestao de monografias |
| 9 | `b25f041` | test(api): cobrir regras de negocio e migracoes no PostgreSQL |
| 10 | `2b98c4a` | test(web): validar formularios e fluxos reais no navegador |
| 11 | `70b1cb9` | docs(projeto): registrar execucao arquitetura e fluxo de contribuicao |

## Conteúdo de cada commit

### 1. 00ff6c8 — chore(git): manter docs e arquivos locais fora do versionamento

Ignora docs/, dados do PostgreSQL e uploads locais.

Preserva os arquivos no workspace e evita incluí-los nos próximos commits.

Arquivos:

- `.gitignore`

### 2. 5a499de — refactor(core): unificar dependencias e preparar a base dos CRUDs

Centraliza dependências no requirements.txt e configura DRF administrativo.

Compartilha validação dos models, escrita transacional, bloqueio de registros e erros de conflito.

Preserva autenticação Basic para clientes da API e trata chamadas da interface sem diálogo nativo de credenciais.

Arquivos:

- `Curso_Django/api.py`
- `Curso_Django/authentication.py`
- `Curso_Django/services.py`
- `Curso_Django/settings.py`
- `requeriments.txt`
- `requirements.txt`

### 3. f67bd16 — refactor(dominio): corrigir entidades e proteger vinculos academicos

Modela alunos, professores e cursos; refatora Monografia e adiciona bancas, participantes, avaliações, documentos e histórico.

Mantém Equipe legada e agrupa as migrações dependentes com proteção contra conversão de dados sem mapeamento.

Aplica unicidade, PROTECT, invariantes e campos explícitos; adapta consultas e templates antigos ao vínculo aluno.

Arquivos:

- `equipe/admin.py`
- `equipe/migrations/0002_professor_curso_aluno.py`
- `equipe/models.py`
- `monografias/admin.py`
- `monografias/forms.py`
- `monografias/migrations/0002_dominio_academico.py`
- `monografias/models.py`
- `monografias/templates/detalhes.html`
- `monografias/templates/monografias.html`
- `monografias/views.py`

### 4. 1b0c85d — feat(academico): disponibilizar CRUD de alunos professores e cursos

Publica as três coleções administrativas com busca, paginação e ordenação.

Valida matrícula, código, e-mail e relações acadêmicas, protegendo dependências na exclusão.

Inclui nomes de relações somente leitura nas respostas JSON.

Arquivos:

- `Curso_Django/api_urls.py`
- `Curso_Django/urls.py`
- `equipe/api.py`
- `equipe/serializers.py`

### 5. dc0a87c — feat(monografias): disponibilizar CRUD de trabalhos e orientacoes

Publica criação, consulta, edição e exclusão de rascunhos.

Valida curso do aluno, orientadores distintos e palavras-chave; mantém status e datas do processo somente leitura.

Centraliza o bloqueio de alteração de trabalhos fora de rascunho no serviço de monografias.

Arquivos:

- `Curso_Django/api_urls.py`
- `monografias/api.py`
- `monografias/serializers.py`
- `monografias/services.py`

### 6. adfa801 — feat(bancas): cadastrar bancas participantes e membros externos

Publica os CRUDs de banca, membro externo e participação.

Valida intervalo, local/link por modalidade e um único tipo de avaliador por participação.

Protege vínculos duplicados, participação já avaliada e bancas realizadas ou canceladas; convites automáticos permanecem pendentes.

Arquivos:

- `Curso_Django/api_urls.py`
- `monografias/api.py`
- `monografias/serializers.py`
- `monografias/services.py`

### 7. d51dc40 — feat(avaliacoes): registrar notas pareceres e recomendacoes

Completa a API com avaliação única por participante, nota de zero a dez e recomendação acadêmica.

Impede alteração e exclusão de avaliações finalizadas e mantém datas do processo somente leitura.

O cadastro administrativo ainda não calcula nem fecha o resultado da defesa.

Arquivos:

- `Curso_Django/api_urls.py`
- `monografias/api.py`
- `monografias/serializers.py`
- `monografias/services.py`

### 8. 443a028 — feat(web): integrar os oito CRUDs as paginas de gestao de monografias

Reaproveita Django templates e Bootstrap, com login administrativo e navegação voltada a trabalhos e bancas.

Integra GET, POST, PATCH e DELETE com sessão, CSRF, busca, paginação, erros por campo e confirmação de exclusão.

Compartilha serviços com o POST HTML, preserva rotas antigas e ajusta layout móvel e tratamento de sessão expirada.

Arquivos:

- `Curso_Django/interface.py`
- `Curso_Django/settings.py`
- `Curso_Django/urls.py`
- `equipe/forms.py`
- `equipe/interface.py`
- `equipe/templates/adicionar_equipe.html`
- `equipe/templates/equipe.html`
- `equipe/urls.py`
- `equipe/views.py`
- `home/forms.py`
- `home/static/home/crud.css`
- `home/static/home/crud.js`
- `home/templates/index.html`
- `monografias/interface.py`
- `monografias/templates/adicionar_monografia.html`
- `monografias/templates/confirmar_exclusao.html`
- `monografias/templates/detalhes.html`
- `monografias/templates/monografias.html`
- `monografias/urls.py`
- `monografias/views.py`
- `templates/base.html`
- `templates/crud/cabecalho.html`
- `templates/crud/detalhes.html`
- `templates/crud/excluir.html`
- `templates/crud/feedback.html`
- `templates/crud/formulario.html`
- `templates/crud/lista.html`
- `templates/navbar.html`
- `templates/registration/login.html`

### 9. b25f041 — test(api): cobrir regras de negocio e migracoes no PostgreSQL

Adiciona testes dos oito CRUDs, autenticação, CSRF, invariantes, estados e exclusão protegida.

Verifica migrações vazias e recusa conversão do legado sem mapeamento.

Prepara banco de testes separado com --test-database e uso de --keepdb.

Arquivos:

- `monografias/test_migrations.py`
- `monografias/tests.py`
- `scripts/postgres_local.py`

### 10. 2b98c4a — test(web): validar formularios e fluxos reais no navegador

Testa páginas, login, redirecionamentos, opções de relações e mensagens da interface.

Acrescenta testes opcionais no Chrome para CRUD, busca, paginação, sessão expirada, rede, conteúdo escapado e layout móvel.

Isola o Playwright nas dependências de desenvolvimento; suíte completa validada anteriormente com 46 testes.

Arquivos:

- `home/test_browser.py`
- `home/test_interface.py`
- `requirements-dev.txt`

### 11. 70b1cb9 — docs(projeto): registrar execucao arquitetura e fluxo de contribuicao

Atualiza instruções de execução, acesso administrativo, funcionalidades e limites da entrega.

Documenta organização dos apps, branches Gitflow, padrão das mensagens e execução dos testes.

Versiona o plano original na raiz; docs/ permanece exclusivamente local, sem links remotos quebrados.

Arquivos:

- `Plano_Refatoracao_CRUD_API_Monografias.pdf`
- `README.md`

## Validação histórica da refatoração (15/11)

Os itens abaixo são o registro da entrega anterior, não uma nova execução de
cada commit durante a revisão de 20/11. O resultado atual está mais adiante.

- Cada um dos 11 commits foi extraído para uma pasta temporária e passou em
  `manage.py check`, usando o conteúdo daquele commit, não os arquivos finais
  ainda presentes no workspace.
- `git diff --cached --check` foi executado antes de cada commit.
- No estado final, `manage.py check` e `node --check home/static/home/crud.js`
  passaram; o Git não apresentou alterações pendentes.
- `git ls-files docs` não retornou arquivos e `git check-ignore` confirmou a
  exclusão da documentação local.
- A suíte completa da implementação já havia passado com 46 testes, incluindo
  Chrome e PostgreSQL. Ela não foi repetida apenas para reorganizar os commits;
  nesta etapa só houve ajuste de documentação, exclusões e espaços em branco.

## Integração da refatoração — 14543ac

O histórico compartilhado registra o PR #1 como merge de `70b1cb9` em
`14543ac`, com pais `74e3114` e `70b1cb9`. Portanto, revisar/integrar essa série
não é mais uma pendência. A classificação e migração de dados legados continuam
em B06, sem impedir o registro da integração já realizada.

## Autenticação inicial — 39d076d

Mensagem original: `Alteracoes autenticacao`, em 20/11/2026.

- Configura apps, middleware, backend e URLs do django-allauth no pacote ativo.
- Define login por username/e-mail, cadastro com e-mail único, confirmação
  obrigatória no fluxo allauth e backend de e-mail no console.
- Cria o app `usuarios`, painel de identidade/papéis e as primeiras rotas
  `/api/usuarios/me/` e `/api/usuarios/monografias/`.
- Resolve papéis usando grupos e vínculos a Aluno, Professor e coordenação de
  Curso; staff é tratado como Administrador.
- Adiciona permissões de papel e três testes de autenticação/visibilidade.
- Mantém o login administrativo em `/entrar/`, com destino explícito para
  `/monografias/` quando não há `next` válido.
- Também altera o pacote antigo `cursodjango`; essas alterações não tornam esse
  pacote a configuração usada por `manage.py`.

Principais arquivos: `Curso_Django/settings.py`, `Curso_Django/urls.py`,
`usuarios/roles.py`, `permissions.py`, `api.py`, `api_urls.py`, `views.py`,
`urls.py`, `templates/usuarios/painel.html` e `tests.py`. O app possui
`migrations/__init__.py`, mas não introduz models/tabelas próprios.

## Rascunhos, convites e auditoria — fda173a

Mensagem original: `finalizando autenticacao`, em 20/11/2026.
A comparação principal desta revisão foi `14543ac..9d04dc0`, abrangendo os
dois commits de autenticação (31 arquivos alterados no conjunto).

| Área | Implementação efetiva |
| --- | --- |
| Configuração | `python-dotenv`, `.env.example`, chave/senha por ambiente, debug/hosts configuráveis e flags de cookies/HTTPS condicionadas a DEBUG |
| Dependências | Inclui `django-allauth==65.22.1` e `python-dotenv>=1.0,<2` em `requirements.txt` |
| Grupos | Comando idempotente `configurar_grupos` cria Alunos, Professores e Coordenadores sem atribuição automática |
| Consulta acadêmica | Reúne monografias por autoria, orientação/coorientação e coordenação; staff vê todos |
| Autorização | Classes de permissão por dono/orientador/coordenador/avaliador; somente parte já aplicada aos endpoints existentes |
| Rascunhos do aluno | Rotas próprias para GET/POST/PATCH/DELETE, dono/curso definidos no servidor, alteração/exclusão limitada a RASCUNHO |
| Convites externos | Emissão por staff ou coordenação do curso; confirmação sem conta com token escopado, hash, prazo, transação e bloqueio da participação |
| Auditoria | Eventos de login/logout, CRUD REST e POST HTML, rascunhos e convites em HistoricoAcao |
| Testes | Dez novos casos em `usuarios/tests_security.py`, além dos três do commit anterior |
| Artefatos | Acrescenta backlog na raiz, patch de segurança e script de conversão de settings antigos |

Os principais arquivos são `usuarios/api.py`, `api_urls.py`, `permissions.py`,
`convites.py`, `auditoria.py`, `signals.py`, `apps.py`,
`management/commands/configurar_grupos.py`, `tests_security.py`,
`Curso_Django/api.py`, `Curso_Django/interface.py`, `Curso_Django/settings.py`,
`requirements.txt` e `.env.example`.

Não foram criadas novas migrações de domínio nesse commit. O allauth traz
migrações da dependência, aplicadas pelo `manage.py migrate`. O comando de
grupos é separado e não substitui cadastro/vínculo de contas.

O arquivo `PENDENCIAS.md` adicionado nesse commit ainda repetia o estado
anterior da refatoração; esta revisão atualiza os recursos que já chegaram.
O nome do commit não significa que todo B04 ou os processos B09–B15 estejam
concluídos.

## Integração da autenticação — 9d04dc0

O PR #2 mescla `feature/autenticacao` em `main`, com pais `14543ac` e
`fda173a`. A referência local `origin/main` também aponta para `9d04dc0` nesta
revisão. Não há necessidade de integrar novamente as duas features descritas.

## Diagnóstico histórico no commit 9d04dc0

- A emissão do convite exige aprovação de orientação, mas a ação que registra
  essa aprovação ainda não existe; o teste configura o status diretamente.
- O cadastro administrativo de banca/avaliação não exige todas as guardas
  acadêmicas do plano. Criar campos de estado ou classes de permissão não
  implementa a sequência de submissão, defesa e publicação.
- O painel acadêmico mostra identidade e papéis; a interface dos novos
  rascunhos/convites e dos demais processos está pendente.
- Login allauth convive com login legado, admin e Basic Auth. A política de
  e-mail/contas deve ser consolidada e testada entre esses acessos.
- IP/VPN aparece em `seguranca_monografias.patch`, mas
  `usuarios/middleware.py` não existe na aplicação e não está configurado.
  O script de conversão também menciona esse módulo. O patch é uma proposta,
  não evidência de proteção instalada; não integra o procedimento atual de setup.
- A auditoria já recebe eventos, mas falta acesso ao histórico, retenção e
  cobertura dos caminhos que não passam pelos helpers HTTP.

Essas diferenças estão refletidas nas linhas B02/B04/B07/B09–B15 do backlog.

## Validação anterior — 20/11/2026, código 9d04dc0

Ambiente: Python 3.12.3, Django 6.0.4, PostgreSQL 16, dependências instaladas e
`.env` local preenchido. A instância local foi preparada com o script do
projeto, incluindo o banco isolado `test_curso_django_dev`.

| Comando | Resultado observado |
| --- | --- |
| `env/bin/python scripts/postgres_local.py start --test-database` | Banco de testes preparado |
| `env/bin/python manage.py check` | Sem problemas |
| `env/bin/python manage.py makemigrations --check --dry-run` | No changes detected |
| `env/bin/python manage.py test --keepdb --noinput` | 59 testes descobertos; 57 aprovados; 2 ignorados; nenhum erro/falha |

A suíte concluiu em aproximadamente 21 segundos. Os dois testes ignorados são
de `home/test_browser.py`, pois `RUN_BROWSER_TESTS=1` não foi ativado. A
contagem anterior de 46 pertence à refatoração: os 13 testes adicionados em
`usuarios` elevaram o total para 59. Não foi repetida a execução no navegador
nesta revisão documental.

A restrição de conexão do sandbox exigiu executar a preparação do banco, a
suíte e a verificação do histórico de migrações com acesso local autorizado.
Os erros de conexão dessa primeira tentativa não são falhas dos testes da
aplicação. Os resultados acima são os das execuções com acesso ao PostgreSQL.

Os casos atuais não comprovam cadastro/confirmação/recuperação de senha allauth
ponta a ponta, toda a matriz de professor/coordenador, concorrência ou o fluxo
acadêmico completo. A cobertura necessária está em `PENDENCIAS.md`.

## Ajustes anteriores de ambiente e documentação após o PR #2

Foi configurado um `.env` local com chave própria e a senha do banco existente;
valores não são registrados aqui nem no Git. A ausência das dependências novas
e das variáveis explica os erros iniciais de inicialização após o pull. Esse
ajuste local não é um commit da feature.

Nesta revisão foram atualizados README, contratos da API, guia de
desenvolvimento, histórico e ambas as cópias do backlog. O PDF continua como
baseline de 11/11. Nenhum código de negócio ou migration foi alterado por esta
atualização documental.

## Comandos de consulta

```bash
git log --oneline --graph --all -20
git log --reverse --oneline 14543ac..9d04dc0
git show --stat 39d076d fda173a
git diff --stat 14543ac..9d04dc0
git branch -avv
git status --short
git ls-files docs
```

O último comando não lista arquivos: `docs/` continua local. Os documentos
canônicos agora ficam na raiz, sem cópias numeradas.

## PR #3 — 0178003 / 5f7857b

A equipe tornou `ACCOUNT_EMAIL_VERIFICATION` opcional e adicionou documentos
na raiz. O backlog recebido em `docs/PENDENCIAS_ATUALIZADO.md` foi lido antes
da implementação dos painéis. Sua proposta de não criar novas telas foi
substituída pela solicitação atual do usuário. Foram mantidas as decisões de
e-mail opcional, retirada de IP/VPN e integração do microserviço ainda pendente.

## Entrega dos perfis e limpeza — 20/11/2026

- Quatro painéis responsivos, navegação por múltiplos papéis, conta sem vínculo,
  busca, filtro de estado, paginação, métricas e próximas bancas por escopo.
- Detalhe de trabalho com autorização; gestão do próprio rascunho por API/HTML.
- Emissão e aceite de convite externo com as mesmas regras existentes na API,
  sem token na URL, sem cache e com proteção CSRF no HTML.
- Consultas em `usuarios/consultas.py` e escritas em `usuarios/services.py`,
  compartilhadas por HTML/API. Auditoria transacional e tradução de conflitos
  dos rascunhos preservadas, com testes de rollback.
- Navbar com painel/logout para não staff, entrada acadêmica pela home e
  preservação do login/CRUD administrativo.
- Remoção de `cursodjango` (cinco fontes), `scripts/proteger_settings.py`,
  `seguranca_monografias.patch`, `requeriments.txt`, esqueletos vazios
  `home/{admin,models,tests}.py` e `usuarios/{admin,models}.py`.
- Consolidação e remoção de `COMMITS (1).md`, `CRUD (1).md`,
  `DESENVOLVIMENTO (1).md`, `PENDENCIAS (1).md` e `PENDENCIAS (2).md`.
- Backup `db.sqlite3.backup` preservado localmente e retirado do rastreamento.
  Migrações, Equipe, banco PostgreSQL, `.env`, PDF do plano, Planta baixa.pdf
  e documento de rotas recebidos foram preservados.
- Backlog B01–B17 consolidado com as observações do microserviço recebido,
  distinguindo código local validado de relato externo não executado.

### Evidências desta entrega

| Verificação | Resultado |
| --- | --- |
| `manage.py check` | Sem problemas |
| `manage.py makemigrations --check --dry-run` | Sem alterações |
| Testes acadêmicos direcionados | 30 aprovados |
| Novos cenários de navegador | 2 aprovados |
| `RUN_BROWSER_TESTS=1 manage.py test --keepdb --noinput` | **78 aprovados, sem falhas ou testes ignorados**, incluindo quatro cenários Chrome |

A suíte completa levou aproximadamente 49 segundos, em PostgreSQL isolado.
São 59 testes anteriores e 19 novos (17 de interface/segurança, dois de
navegador). Foram verificadas capturas dos perfis em desktop e celular,
geradas em `/tmp/perfis-monografias`; não foram incluídas no Git.
O microserviço, Redis e RabbitMQ não foram executados nem integrados.

## Correção de login e perfis na API — 20/11/2026

Revisão sobre `738df0c`. O login `/entrar/` rejeitava não staff, o índice da
API herdava a restrição administrativa e Basic tinha precedência sobre a
sessão. Os testes reproduziram identidade do admin substituindo a de um aluno
e Basic retido permitindo acesso após logout do navegador.

- `/accounts/login/`, `/entrar/` e `/api-auth/login/` compartilham allauth,
  usuário/e-mail, template do projeto e destino padrão no painel. `next`
  preserva destinos locais, incluindo `/api/`, e rejeita destinos externos.
- Saída pelo sistema/API usa POST com CSRF e retorna à tela de login.
  `/accounts/logout/` preserva a confirmação por GET sem encerrar a sessão.
- A API navegável vincula login, painel e logout. Sua raiz apresenta identidade,
  papéis e links autorizados; conta sem vínculo acessa a própria identidade.
- A sessão tem prioridade; Basic retido no navegador é ignorado. Clientes
  sem sessão continuam usando Basic. Escritas por sessão exigem CSRF mesmo
  na presença de um cabeçalho Basic válido.
- A restrição administrativa fica explícita em `CRUDViewSet`; páginas de
  gestão retornam 403 para autenticados sem staff, evitando ciclos de login.
- Removidos o formulário e o template exclusivos do login administrativo.
  README, contratos, guia de desenvolvimento e B04 foram atualizados.

Validação: `manage.py check` sem problemas e **89 testes aprovados** com
PostgreSQL e Chrome, sem testes ignorados. São dez regressões de autenticação
e um novo cenário de navegador, além dos 78 anteriores. O fluxo Chrome troca
admin → aluno → professor sem limpar cookies, mantém Basic antigo apenas nas
requisições ao servidor de teste e verifica a identidade efetiva da API.
Capturas de login em desktop/celular foram verificadas em `/tmp/login-api`.
O limite de tentativas foi isolado somente na matriz de testes; permanece
ativo na aplicação e nos cenários Chrome. Não houve mudança de modelos ou
migrações, nem integração JWT com o microserviço.

## Cadastro público — 20/11/2026

Revisão de `/accounts/signup/`, sobre as correções locais de login. A
investigação confirmou que a identidade do cadastro é `auth.User`, a mesma
do CRUD nativo em `/admin/auth/user/`. A tela ainda usava o template padrão
do allauth, sem integração visual com o projeto.

- Template próprio com layout responsivo, link de login, POST/CSRF, instruções
  de senha e erros gerais/por campo. Usuário/e-mail são preservados quando
  há erros; senhas não são reexibidas.
- `CadastroContaForm` configurado em `ACCOUNT_FORMS`, preservando as validações
  do allauth e salvando usuário, e-mail e auditoria `USUARIO_CRIADO` na mesma
  transação. Não há nova tabela de identidade nem privilégios no cadastro público.
- Confirmação explícita de conta salva após `user_signed_up` e acesso ao painel.
- Oito testes verificam conta/e-mail/senha persistidos, login posterior,
  listagem administrativa, duplicados, senha inválida, CSRF, rollback,
  privilégios e redirecionamento externo.
- Novo fluxo Chrome abre cadastro pelo login, corrige senha divergente,
  salva, sai, entra com e-mail e consulta a conta na administração. Capturas
  desktop/celular foram verificadas em `/tmp/cadastro-usuarios`.

Validação: `check` e `git diff --check` sem problemas. A suíte agora tem 98
casos; os 89 anteriores passaram na execução completa. Os oito novos testes
e o cenário Chrome passaram juntos na reexecução direcionada final (**9/9**),
após ajustar a senha de teste e o seletor do link administrativo com filtros.
GET no servidor local da porta 8000 retornou 200 com o novo formulário/CSS.
Os usuários de teste foram criados somente no banco de testes; nenhuma conta
de demonstração foi inserida no banco da aplicação. Provisionamento de
Aluno/Professor, recuperação completa de senha e JWT continuam pendentes.
Os cenários de convite preparam a aprovação como fixture, sem afirmar que
existe uma ação de aprovação no principal.

### Commits da entrega e integração

| Commit | Responsabilidade |
| --- | --- |
| `4515604` | Painéis, consultas/serviços compartilhados, rascunhos, convites e 19 testes novos |
| `ba8c71e` | Remoção do legado/duplicatas e backup fora do rastreamento |

A documentação consolidada é registrada em um terceiro commit separado.
A branch de trabalho é `feature/telas-perfis-academicos`, criada a partir de
`5f7857b`. `git fetch origin` confirmou que não havia novos commits em
`origin/main` além dessa base. A integração em `main` usa merge com registro
próprio (`--no-ff`), preservando os commits da entrega. O hash do merge pode
ser consultado com `git log --first-parent --oneline main -1`.

O merge é local; não foi solicitado push para o remoto. `.env`, backup SQLite,
PostgreSQL, uploads e as cópias em docs/ continuam fora do versionamento.

## Perfis conforme o enunciado anexado — 20/11/2026

Revisão local após leitura de `Trabalho_SistemasDistribuidos_Monografias (1) (2).md`.
A comparação completa está em [ESCOPO_E_ACESSOS.md](ESCOPO_E_ACESSOS.md).
Esta revisão integra a consolidação de cadastro, login e acesso por perfil
registrada ao final deste documento.

- Corrigida a promoção implícita de qualquer staff para Administrador. O papel
  administrativo exige superusuário ou grupo `Administradores`; os papéis
  acadêmicos são definidos pelos vínculos, sem depender dos grupos antigos.
- A mesma regra protege os oito CRUDs, páginas, menus, raiz da API e admin
  Django. Este último mantém staff/permissões de model e rejeita login de
  staff sem papel administrativo. Vínculos coexistentes não são ocultados.
- Formulários administrativos de aluno/professor oferecem Conta de acesso;
  detalhes mostram o usuário vinculado. Salvar o vínculo libera o perfil na
  próxima requisição; remover/trocar o vínculo revoga o acesso correspondente.
- Painel docente com orientações/coorientações, filtro de vínculo e próprias
  participações em bancas não canceladas. Detalhes com perfil explícito
  respeitam esse escopo. O orientador principal também pode emitir convites
  externos elegíveis; coorientador/avaliador não recebe essa autorização.
- A conta local identificada pelo responsável foi vinculada ao aluno e curso
  informados, com a matrícula fornecida. A marcação staff foi removida e a
  manutenção foi registrada em `HistoricoAcao`, sem alterar os demais cadastros.
- README, contratos, desenvolvimento e pendências reconciliados com o enunciado.
  Permanecem pendentes os processos de submissão/aprovação, agenda validada,
  avaliação própria, publicação/catálogo e integração distribuída. IP/VPN e
  indicadores exigidos pelo enunciado voltam a aparecer explicitamente no backlog.

Validação: **110 testes aprovados**, sem falhas ou casos ignorados, incluindo
seis cenários Chrome e doze testes novos em `usuarios/test_papeis.py`.
O cenário de cadastro também cria o vínculo de Professor pelo formulário/API,
faz logout/login e verifica painel docente e bloqueio administrativo. A troca
de contas usa professor staff para reproduzir a causa original. Capturas de
desktop/celular inspecionadas em `/tmp/perfis-escopo`. `manage.py check`,
`makemigrations --check --dry-run` e `git diff --check` passaram; nenhum model
ou schema foi alterado. Testes executados somente no banco isolado.


## Consolidação das atualizações — 20/11/2026

Commit identificado pela mensagem:
`fix(usuarios): corrigir cadastro, login e acesso por perfil`.

Reúne as correções locais de login/API, cadastro público, vínculos e separação
de perfis, formulários/telas, regressões automatizadas e documentação descritas
nas revisões anteriores. Inclui o enunciado anexado e a comparação de acessos.

O `PENDENCIAS.md` foi conferido novamente contra o enunciado e o código e
organizado em 13 áreas, com tarefas abertas, prioridades, dependências,
critérios de aceite e ordem de entrega. Destaca as restrições ainda ausentes
nos CRUDs de banca/avaliação e nos caminhos do admin, além das pendências de
PDF, processos acadêmicos, catálogo, indicadores, Redis/filas, auditoria,
integração e testes de carga. As entregas existentes permanecem separadas do
trabalho restante; o relatório externo continua identificado como evidência
recebida, sem execução comprovada.

Validação de referência: 110 testes aprovados na revisão de perfis, incluindo
seis cenários Chrome, mais `check` e verificação de migrações sem alterações.
A revisão final é documental e foi conferida com `git diff --check`; não houve
nova alteração funcional que exigisse repetir a suíte. As cópias locais de
pendências e histórico em `docs/` foram sincronizadas com os documentos da raiz.


## Merge do PR #4 na main local — 21/11/2026

`origin/main` avançou para `3448d33` (PR #4), com o emissor JWT de `b019850`.
O merge local preserva `c7230af` (cadastro, login, perfis e documentação) e
os commits remotos. O Git aplicou a união sem conflitos textuais; foi feita
uma revisão de compatibilidade para manter os papéis atuais no novo emissor.

O endpoint `POST /api/usuarios/token-microservico/` exige sessão/CSRF,
seleciona um dos papéis autorizados pelos vínculos e emite token de dez minutos
com chave `MICROSERVICO_JWT_SIGNING_KEY` configurada. Sem chave válida, retorna
503 apenas nessa rota. `requirements.txt` inclui SimpleJWT; `.env.example`
mostra a variável necessária. Cinco testes novos verificam assinatura/claims,
professor staff sem papel admin, revogação da coordenação, ausência de chave
e CSRF. A validação do consumo pelo microserviço continua pendente.

Suíte completa após o merge: **115 testes aprovados**, incluindo seis cenários
Chrome. `manage.py check` passou. Os arquivos de documentação foram alinhados
com a nova rota; a chave JWT real não foi adicionada ao repositório.
