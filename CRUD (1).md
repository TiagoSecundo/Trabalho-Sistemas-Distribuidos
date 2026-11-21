# CRUD acadêmico

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

## Autenticação nesta etapa

O CRUD é administrativo: exige uma conta Django ativa com `is_staff=True`.
Usuários anônimos recebem 401 e usuários sem esse perfil recebem 403.
Nas chamadas da interface (`X-Requested-With: XMLHttpRequest`), ausência de
sessão retorna 403 sem desafio HTTP Basic, para mostrar o erro na página sem
abrir o diálogo de credenciais do navegador. A exigência de autenticação é igual.
Essa política inicial não implementa ainda as permissões acadêmicas por papel
e titularidade previstas nas próximas etapas do plano.

Crie uma conta administrativa local:

```bash
env/bin/python manage.py createsuperuser
```

No navegador, entre em `/entrar/` e abra as telas de gestão ou `/api/`.
`/api-auth/login/` também permanece disponível. No Postman, selecione
Basic Auth e use a conta Django criada acima. A senha do PostgreSQL não é uma
conta de acesso à API. Requisições que usam sessão devem enviar CSRF nas escritas.

## Rotas

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

Todas as coleções oferecem `GET` para listar e `POST` para criar. Acrescente
`{id}/` para `GET`, `PUT`, `PATCH` e `DELETE`. `PUT` exige todos os campos
obrigatórios; `PATCH` aceita apenas os campos alterados.

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
`curso_nome`, `coordenador_nome`, `aluno_nome`, `orientador_nome`,
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

Monografia:

```json
{"titulo":"API de monografias","resumo":"Descrição do trabalho","palavras_chave":["Django","TCC"],"aluno":1,"curso":1,"orientador":1}
```

Banca:

```json
{"monografia":1,"inicio":"2026-12-10T14:00:00-03:00","fim":"2026-12-10T15:00:00-03:00","modalidade":"PRESENCIAL","local":"Sala 10"}
```

Participação em banca:

```json
{"banca":1,"professor":1,"papel":"AVALIADOR"}
```

Para avaliador externo, cadastre nome, email e instituição em
`/api/membros-externos/`, e use `membro_externo` na participação, em vez de
`professor`. Cada participação deve ter exatamente um desses dois vínculos.

Avaliação:

```json
{"participacao":1,"nota":"8.50","parecer":"Trabalho adequado.","recomendacao":"APROVADA"}
```

A nota foi representada na escala de 0 a 10, com duas casas decimais. Não há
nota mínima de aprovação, cálculo de média ou fechamento automático nesta etapa.
As recomendações aceitas são `APROVADA`, `APROVADA_COM_RESSALVAS` e `REPROVADA`.

## Limites desta entrega

O CRUD valida unicidade, campos obrigatórios, formatos, referências, curso do
aluno, orientadores distintos, intervalo da banca, local/link conforme modalidade,
uma banca agendada por trabalho, um participante por banca e uma avaliação por
participante. Uma participação avaliada não pode trocar de avaliador ou banca.

Status e datas de processo são somente leitura. Monografias novas começam em
`RASCUNHO`; bancas em `AGENDADA`; participações em `CONVIDADO`. Registros publicados,
bancas encerradas e avaliações finalizadas não podem ser alterados pelo CRUD.

Aprovação de orientação, validação de disponibilidade, confirmação de convites,
avaliação pelo próprio participante, cálculo de resultado e publicação são ações
de processo ainda não implementadas. O cadastro administrativo de banca e avaliação
nesta entrega não executa nem certifica essas etapas acadêmicas.

Os campos de PDF/hash e as tabelas DocumentoComplementar/HistoricoAcao estão
preparados no schema. Upload, download, cálculo de hash e auditoria automática
ficam para a etapa de processos; arquivos e tokens não são expostos nesta API.
Não há endpoints públicos do catálogo nesta entrega.

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

Cada página oferece busca, paginação, consulta, cadastro, edição e confirmação
de exclusão. O navegador faz GET/POST/PATCH/DELETE nos endpoints acima, usando
sessão e CSRF, e mostra erros junto aos campos. Relações aparecem por nome;
opções dos formulários são geradas pelo Django e incluem todos os registros.
Os endereços antigos de monografias e de adicionar integrantes foram preservados.

Palavras-chave podem ser digitadas separadas por vírgula (a interface converte
para uma lista JSON). Horários das bancas são digitados e exibidos no fuso
`America/Sao_Paulo`, independentemente do fuso do navegador.

Sem JavaScript, os formulários aceitam POST e as listas mostram os primeiros
20 registros. API e POST HTML usam os mesmos serviços de escrita e bloqueios
de estado. Busca e navegação entre páginas requerem JavaScript.

Consulte o [guia de integração](DESENVOLVIMENTO.md) para ampliar os recursos
e o [backlog](PENDENCIAS.md) para os fluxos que ainda faltam.

---
## Atualização posterior — integração com autenticação acadêmica (20/11/2026)

Esta seção complementa o escopo histórico do CRUD administrativo descrito acima.

Foi desenvolvida separadamente uma camada no app `usuarios` para reconhecer perfis como administrador, aluno, professor e coordenador, usando `auth.User`, grupos e vínculos acadêmicos. Há rotas planejadas/implementadas no trabalho local para painel (`/usuarios/painel/`), informações da conta (`/api/usuarios/me/`), monografias vinculadas ao usuário (`/api/usuarios/monografias/`) e operações próprias sobre rascunhos (`/api/usuarios/rascunhos/`). A presença efetiva de cada endpoint deve ser conferida no código atual.

**Distinção importante:** os oito endpoints de CRUD listados anteriormente permanecem **administrativos**; não devem ser liberados indiscriminadamente para qualquer usuário autenticado. Ações acadêmicas devem usar rotas específicas e verificar papel, vínculo com o objeto e estado do processo no backend.

### Logins e interface existentes

- `/entrar/`: login administrativo legado, com formulário que exige `is_staff`.
- `/accounts/login/`: login fornecido pelo `django-allauth` para contas acadêmicas.
- `/usuarios/painel/`: painel inicial de usuário autenticado.

As telas administrativas existentes usam Django templates, Bootstrap, `templates/base.html` e `templates/navbar.html`. Foi recomendada a reutilização desse layout para o painel acadêmico, sem criar um frontend separado. A unificação visual do login e a adaptação da navbar **foram propostas, mas não estão confirmadas como concluídas**.

### Segurança

A implementação posterior incluiu testes e controles de autorização acadêmica. A funcionalidade de restrição administrativa por IP/VPN foi retirada por decisão do projeto; isso não elimina as verificações de sessão, CSRF, `is_staff` e autorização por papel/objeto. A restrição IP/VPN continua sendo um requisito do enunciado que não estará atendido após essa remoção.

O fluxo completo de submissão, aprovação, agenda, avaliação e publicação não deve ser confundido com o CRUD de cadastros nem com a API de rascunhos.
