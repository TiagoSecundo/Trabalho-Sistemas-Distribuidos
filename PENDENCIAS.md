# Acompanhamento do plano de refatoração

Revisão: **20/11/2026**, após `5f7857b` (PR #3) e a entrega local das telas dos
perfis. Referências: plano original de 11/11, código principal, commits e
`docs/PENDENCIAS_ATUALIZADO.md` recebido da equipe. Os commits da entrega e
resultados de validação ficam em [COMMITS.md](COMMITS.md).

Este é o backlog canônico versionado. `docs/PENDENCIAS.md` é a cópia local.
As cópias numeradas foram consolidadas. O documento recebido descreve também
um ZIP de microserviço; esse código não está neste repositório. Suas capacidades
abaixo são **relatos da revisão recebida**, sem execução ou integração verificada
nesta entrega. Não confundir uma função no serviço separado com fluxo integrado.

## Decisões e escopo atual

- A orientação anterior de não criar telas foi substituída pelo pedido atual
  de implementar os perfis existentes. Foram entregues painéis, rascunhos e
  convites conectados ao backend principal; não foram criadas ações fictícias
  de submissão, aprovação, avaliação ou publicação.
- Confirmação de e-mail é **opcional**, efetivamente configurada em `0178003`
  e integrada em `5f7857b`. Login de conta sem e-mail confirmado foi testado.
- IP/VPN foi retirado do escopo pela equipe. O patch e o script residuais foram
  removidos; `SecurityMiddleware`, CSRF e permissões da aplicação continuam
  ativos. A decisão deixa esse requisito original sem atendimento.
- Integração do microserviço, identidade JWT e consistência de dados continuam
  pendentes. O principal não emite JWT para o serviço separado.

## Entregas integradas e desta revisão

- `14543ac`, PR #1: modelagem, oito CRUDs, HTML/API, migrações e PostgreSQL.
- `39d076d`, `fda173a`, integrados em `9d04dc0`, PR #2: allauth, papéis,
  consultas acadêmicas, rascunhos próprios, convites externos e auditoria.
- `0178003`, integrado em `5f7857b`, PR #3: e-mail opcional e documentos da equipe.
- `4515604`: painéis de Aluno, Professor, Coordenador e Administrador; navegação e logout
  para qualquer conta autenticada; estado orientativo para conta sem vínculo.
- Busca, filtro por situação, paginação, contadores e próximas bancas dentro
  do escopo de cada perfil; detalhe de trabalho sem acesso cruzado indevido.
- Formulários do próprio rascunho via API/HTML e telas de emissão/confirmação
  de convite externo, com serviços compartilhados, CSRF, bloqueios e auditoria.
- `ba8c71e`: limpeza do pacote `cursodjango`, conversor/patch obsoletos, alias de dependências,
  cinco esqueletos vazios e documentos numerados. Backup SQLite preservado
  localmente e removido do rastreamento; migrações, Equipe e fontes de requisitos
  preservados. Documentação canônica consolidada na raiz.

## Situação por item do plano

| Item / prioridade | Estado | Entregue e critério restante |
| --- | --- | --- |
| B01 / P0 — baseline e backup | Concluído | Histórico, fontes e integrações preservados; backup local mantido. |
| B02 / P0 — configuração e legado | Concluído nesta revisão | Configuração ativa única, dependências e `.env` documentados; pacote alternativo, arquivos vazios, script/patch e documentos duplicados removidos; backup fora do Git. Migração de dados Equipe permanece em B06. |
| B03 / P0 — decisões do domínio | Parcial | Vínculos e constraints implementados. Confirmar notas, quórum, composição de banca, correções, publicação e matriz entre serviços. |
| B04 / P0 — autenticação e autorização | Parcial | Allauth com e-mail opcional, papéis por grupo/vínculo, painéis protegidos, acesso por objeto e testes. Falta provisionamento de contas/perfis, política dos diferentes logins, recuperação de senha e identidade JWT integrada. |
| B05 / P0 — Aluno, Professor e Curso | CRUD administrativo concluído; integração pendente | Models, migrações e CRUDs testados. Vinculação de conta/grupo manual; definir IDs compartilhados com o microserviço. |
| B06 / P0 — Monografia e migração | Parcial | CRUD, rascunhos do dono e telas entregues. Mapear integrantes legados e definir fonte de verdade/sincronização entre o model principal e o microserviço. |
| B07 / P0 — API REST | CRUD principal concluído; integração parcial | Contratos administrativos e acadêmicos disponíveis; páginas reutilizam consultas e serviços. Conflitos de rascunhos usam a mesma tradução do CRUD. Faltam contrato/versionamento entre serviços e demais autorizações acadêmicas. |
| B08 / P0 — Banca e auxiliares | Schema e CRUD concluídos; processo parcial | Banca, participação, membro externo e avaliação têm CRUD; painéis exibem bancas vinculadas. Receber evento externo não substitui agendamento seguro. |
| B09 / P0 — submissão e orientação | Pendente no principal; relatado no microserviço | Upload/submissão/aprovação/devolução constam do documento do serviço separado. Falta integração e teste com identidade real; impedir banca antes de aprovação. Rascunho não é submissão. |
| B10 / P0 — agenda e convites | Parcial | Emissão externa por staff/coordenação do curso e confirmação por token têm API e telas. Falta entrega automática, internos, recusa, sobreposição, quórum, reagendamento, renovação e concorrência/eventos. |
| B11 / P0 — avaliação e resultado | Parcial | CRUD administrativo de notas e restrições básicas existente. Falta realização, avaliação pelo participante habilitado, cálculo e fechamento; evento de resultado no microserviço não comprova esses processos. |
| B12 / P0 — documentos e publicação | Parcial no trabalho geral; sem integração no principal | PDF/hash/integridade são relatados no microserviço. Faltam download privado, complementares, versões, correções, termo e publicação autorizada. |
| B13 / P1 — consulta pública | Pendente | API de catálogo somente PUBLICADA, filtros e download autorizado. Painel privado e página inicial não são catálogo público. |
| B14 / P1 — auditoria | Parcial | Eventos de sessão, CRUD, rascunhos e convites; HTML/API acadêmicos gravam na mesma transação. Falta consulta autorizada, retenção, padronização, mudanças de papéis/admin e correlação com simple-history/eventos externos. |
| B15 / P1 — frontend | Perfis e funções existentes entregues; processo completo pendente | Quatro painéis, múltiplos papéis, busca/paginação, rascunhos e convites funcionam no navegador/celular. Futuras telas de processo dependem de APIs integradas e decisão de escopo; não considerar o percurso acadêmico completo. |
| B16 / P1 — PostgreSQL | Principal local concluído | Banco e suíte isolada validados; Compose/banco do microserviço ainda não executados nesta entrega. |
| B17 / P0 — integração de microsserviços | Pendente | Definir autoridade de dados, JWT/claims/IDs, contratos de eventos, entrega confiável, reconciliação e testes ponta a ponta. |

## Limites que permanecem nas telas

1. Professor consulta orientações/coorientações; coordenador consulta trabalhos
   dos cursos coordenados. Esses papéis não ganham CRUD administrativo nem
   ações de aprovação/avaliação por acessar um painel.
2. O aluno pode ler seus trabalhos em qualquer estado, mas só altera/exclui
   RASCUNHO. `AJUSTES_SOLICITADOS` ainda não reabre edição; não há upload no
   principal. Aluno e curso são definidos no servidor.
3. O convite externo exige monografia `APROVADA_ORIENTADOR` ou `BANCA_AGENDADA`,
   banca `AGENDADA` e participação `CONVIDADO`. A aplicação ainda não tem a
   ação de aprovação: os testes preparam esse estado como fixture.
4. A emissão mostra endereço e código uma vez, para entrega manual. O código
   não vai na URL e só confirma aquela participação; não autoriza download
   nem avaliação. Falta envio automático e proteção concorrente com reagendamento.
5. Conta sem grupo/vínculo recebe orientação para contatar a administração.
   Cadastro allauth não provisiona Aluno/Professor. Staff tem precedência sobre
   os outros papéis e usa o painel administrativo.
6. O admin Django e escritas diretas no ORM não recebem automaticamente a
   auditoria dos serviços. As permissões de orientador/avaliador preparadas no
   código ainda dependem dos respectivos endpoints de processo.

## Microserviço — implementação relatada no documento recebido

| Área | Evidência localizada | Limite atual |
| --- | --- | --- |
| API REST de monografias | `MonografiaViewSet`, CRUD e filtros por status, curso, aluno, orientador; busca por título, resumo e palavras-chave | Banco/modelo separados do principal; regras de acesso precisam ser revisadas |
| Autenticação de chamadas | `JWTStatelessUserAuthentication` do SimpleJWT; claims `role`, `aluno_id`, `professor_id` | O comando `gerar_token` **simula** um emissor para desenvolvimento; não existe integração demonstrada com o login real do sistema principal |
| Upload de PDF | `POST /api/monografias/{id}/upload/`; extensão `.pdf`, assinatura `%PDF-`, tamanho máximo configurável e SHA-256 por partes | Não há endpoint específico de download privado; falta validar comportamento e permissões em execução |
| Submissão | `POST /api/monografias/{id}/submeter/`; exige arquivo, atualiza estado/data, usa lock temporário no Redis e publica evento | Fluxo não está integrado ao principal; falta robustez diante de falha na publicação/concorrência |
| Orientação | `POST /api/monografias/{id}/aprovar-orientador/` e `/solicitar-ajustes/`; compara o ID do orientador, registra estado e evento | O motivo dos ajustes é enviado no evento, mas não há campo persistido específico no model; testar ponta a ponta |
| Integridade | `GET /api/monografias/{id}/verificar-integridade/`; recalcula SHA-256 do arquivo | Disponível apenas no escopo de leitura autorizado pelo viewset; depende do armazenamento do arquivo |
| Histórico | `django-simple-history` em `Monografia` e `DocumentoComplementar` | Histórico dos dois projetos não foi unificado nem tem consulta administrativa específica demonstrada |
| Redis | Cache; lock `upload_em_andamento`; throttle de submissão `5/hour` | Configuração existe, mas comportamento real/cargas não foram testados aqui |
| RabbitMQ | Publicador de eventos `monografia.*`; consumidor de eventos `banca.*` e `repositorio.extracao_concluida`; fila de erro (DLQ) | Eventos de outros serviços ainda não estão comprovadamente conectados; falhas de publicação são registradas em log, sem garantia de entrega |
| PostgreSQL e contêineres | `docker-compose.yml` com banco, Redis, RabbitMQ, `web` e `consumer`; `Dockerfile` | Estrutura pronta no código, **não validada por execução** nesta revisão |
| Saúde e documentação da API | `/health/`, `/api/schema/`, `/api/docs/` (Swagger) | Rota de saúde verifica banco e Redis; não verifica diretamente RabbitMQ nem o consumidor |
| Testes do microserviço | Arquivo `monografias/tests.py` | Apenas esqueleto; não foram encontrados testes automatizados implementados no ZIP |

### Rotas relevantes já definidas no microserviço

- `GET/POST /api/monografias/`
- `GET/PUT/PATCH/DELETE /api/monografias/{id}/`
- `POST /api/monografias/{id}/upload/`
- `POST /api/monografias/{id}/submeter/`
- `POST /api/monografias/{id}/aprovar-orientador/`
- `POST /api/monografias/{id}/solicitar-ajustes/`
- `GET /api/monografias/{id}/verificar-integridade/`
- `GET /health/`, `GET /api/schema/` e `GET /api/docs/`

O `docker-compose.yml` mapeia o serviço web para a **porta 8001 no host** (porta 8000 no contêiner). Isso permite executá-lo ao lado do sistema principal, normalmente acessado na porta 8000, **sem significar que os serviços já se comuniquem**.

## Pendências de integração relatadas pelos outros desenvolvedores

### P0 — integração, identidade e segurança

1. **Definir a fonte de verdade de `Monografia`.** O principal já possui CRUD/schema de monografia e o microserviço mantém **outro** model/banco com `aluno_id`, `orientador_id` e `curso_id` numéricos. Decidir quais ações pertencem a cada serviço, como sincronizar o estado e evitar duas escritas concorrentes sobre o mesmo trabalho.
2. **Integrar JWT ao login de verdade.** O microserviço não tem endpoint de login ou emissão de JWT a partir do allauth: `gerar_token` é um comando de desenvolvimento. Estabelecer emissor confiável, claims (`role`, `user_id`, `aluno_id`, `professor_id`), duração, chave de assinatura segura e verificação de perfis desativados/revogados. **Não usar geração manual de token como solução final.**
3. **Corrigir autorizações amplas.** No ZIP, `coordenador` consegue listar todas as monografias e `admin` também; o papel de coordenador deveria ser avaliado conforme a regra de curso decidida pelo grupo. Aluno tem queryset restrito ao próprio ID, mas o serializer permite editar campos como `orientador_id` e `curso_id` sem validação de vínculo/permite alterações sensíveis. Rever também exclusão de trabalhos já submetidos e ações por estado.
4. **Controlar acesso aos PDFs.** Implementar download privado mediante autorização e testar se a rota de arquivos/media e o armazenamento impedem leitura anônima ou de outra pessoa. Proteger também documentos complementares.
5. **Revisar os caminhos de autenticação existentes no principal.** Os acessos `/accounts/login/`, `/entrar/`, `/admin/`, `/api-auth/login/` e Basic Auth tinham políticas diferentes no arquivo-base. Confirmar quais devem permanecer e testar acesso indevido, conta sem vínculo, conta inativa, logout e confirmação de e-mail **não obrigatória**.

### P0/P1 — comunicação, consistência e fluxo

6. **Conectar eventos reais, não só simulá-los.** O serviço publica eventos na exchange `monografias` e consome eventos de `eventos_externos`. Verificar os produtores/consumidores reais do serviço de banca e do repositório, com esquema de mensagens e IDs coerentes.
7. **Evitar perda e repetição indevida de eventos.** `publicar()` registra erros de RabbitMQ sem interromper a transação já confirmada; falta estratégia de entrega confiável (por exemplo, outbox, retentativas e reconciliação). A checagem atual de idempotência por **estado final** não substitui identificação única de evento; testar eventos repetidos, atrasados e fora de ordem.
8. **Revisar locks/transações.** Em `submeter`, a chave Redis é criada antes da transação e pode permanecer até o TTL em casos de falha; o consumidor de `repositorio.extracao_concluida` a libera. Confirmar se o serviço externo sempre publicará esse evento, inclusive em falhas, e testar operações simultâneas.
9. **Completar sequência acadêmica.** Confirmar entrada em análise, aprovação/devolução e reenvio; impedir agendamento antes da aprovação; garantir que `banca.resultado_final` não encerre uma defesa em estado indevido; implementar cálculo de resultado, correções e publicação.
10. **Completar contratos dos documentos.** Upload/dados de arquivos, download e validação dos documentos complementares, restrição de tamanho/assinatura e políticas de armazenamento e publicação.

### P1 — verificação e operação

11. **Escrever testes automatizados do microserviço.** `monografias/tests.py` não contém casos de teste. Cobrir JWT e papéis, isolamento por aluno/curso/orientador, arquivo adulterado, PDF inválido/grande/duplicado, submissão repetida, aprovação indevida, consumo repetido, DLQ, falha do RabbitMQ e concorrência.
12. **Executar integração e carga.** Subir os serviços do `docker-compose.yml`, aplicar migrações, testar `/health/`, Swagger e chamadas reais; testar fluxo entre banco/Redis/RabbitMQ/serviço principal e comportamento sob acessos simultâneos.
13. **Completar observabilidade e auditoria.** Relacionar eventos com IDs de correlação/usuário, inspecionar filas/DLQ, tratar mensagens malformadas e oferecer consulta de histórico autorizada.
14. **Revisar implantação.** Gerenciar `.env`/JWT com segurança, não expor senhas de exemplo, configurar HTTPS quando aplicável e definir backups dos bancos e dos PDFs. O `Dockerfile` e o Compose são estrutura de execução, não evidência de ambiente produtivo pronto.

## Decisões do domínio ainda necessárias (B03)

- Nota mínima, pesos, desempate e compatibilidade com as recomendações dos avaliadores.
- Quantidade de membros, quórum, presidente/suplente, sobreposição de agendas e coorientador.
- Limite de trabalhos ativos, reenvios, histórico de bancas e exclusão/inativação.
- Quem cadastra/inativa aluno/professor/coordenador e quais campos cada perfil pode alterar.
- Troca do orientador, motivo de ajustes, prazo de correções e pré-requisitos de publicação.
- Tamanho máximo e política de PDFs duplicados (o microserviço **atualmente bloqueia hash repetido**).
- Modelo de autorização/armazenamento dos documentos e retenção dos logs/auditoria.
- Participação de membros externos: token de confirmação **não é automaticamente token de avaliação ou de download**.

## Próximas entregas

1. **Identidade e dados (B04/B06/B17):** emissor JWT confiável, claims/IDs,
   revogação, autoridade do dado e autorização por curso/objeto. Não usar o
   comando manual de token do microserviço como solução final.
2. **Submissão integrada (B09/B12/B17):** PDF privado, hash, upload, submissão,
   ajustes/reenvio e aprovação com conta real, sem edição manual de estados.
3. **Eventos e consistência (B10/B11/B17):** produtores/consumidores reais,
   outbox ou estratégia equivalente de entrega confiável, idempotência por
   evento, ordem, retentativa, DLQ e concorrência.
4. **Banca e resultado (B10/B11):** agenda/quórum, convites internos e recusa,
   avaliação própria, realização, resultado e correções com regra acadêmica.
5. **Publicação e catálogo (B12/B13):** documentos complementares, termo,
   download autorizado e somente trabalhos publicados na consulta pública.
6. **Auditoria e validação (B14/B16/B17):** consulta autorizada, retenção e
   correlação entre serviços, testes distribuídos e comandos reproduzíveis.
   Ampliar as interfaces somente conforme as ações forem integradas.

## Validação desta entrega

A suíte usa `test_curso_django_dev`, sem fixtures no banco da aplicação.
`manage.py check` passou e `makemigrations --check --dry-run` não detectou
alterações. A suíte completa teve **78 testes aprovados, sem falhas ou testes
ignorados**, incluindo quatro cenários Chrome. Os resultados estão em
[COMMITS.md](COMMITS.md).

Foram adicionados testes de isolamento por aluno/curso, múltiplos papéis,
conta sem vínculo/inativa, e-mail opcional, CSRF, leitura de detalhes, busca e
paginação, estados protegidos, auditoria/rollback e convite externo. Os testes
Chrome exercitam rascunhos por chamadas reais à API, perfis, confirmação externa,
logout e viewport móvel. Isso não comprova o microserviço nem os processos
acadêmicos ainda ausentes.

## Decisões e itens externos à entrega

IP/VPN foi retirado do escopo escolhido e não é apresentado como proteção
ativa. Redis/RabbitMQ e JWT aparecem no relatório do serviço separado, porém
não estão integrados ao principal. Extração de PDF, repositório público, testes
de carga e implantação produtiva continuam sem comprovação nesta cópia.
O PDF original e os documentos de referência recebidos foram preservados.
