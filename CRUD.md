# CRUD administrativo e API acadêmica

Revisado em **20/11/2026**, após `5f7857b` e a entrega dos painéis por perfil. Este documento descreve as rotas implementadas; as ações
ainda propostas no PDF são acompanhadas em [backlog geral](docs/PENDENCIAS_SISTEMA_MONOGRAFIAS_22-11-2026.md).

Esta entrega implementa a modelagem e o CRUD básico das seções 3 e 4 do
`Plano_Refatoracao_CRUD_API_Monografias.pdf`. O padrão original foi mantido:
classes `models.Model`, campos explícitos e relações no ORM, nos apps `equipe`
e `monografias`; as telas existentes continuam usando `ModelForm` e funções
de view. A API usa serializers, ModelViewSets e router do Django REST Framework.

## Modelos

| App | Modelos |
| --- | --- |
| `equipe` | `Aluno`, `Professor`, `Curso` |
| `monografias` | `Monografia`, `Banca`, `Avaliacao`, `ParticipacaoBanca`, `MembroExterno`, `DocumentoComplementar`, `HistoricoAcao` |

`auth.User` continua sendo a identidade de autenticação. Aluno e Professor
possuem vínculo opcional com uma conta existente; o CRUD não cria contas nem
altera senhas. Um aluno pode ter várias monografias. Os vínculos acadêmicos
usam `PROTECT`; a exclusão de dependências retorna erro, sem apagar os trabalhos.

`Equipe` foi desativada como cadastro de negócio. Sua tabela antiga fica
preservada temporariamente para os integrantes que ainda precisam ser
classificados como aluno ou professor; não há CRUD novo sobre essa tabela.
Formação acadêmica sozinha não determina o papel de uma pessoa.

## Autenticação e separação de acessos

A raiz `/api/` aceita qualquer conta autenticada e retorna `papeis`, o link
`me` e recursos autorizados: `minhas-monografias` para perfis acadêmicos/admin,
`meus-rascunhos` para Aluno e as oito coleções para Administrador. Uma conta
sem vínculo recebe `papeis: []` e acesso à própria identidade.
Os oito CRUDs exigem conta ativa com papel Administrador (superusuário ou grupo `Administradores`); a API acadêmica usa
`/api/usuarios/`. Usuários sem permissão recebem 403.
Sem autenticação, clientes JSON recebem 401 com desafio Basic; navegação HTML,
Fetch Metadata e `X-Requested-With: XMLHttpRequest` recebem 403 sem diálogo
nativo de credenciais. Essas requisições de navegador ignoram Basic retido.
As rotas acadêmicas têm permissões próprias: identidade para autenticados,
listagem por papel/vínculo, rascunhos do aluno dono e convites com escopo de
participação. Isso não concede acesso acadêmico aos CRUDs administrativos.

Crie uma conta administrativa local:

```bash
env/bin/python manage.py createsuperuser
```

No navegador, entre em `/accounts/login/` e abra o painel ou `/api/`.
`/entrar/` e `/api-auth/login/` usam o mesmo formulário e aceitam todos os perfis.
O campo de identificação do formulário é `login` (usuário ou e-mail).
No Postman, selecione Basic Auth e use sua conta Django sem cookie de sessão.
A senha do PostgreSQL não é uma conta de acesso à API. Uma sessão presente
tem prioridade sobre Basic e exige CSRF nas escritas.

O fluxo django-allauth está em `/accounts/signup/`, `/accounts/login/` e
`/accounts/logout/`, com login por usuário/e-mail e confirmação de e-mail
opcional desde `0178003`. O e-mail é impresso no terminal pelo backend de
console. Após login, o destino padrão é `/usuarios/painel/`, que mostra os
painéis de Aluno, Professor, Coordenador ou Administrador. Um `next` local
válido preserva o destino solicitado. `/sair/`, `/accounts/logout/` e
`/api-auth/logout/` encerram a sessão por POST/CSRF e retornam à tela de login;
GET em `/accounts/logout/` apenas mostra uma confirmação. A API navegável
oferece links para login, painel e saída, compartilhando a sessão do sistema.
`/admin/` mantém o login próprio do Django para contas administrativas.

`configurar_grupos` cria os três grupos acadêmicos e `Administradores`, sem
atribuir usuários. Aluno/Professor são identificados pelos vínculos
`Aluno.usuario`/`Professor.usuario`; coordenação exige `Curso.coordenador`
apontando para o professor da conta. Não é preciso adicionar grupo acadêmico.
Administrador exige superusuário ou grupo `Administradores`; `is_staff` não
concede esse papel. Papéis podem coexistir. Cadastrar conta no allauth não
cria vínculos: a administração os seleciona no campo **Conta de acesso** dos
formulários de aluno/professor ou no campo `usuario` dos respectivos CRUDs.
A conta aparece como `usuario_nome` (somente leitura) nos detalhes.

O formulário público em `/accounts/signup/` cria a identidade `auth.User`
usada também pela API e pelo CRUD nativo de usuários (`/admin/auth/user/`).
Recebe `username`, `email`, `password1` e `password2` via POST com CSRF. Erros
de validação voltam à tela com os campos indicados; o sucesso direciona ao
painel com uma confirmação. Conta, e-mail e evento `USUARIO_CRIADO` são salvos
na mesma transação. O formulário não grava uma segunda identidade em Aluno
ou Professor nem permite atribuir privilégios.

## Rotas administrativas

| Entidade | Coleção |
| --- | --- |
| Aluno | `/api/alunos/` |
| Professor | `/api/professores/` |
| Curso | `/api/cursos/` |
| Monografia | `/api/monografias/` |
| Banca | `/api/bancas/` |
| Avaliação | `/api/avaliacoes/` |
| Membro externo (apoio) | `/api/membros-externos/` |
| Participação em banca (apoio) | `/api/participacoes-banca/` |

Todas as coleções oferecem `GET` para listar e consultar `{id}/`. Somente alunos,
professores, cursos e membros externos oferecem `POST`, `PUT`, `PATCH` e `DELETE`
administrativos. Monografias, bancas, participações e avaliações retornam **403**
para escritas genéricas; use as ações acadêmicas abaixo. Acesso administrativo
também exige a rede configurada em `ADMIN_ALLOWED_NETWORKS`.

Respostas: 201 ao criar, 200 ao consultar/editar, 204 ao excluir, 400 para dados
inválidos, 401/403 para acesso negado, 404 para ID inexistente e 409 para exclusão
protegida ou conflito de estado. Erros de validação são associados aos campos.

As listas possuem paginação de 20 registros e retornam `count`, `next`,
`previous` e `results`. Use `?page=2`, `?search=texto` e `?ordering=nome`.
Os campos de ordenação dependem do recurso: nome/matrícula/código nos cadastros,
título/data de publicação nas monografias, início/fim nas bancas e nota/data de
registro nas avaliações. Os nomes dos parâmetros são os campos sem acentos,
por exemplo `?ordering=-data_publicacao`.

As respostas também incluem campos de exibição somente leitura:
`usuario_nome`, `curso_nome`, `coordenador_nome`, `aluno_nome`, `orientador_nome`,
`coorientador_nome`, `monografia_titulo`, `participante_nome` e descrições
de status, modalidade, papel e recomendação, conforme o recurso. Os IDs
originais continuam sendo os campos usados para escrita. Não reenvie o objeto
inteiro retornado pelo GET em um PUT/PATCH; envie apenas campos editáveis.

## Exemplo de sequência de cadastro

Envie os objetos seguintes como JSON nas respectivas coleções. Substitua os
IDs pelos retornados nas respostas; eles não precisam começar em 1.

Professor:

```json
{"nome":"Ana Silva","email":"ana@example.com","departamento":"Computação","area_pesquisa":"Sistemas distribuídos"}
```

Curso:

```json
{"nome":"Ciência da Computação","codigo":"CC","coordenador":1}
```

Aluno:

```json
{"nome":"João Souza","matricula":"2026001","email":"joao@example.com","curso":1,"orientador_atual":1}
```

Rascunho, como aluno vinculado, em `POST /api/usuarios/rascunhos/`:

```json
{"titulo":"API de monografias","resumo":"Descrição do trabalho","palavras_chave":["Django","TCC"],"orientador":1}
```

Proposta, após aprovação, em `POST /api/usuarios/monografias/1/propor-banca/`:

```json
{"inicio":"2026-12-10T14:00:00-03:00","fim":"2026-12-10T15:00:00-03:00","modalidade":"PRESENCIAL","local":"Sala 10"}
```

Participação, como responsável, em `POST /api/usuarios/bancas/1/participantes/`:

```json
{"professor":1,"papel":"AVALIADOR"}
```

Para avaliador externo, cadastre nome, email e instituição em
`/api/membros-externos/`, e use `membro_externo` na participação, em vez de
`professor`. Cada participação deve ter exatamente um desses dois vínculos.

Avaliação do próprio professor, depois da defesa, em `POST /api/usuarios/participacoes/1/avaliacao/`:

```json
{"nota":"8.50","parecer":"Trabalho adequado.","recomendacao":"APROVADA"}
```

A nota usa escala de 0 a 10, com duas casas decimais. B11 calcula média simples,
exige todas as avaliações titulares e usa mínimo 6,00. Após fechamento, notas
e pareceres não podem ser alterados.
As recomendações aceitas são `APROVADA`, `APROVADA_COM_RESSALVAS` e `REPROVADA`.

## API acadêmica: identidade e monografias

Estas rotas são registradas em `usuarios/api_urls.py`; não aparecem na lista
automática de recursos do router em `/api/`.

| Método e rota | Permissão e contrato |
| --- | --- |
| `GET /api/usuarios/me/` | Conta autenticada; retorna `id`, `username`, `email` e `papeis`, inclusive lista vazia para conta sem papel |
| `GET /api/usuarios/monografias/` | Papel acadêmico válido ou Administrador; resumo paginado com `id`, `titulo`, `status_fluxo` |
| `GET /api/usuarios/rascunhos/` | Papel Aluno; lista paginada de todos os trabalhos próprios, inclusive fora de RASCUNHO |
| `POST /api/usuarios/rascunhos/` | Papel Aluno; cria RASCUNHO com aluno e curso obtidos no servidor |
| `GET /api/usuarios/rascunhos/{id}/` | Papel Aluno e trabalho próprio, em qualquer estado |
| `PATCH /api/usuarios/rascunhos/{id}/` | Aluno dono e estado RASCUNHO; resposta 200 |
| `DELETE /api/usuarios/rascunhos/{id}/` | Aluno dono, estado RASCUNHO e sem vínculo protegido; resposta 204 |

A listagem de resumos reúne os escopos dos papéis: aluno vê os próprios
trabalhos; professor vê orientações, coorientações e trabalhos de bancas não canceladas em que participa; coordenador vê trabalhos
dos cursos que coordena; Administrador vê todos. Conta sem papel válido recebe 403.
Essa listagem não é o catálogo público. Busca e ordenação específicas não
foram configuradas nas views acadêmicas; não presumir o contrato de filtros
dos CRUDs administrativos.

No CRUD acadêmico, o queryset contém apenas trabalhos do próprio aluno: um ID
de outro aluno retorna 404. Administrador só usa essa rota quando também tem vínculo de Aluno; a gestão
geral usa o CRUD administrativo. `PUT` não foi disponibilizado.
Leitura não depende do estado, mas alteração/exclusão fora de RASCUNHO retorna
409. `AJUSTES_SOLICITADOS` ainda não reabre edição.

Exemplo de criação pelo aluno autenticado:

```http
POST /api/usuarios/rascunhos/
Content-Type: application/json
```

```json
{"titulo":"Meu TCC","resumo":"Descrição do estudo","palavras_chave":["Django"],"orientador":1}
```

Envie somente título, resumo, palavras-chave, orientador e coorientador
opcional. `aluno`, `curso`, status, datas, hash e campos de exibição são de
leitura; enviá-los no JSON retorna 400, inclusive se corresponderem ao próprio
usuário. O cadastro de Aluno deve ter curso. A resposta 201 usa o contrato de
Monografia, com IDs e nomes para exibição. O orientador é validado como
Professor e deve ser diferente do coorientador; não existe ainda uma regra de
aprovação da escolha de orientação ou de elegibilidade por curso.

Os serviços em `usuarios/services.py` verificam o papel, definem aluno/curso,
bloqueiam o trabalho ao alterar/excluir e registram auditoria na mesma transação.
São usados pelo serializer da API e pelo POST HTML. `RascunhoAlunoViewSet`
herda de `CRUDViewSet` e reutiliza a tradução de conflitos de integridade/estado;
o evento registrado é o acadêmico, sem duplicar `CRUD_*`.

## Token para o microserviço

`POST /api/usuarios/token-microservico/` exige sessão do sistema e CSRF.
O corpo pode informar `role=aluno|orientador|coordenador|admin` quando a conta
possui vários papéis. A autorização usa os vínculos atuais; `is_staff` sozinho
não libera `admin`. A resposta 200 inclui `access` (Bearer), `token_type`,
`role` e `expires_in=600`; tem `Cache-Control: no-store`. Sem chave
`MICROSERVICO_JWT_SIGNING_KEY` de pelo menos 32 caracteres, retorna 503.
O token leva IDs/vínculos do papel selecionado. Essa rota é o emissor do
sistema principal, mas a verificação/revogação no serviço separado e o fluxo
integrado ainda precisam de teste entre os serviços. O JWT não substitui a
sessão/CSRF do CRUD principal.

## Convite de membro externo

O identificador das rotas abaixo é de **ParticipacaoBanca**, não de Banca.

### Emitir

```http
POST /api/usuarios/convites/{participacao_id}/emitir/
```

Não exige campos no corpo. Exige autenticação e uma das autorizações:
Administrador, orientador principal da monografia ou coordenador do curso.
Coorientador ou avaliador sem um desses vínculos não pode emitir o convite.
A participação precisa ser externa, estar `CONVIDADO`, pertencer a banca
`AGENDADA` e a monografia em `APROVADA_ORIENTADOR` ou `BANCA_AGENDADA`.
Participação inexistente retorna 404; ator sem permissão, 403; pré-condições
de negócio inválidas, 400. O sucesso retorna 200:

```json
{"token":"<segredo retornado nesta emissão>","expira_em":"<data e hora em ISO 8601>"}
```

O token é gerado com `secrets.token_urlsafe(32)`; somente seu SHA-256 é
persistido. A expiração considera o maior entre sete dias após a emissão e
dois dias após o fim da banca, limitada a 90 dias após a emissão. Reemitir
para uma participação ainda convidada substitui o hash e invalida o token
anterior. O token em claro não pode ser recuperado por GET e não integra
serializers de listagem, histórico ou logs da aplicação.

### Confirmar

```http
POST /api/usuarios/convites/{participacao_id}/confirmar/
Content-Type: application/json
```

```json
{"token":"<segredo recebido>"}
```

Essa view não usa autenticação de sessão/Basic: a autorização depende do
token da participação. Exige participação externa ainda `CONVIDADO`, banca
`AGENDADA` e token válido, não expirado. A comparação de hash usa
`hmac.compare_digest`. Token ausente, inválido, expirado ou convite já aceito
retorna 403; ID inexistente retorna 404. Sucesso retorna 200:

```json
{"confirmado":true}
```

Grava `CONFIRMADO` e `confirmado_em`. Emissão e confirmação usam transação e
bloqueio da participação e registram histórico; a confirmação externa grava
`ator=None` e o ID da participação. O token autoriza somente essa confirmação,
sem acesso geral à conta, documentos ou avaliações.

Há telas de emissão e aceite; ainda não há envio automático de convite por
e-mail, recusa, confirmação interna, disponibilidade/quórum ou integração com
reagendamento. A aplicação também não implementa a aprovação de orientação
necessária para liberar a emissão. Os testes montam esse estado diretamente
no ORM; não representam o processo acadêmico completo.

## Auditoria implementada

| Origem | Eventos em HistoricoAcao |
| --- | --- |
| Sinais Django de autenticação | `LOGIN`, `LOGOUT` |
| CRUD REST e POST HTML pelos helpers compartilhados | `CRUD_CRIACAO`, `CRUD_ATUALIZACAO`, `CRUD_EXCLUSAO` |
| CRUD acadêmico do aluno | `RASCUNHO_CRIADO`, `RASCUNHO_ALTERADO`, `RASCUNHO_EXCLUIDO` |
| Convite externo | `CONVITE_EXTERNO_EMITIDO`, `CONVITE_EXTERNO_CONFIRMADO` |

O model guarda ator, referência textual do objeto, ação, data/hora e detalhes.
Os helpers guardam modelo/ID, e os serviços acadêmicos guardam o ID relevante;
não há diff completo dos campos. Escrita e evento de CRUD/convite usam a mesma
transação. Login/logout são auditados via sinais, não por uma auditoria genérica
de toda autenticação HTTP Basic.

Ainda não há endpoint/tela de histórico nem política de retenção. Escrita
direta no ORM não passa pelos helpers. Cadastros do Django Admin geram
`ADMIN_CRIACAO`, `ADMIN_ATUALIZACAO`, `ADMIN_EXCLUSAO`; mudanças de contas/grupos
também ficam no `LogEntry` nativo. Escritas acadêmicas no admin são bloqueadas. A referência textual usa formatos
diferentes entre CRUD e ações acadêmicas; sua padronização está pendente.

## Limites desta entrega

O CRUD valida unicidade, campos obrigatórios, formatos, referências, curso do
aluno, orientadores distintos, intervalo da banca, local/link conforme modalidade,
uma banca agendada por trabalho, um participante por banca e uma avaliação por
participante. Uma participação avaliada não pode trocar de avaliador, papel ou
banca. Isso não valida disponibilidade da comissão nem habilitação para avaliar.

Status e datas de processo são somente leitura. Rascunhos nascem em `RASCUNHO`,
propostas em `PENDENTE` e participações em `CONVIDADO`. B10 exige orientação
aprovada, confirmações e ausência de conflito antes de agendar. B11 exige defesa
realizada, autoria do avaliador e resultado aberto. Rotas administrativas genéricas
e Django Admin mantêm esses registros apenas para consulta.

As ações acadêmicas B09–B11 implementam submissão, aprovação/devolução,
realização e fechamento do resultado. B12 acrescenta documentos privados,
validação de PDF de até 50 MB, SHA-256, histórico de versões, conferência de
correção/termo e publicação automática. O serializer de monografia retorna `sha256` como leitura;
`arquivo_pdf`, `token_hash` e `expira_em` da participação não são campos dos
CRUDs administrativos. O catálogo público usa endpoints separados em `/api/publico/`.

### Documentos e publicação B12 — 22/11/2026

| Método e rota | Operação |
| --- | --- |
| `GET/POST /api/usuarios/monografias/{id}/documentos/` | Listar documentos ou enviar multipart com `tipo` e `arquivo` |
| `POST /api/usuarios/monografias/{id}/documentos/{documento_id}/conferir/` | Aceitar com `decisao=aceitar` e `confirmacao=true`, ou rejeitar com `decisao=rejeitar` e `motivo` obrigatório |
| `GET /api/usuarios/monografias/{id}/documentos/{documento_id}/arquivo/` | Baixar documento com autorização e hash conferidos |

Aluno envia termo/correção/comprovante; orientador confere correções; coordenador
do curso ou Administrador confere visualmente a assinatura do termo. Ata é
opcional e pode ser enviada pela orientação, coordenação ou administração.
Somente resultado B11 aprovado permite iniciar o fluxo. A última conferência
necessária publica automaticamente; não há endpoint de liberação manual.

`Publicacao.documento_final` e `Publicacao.sha256` identificam o PDF final;
`Monografia.sha256` preserva o hash original do B09. Termos e versões antigas
permanecem privados. Registros publicados não admitem alteração/exclusão no
CRUD ou Admin. A tela correspondente é `/usuarios/trabalhos/{id}/documentos/`.
Veja [arquitetura e testes B12](docs/DESENVOLVIMENTO.md#b12--documentos-correções-e-publicação-automática-22112026).

### Repositório e API públicos B13 — 22/11/2026

`GET /api/publico/monografias/` lista somente publicações B12 consistentes.
Filtros combináveis: `titulo`, `autor`, `orientador` (ID), `curso` (ID),
`ano_defesa` e `palavras_chave` (termos separados por vírgulas). `busca` inclui
metadados e texto do PDF indexado. O ano vem da banca realizada no fuso local.

`ordering` aceita `-data_defesa`, `data_defesa`, `titulo`, `-titulo` e
`-data_publicacao`. `page` começa em 1; `page_size` é 12 por padrão e no máximo
50. Resposta: `count`, `page`, `pages`, `next`, `previous` e `results`.
Parâmetros inválidos/desconhecidos/repetidos recebem 400.

Detalhe: `GET /api/publico/monografias/{id}/`. Arquivo final:
`GET /api/publico/monografias/{id}/arquivo/`, inline por padrão ou download com
`?download=1`. `{id}` é o ID da monografia no principal. Trabalhos sem
publicação B12 válida retornam 404. Arquivo com integridade inválida retorna 409.
Rotas não aceitam escrita, mesmo para administradores (405).

`GET /api/publico/cursos/` e `GET /api/publico/orientadores/` retornam listas de
`{id, nome}` vinculadas a publicações disponíveis. Respostas não incluem
e-mails, matrículas, contas, avaliações, termos ou caminhos privados.

Interface: `/repositorio/` e `/repositorio/{id}/`, sem login. Busca e detalhe
consomem a API via JavaScript; o detalhe também tem HTML inicial utilizável.
A indexação do PDF final ocorre fora da requisição, em worker RabbitMQ com
outbox, retentativas e DLQ. Veja [contratos e operação B13](docs/DESENVOLVIMENTO.md#b13--repositório-api-pública-e-indexação-por-fila-22112026).

## Migrações e testes

As migrações iniciais foram preservadas. A migração de Monografia é simplificada
porque o banco local não continha monografias. Ela verifica a tabela antes de
alterá-la e recusa execução ou reversão com registros, evitando converter IDs
de integrantes em IDs de alunos/professores sem um mapeamento explícito.

Prepare o banco de testes e execute a suíte:

```bash
env/bin/python scripts/postgres_local.py start --test-database
env/bin/python manage.py test --keepdb --noinput
env/bin/python manage.py makemigrations --check --dry-run
env/bin/python manage.py check
```

O banco `test_curso_django_dev` é separado do banco da aplicação. Use `--keepdb`
porque o usuário da aplicação não tem permissão de criar/remover bancos.

Validação atual após o merge: **115 testes aprovados**, incluindo seis cenários
Chrome,
sem casos ignorados. Inclui vínculo de conta por HTML/API, login com painel
docente, staff sem acesso administrativo, revogação e convite do orientador.
Recuperação de senha completa, concorrência distribuída e integração do
microserviço continuam pendentes.

## Telas integradas

| Recurso | Página de gestão |
| --- | --- |
| Alunos | `/equipe/?tipo=aluno` |
| Professores | `/equipe/?tipo=professor` |
| Cursos | `/equipe/?tipo=curso` |
| Monografias | `/monografias/` |
| Bancas | `/monografias/bancas/` |
| Participantes | `/monografias/participacoes-banca/` |
| Membros externos | `/monografias/membros-externos/` |
| Avaliações | `/monografias/avaliacoes/` |

Todas as páginas de gestão acima exigem Administrador e rede autorizada. Oferecem
busca, paginação e consulta. Cadastro, edição e exclusão ficam disponíveis apenas
para alunos, professores, cursos e membros externos. O navegador usa os métodos permitidos, com
sessão e CSRF, e mostra erros junto aos campos. Relações aparecem por nome;
opções dos formulários são geradas pelo Django e incluem todos os registros.
Os endereços antigos de monografias e de adicionar integrantes foram preservados.

Palavras-chave podem ser digitadas separadas por vírgula (a interface converte
para uma lista JSON). Horários das bancas são digitados e exibidos no fuso
`America/Sao_Paulo`, independentemente do fuso do navegador.

Sem JavaScript, os formulários aceitam POST e as listas mostram os primeiros
20 registros. API e POST HTML usam os mesmos serviços de escrita e bloqueios
de estado. Busca e navegação entre páginas requerem JavaScript.

## Telas acadêmicas entregues

| Página | Função e escopo |
| --- | --- |
| `/usuarios/painel/` | Seleciona um papel disponível; sem vínculo, mostra orientação para solicitar acesso |
| `/usuarios/painel/aluno/` | Trabalhos do dono e gestão de rascunhos |
| `/usuarios/painel/professor/` | Orientações, coorientações e participações em bancas não canceladas; filtro por vínculo e painel docente |
| `/usuarios/painel/coordenador/` | Trabalhos dos cursos coordenados |
| `/usuarios/painel/administrador/` | Visão geral e atalhos administrativos |
| `/usuarios/trabalhos/{id}/` | Detalhes e bancas de um trabalho visível ao usuário |
| `/usuarios/rascunhos/novo/` | Formulário do próprio rascunho |
| `/usuarios/rascunhos/{id}/editar/` e `/excluir/` | Escrita do aluno dono apenas em RASCUNHO |
| `/usuarios/convites/{participacao_id}/emitir/` | Emissão HTML por Administrador, orientador principal ou coordenação do curso |
| `/usuarios/convites/{participacao_id}/` | Aceite externo por código, sem exposição de dados antes da validação |

Os painéis usam `q`, `estado` e `page` na consulta HTML, com dez trabalhos por
página. Isso não adiciona filtros aos endpoints acadêmicos JSON. As consultas
compartilhadas em `usuarios/consultas.py` garantem o mesmo escopo básico.
Quem acumula papéis pode alternar pelas abas; o padrão prioriza Administrador,
Coordenador, Professor e Aluno. `is_staff` não interfere nessa seleção.
Professor também aceita `vinculo=orientacoes` ou `vinculo=bancas`. Detalhes
com `?perfil=` respeitam o escopo do perfil selecionado.

Aluno usa POST/PATCH/DELETE da API via `crud.js`. Sem JavaScript, os formulários
fazem POST HTML, com os mesmos serviços e transações. Campos extras de dono,
curso e estado são ignorados pelo ModelForm e não alteram a identidade definida
no servidor; o JSON continua rejeitando campos de leitura com 400.

Emissão/aceite de convite usam POST HTML com CSRF. Endereço de confirmação e
código são apresentados separadamente, sem segredo na URL; a resposta não pode
ser armazenada em cache. O código só é mostrado no resultado da emissão e não
pode ser recuperado pelo GET. Não há envio automático. As condições de estado
são as mesmas da API e ainda dependem de aprovação não implementada no principal.

A navbar oferece Meu painel e saída para todos os autenticados. Os acessos de
gestão continuam exclusivos do papel Administrador. Os templates allauth existentes foram
preservados, com confirmação de e-mail opcional. Submissão, aprovação, avaliação
e publicação estão nos fluxos B09–B12; catálogo e indexação final por fila estão
no B13. Notificações e demais integrações assíncronas permanecem no B17/P0-C.

Consulte o [guia de integração](docs/DESENVOLVIMENTO.md) para ampliar os recursos
e o [backlog](docs/PENDENCIAS_SISTEMA_MONOGRAFIAS_22-11-2026.md) para os fluxos que ainda faltam.
