# Registro dos commits da entrega

Registro local, excluído do Git junto com a pasta `docs/`, conforme solicitado.

## Branches e escopo

- Ponto de partida da entrega: `main`, em `abf487f`.
- Integração criada: `develop`, também em `abf487f`.
- Branch de implementação: `feature/refatoracao-crud-monografias`.
- Entrega: 11 commits, de `00ff6c8` a `70b1cb9`.
- Gitflow organiza as branches; Conventional Commits organiza as mensagens.
- Os commits são locais. A integração posterior em main está registrada abaixo; não foi feito push.
- `docs/`, ambiente virtual, dados PostgreSQL e uploads não foram incluídos.
- O PDF do plano está na raiz e foi versionado com o README.

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

## Sequência

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

## Validação

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

## Consulta e integração futura

Para consultar os commits e seus detalhes:

```bash
git log --oneline --reverse develop..feature/refatoracao-crud-monografias
git show --stat 70b1cb9
git status --short
git ls-files docs
```

As regras acadêmicas pendentes continuam listadas em `PENDENCIAS.md`.

## Integração posterior em main

A pedido do usuário, a feature foi mesclada diretamente em `main` com
`git merge --ff-only feature/refatoracao-crud-monografias`.

- `main` e `feature/refatoracao-crud-monografias` apontam para
  `70b1cb9af3b3ce7faadb22c13e91a978b5dc38c6` e possuem conteúdo e histórico iguais.
- A branch ativa passou a ser `main`; o workspace permanece limpo.
- `develop` continua no ponto inicial `abf487f`.
- Não houve conflitos, novo commit de merge, mudança de código ou push.
- `docs/` permanece local e ignorada pelo Git.
