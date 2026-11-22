# Sistema de Monografias — pendências reais para entrega

**Atualizado em:** 22/11/2026

**Objetivo:** consolidar **somente o que ainda precisa ser implementado, integrado, corrigido ou comprovado**, evitando reabrir funcionalidades já entregues.

**Projetos:** `Trabalho-Sistemas-Distribuidos` (principal, branch `feature/autenticacao`) e `microservico-sd` (microserviço, branch `main`).

## 1. Como este levantamento foi feito

Fontes utilizadas:

1. Enunciado original **“Trabalho de Sistemas Distribuídos”**, do prof. Alessandro Vivas Andrade, especialmente as seções de autenticação, submissão, banca, publicação, APIs, microsserviços, Redis, filas, escalabilidade, dashboard e histórico.
2. Última cópia compartilhada do código, **`Trabalho SC(4).zip`**, e documentação `PENDENCIAS.md` da equipe.
3. Alterações posteriores dos módulos **B09, B10 e B11**, inclusive as implementações de avaliação externa e integração entre os dois projetos.
4. Resultados informados e executados pelo integrante no Ubuntu em 22/11/2026.
5. Implementação local B12 autorizada pelo integrante, migração aplicada e testes de regras, Chrome e HTTP/JWT real executados em 22/11/2026; detalhes em [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md#b12--documentos-correções-e-publicação-automática-22112026).
6. Implementação local B13 solicitada na sequência, incluindo API/catálogo anônimos e indexação do PDF final via RabbitMQ real; evidências e operação em [DESENVOLVIMENTO.md](DESENVOLVIMENTO.md#b13--repositório-api-pública-e-indexação-por-fila-22112026).

**Importante:** a revisão se baseia no código fornecido e nas alterações/testes comprovados nesta conversa. Não é uma inspeção independente de eventuais commits posteriores dos colegas no GitHub. Onde isso fizer diferença, a tarefa é **verificar**, não reimplementar.

### Legenda

- **CONCLUÍDO NO ESCOPO:** código implementado e testes automatizados aprovados; pode haver validações complementares para entrega.
- **PARCIAL:** componente existente, mas parte da exigência acadêmica ainda não está implementada ou demonstrada.
- **PENDENTE:** funcionalidade obrigatória não localizada como implementação utilizável.
- **VERIFICAR:** não há evidência suficiente para afirmar que falta; conferir antes de programar.

### Evidência de funcionamento já obtida

| Projeto / funcionalidade | Evidência | Situação |
|---|---|---|
| Sistema principal, suíte completa após B09 | **163 testes encontrados: 157 aprovados, 6 ignorados, 0 falhas** | Aprovada |
| B09, testes específicos do principal | **13/13 aprovados** | Aprovado |
| Microserviço após patch B09 | **6/6 aprovados** (toda a suíte descoberta naquele projeto) | Aprovado, porém cobertura pequena |
| B10, agendamento de bancas | **12/12 testes específicos aprovados** | Aprovado |
| B11, avaliação externa | **13/13 testes específicos aprovados** | Aprovado |
| B09 em funcionamento real | Aluno enviou PDF; orientador consultou o documento e aprovou; serviços em `8000`/`8001`, com `/health/` respondendo 200 | **Fluxo principal validado manualmente** |
| B09 no microserviço | Commit **`75636b4`**, enviado para `main` de `HudsonJR777/microservico-sd` | Publicado |
| B09 no principal | Integrante confirmou que também fez o push | **Publicado, segundo confirmação do integrante** |
| B10 / B11 no principal | Commits `edb86d0` (B10), `8664788` (B11 interno) e `dc3493a` (avaliação externa) | Publicados anteriormente |
| B12, suíte de regressão após implementação | **189 encontrados: 181 aprovados, 8 opcionais ignorados, 0 falhas**, antes de acrescentar os dois testes remotos opcionais | Aprovada localmente |
| B12, regras, arquivos, permissões e concorrência PostgreSQL | **24/24 aprovados** | Aprovado localmente |
| B12, navegador Chrome com contas e sessões | **2/2 aprovados**, publicação sem ressalvas e rejeição/reenvio com ressalvas; desktop e celular | Aprovado localmente |
| B12, integração real com microserviço `75636b4` | **2/2 aprovados**, HTTP/JWT sem mocks, original preservado e hash final conferido | Aprovado em ambiente Docker descartável |
| B12, migração e consistência | `0006_documentos_publicacao_b12` aplicada; `check` sem problemas e `makemigrations --check --dry-run` sem alterações | Commit/push desta entrega pendentes |
| B13, suíte completa padrão | **216 encontrados: 201 aprovados, 15 opcionais ignorados, zero falhas** | Aprovada localmente |
| B13, API/privacidade/filtros/outbox/indexação/migração | **20/20 aprovados**, incluídos na suíte completa | Aprovado localmente |
| B13, Chrome anônimo | **2/2 aprovados**, seis filtros, paginação, detalhe, download, erro/retomada e desktop/celular | Aprovado localmente |
| B13, RabbitMQ real | **3/3 aprovados**, extração/busca, mensagens repetidas, DLQ e retomada de envio após falha | Filas de teste descartadas; broker/worker locais ativos |

> **Limites da evidência:** testes B12 de regras e navegador simulam o transporte do PDF original; a integração B12 usa HTTP/JWT real. No B13, filas/extração/busca foram testadas com RabbitMQ real. Bancas e PDFs são fixtures; não são termos acadêmicos assinados reais. Notificações, extração na submissão B09, Redis de busca/sessões e carga continuam pendentes.

---

## 2. Situação consolidada por requisito B01–B17

| Item | Estado atualizado | Observação objetiva |
|---|---|---|
| **B01 — Base/backup** | Concluído no escopo anterior | Preservar documentação, migrações e backups; validar restauração na entrega, se aplicável |
| **B02 — Configuração e legado** | Concluído no escopo anterior | Verificar apenas configuração de implantação final |
| **B03 — Regras de domínio** | **Parcial** | Média **6,0** e média aritmética já adotadas; correções/publicação definidas no B12; composição/quórum acadêmico ainda dependem das exigências do curso |
| **B04 — Autenticação/autorizações** | **Parcial** | Allauth, perfis, JWT e avaliação externa existem; faltam controle de rede IP/VPN, revisão de autorizações e rotas administrativas alternativas |
| **B05 — Alunos/professores/cursos** | Concluído no núcleo | CRUD e vínculos de conta funcionam; não recriar |
| **B06 — Monografia/rascunho** | Concluído no núcleo; integração histórica parcial | Dois IDs vinculados no B09; trabalhos remotos antigos não vinculados automaticamente |
| **B07 — API REST** | **Núcleo implementado; entrega B13 pendente** | APIs administrativas/acadêmicas, ações privadas B12 e leituras públicas B13 disponíveis; revisões gerais de segurança continuam abaixo |
| **B08 — Modelagem de bancas e auxiliares** | Concluído no núcleo | Models, CRUD e participantes existentes |
| **B09 — Submissão e orientação** | **Concluído no fluxo principal; validação complementar** | PDF, hash, submissão, leitura privada e aprovação integrados; testar manualmente devolução para ajustes/reenvio e falhas |
| **B10 — Agendamento/convites** | **Concluído no núcleo; integração assíncrona pendente** | Aprovação prévia, proposta, confirmações e conflitos; faltam notificações automáticas via fila |
| **B11 — Avaliação/resultado** | **Concluído no núcleo** | Professores e externos, nota/parecer/recomendação, média e fechamento testados; integração de eventos/revisão do CRUD legado ainda a avaliar |
| **B12 — Correções/documentos/publicação** | **Implementado e validado localmente; entrega Git pendente** | Documentos privados, conferência humana, versões, publicação automática e arquivo final fixado; testes de regras, navegador e integração real aprovados |
| **B13 — Repositório público** | **Implementado e validado localmente; entrega Git pendente** | Seis filtros, API anônima, catálogo/detalhe, PDF final e busca textual assíncrona; testes de API, Chrome e RabbitMQ real aprovados |
| **B14 — Auditoria** | **Parcial** | `HistoricoAcao` e `django-simple-history` existem; falta confirmar rastreabilidade fim a fim e operações do admin |
| **B15 — Frontend e dashboard** | **Parcial** | Painéis, ações acadêmicas, B12 e catálogo público B13 presentes; faltam os **5 gráficos** |
| **B16 — PostgreSQL** | Concluído no ambiente local | Dois bancos/migrações executados; documentar inicialização/reprodução |
| **B17 — Integração distribuída** | **Parcial** | JWT/HTTP B09 e indexação B13 via RabbitMQ/outbox validados; faltam extração na submissão, outros eventos, cache de busca, notificações e carga |

**Regra para o grupo:** B09, B10 e B11 **não devem voltar à categoria “a implementar”**. Suas pendências remanescentes são integrações, validações ou correções específicas, detalhadas abaixo.

---

## 3. Pendências obrigatórias de maior prioridade

### P0-A — B12: versão corrigida, documentos e publicação automática

**Situação em 22/11/2026:** implementação e validação local finalizadas. A entrega ainda não recebe o rótulo global **CONCLUÍDO**, pois commit/push não foram realizados (critério 8.6). Decisões aprovadas pelo integrante antes da implementação.

**Exigência expressa do enunciado:** a monografia só pode ser publicada após **aprovação final na banca**, **entrega de versão corrigida quando houver ressalvas** e **termo de autorização de publicação assinado**.

**Já existe e deve ser aproveitado:**

- Status `APROVADA`, `APROVADA_COM_RESSALVAS`, `CORRECOES_ENTREGUES` e `PUBLICADA` no modelo `Monografia`.
- Modelo `DocumentoComplementar` no principal, com tipos `ATA`, `TERMO_AUTORIZACAO`, `COMPROVANTE_CORRECAO` e `VERSAO_CORRIGIDA`.
- Modelo de documento complementar também no microserviço, com nomenclatura própria de tipos.
- Resultado da banca calculado e gravado pelo B11.

**Checklist de implementação — realizado:**

- [x] Definir **qual sistema é responsável por armazenar a versão corrigida e o termo**, evitando upload e estados contraditórios nos dois bancos; manter IDs referenciáveis. **Principal: documentos B12 e cópia final; microserviço: original B09.**
- [x] Criar envio autenticado dos documentos necessários (incluindo PDF da versão corrigida) com **validação de formato, tamanho e hash SHA-256** e acesso privado enquanto não publicado. **PDF estruturalmente válido, sem senha, até 50 MB; downloads autorizados conferem hash.**
- [x] Permitir envio da versão corrigida **somente quando a banca exigir ressalvas**; persistir qual arquivo é a versão final para publicação. **Resultado original B11 preservado; `Publicacao.documento_final` define o arquivo.**
- [x] Definir e implementar quem **confirma a correção**, registrando decisão e data. **Orientador principal; rejeição motivada, nova versão exige nova conferência.**
- [x] Permitir anexar o **termo de autorização assinado**, registrar quem enviou e quando; **não presumir que um PDF anexado está assinado**. **Coordenador do curso ou Administrador confirma visualmente a assinatura com declaração explícita, usuário e data.**
- [x] Implementar serviço de **publicação com pré-condições verificadas no backend**. **A última conferência necessária publica automaticamente, sem botão de liberação.**
- [x] Garantir que reprovação, falta de termo ou falta de correção obrigatória **bloqueiem** a publicação. **Também bloqueia inconsistência no fechamento B11 e arquivo adulterado.**
- [x] Ao publicar, fixar status `PUBLICADA`, `data_publicacao` e arquivo final; impedir edição/exclusão indevida após publicação. **Proteções na API, HTML, CRUD e Admin; cópia original com hash validado quando não há ressalvas.**
- [x] Registrar auditoria de submissão de documentos, aprovação das correções e publicação. **Histórico de versões/decisões preservado; operação transacional e idempotente.**
- [x] Testar caminho aprovado sem ressalvas; aprovado com ressalvas e correção; reprovado; termo ausente; documento inválido; publicação repetida; usuário sem permissão. **24 testes de regras, 2 de navegador e 2 de integração real aprovados.**

**Evidência e reprodução:** [guia B12 em DESENVOLVIMENTO.md](DESENVOLVIMENTO.md#b12--documentos-correções-e-publicação-automática-22112026). Migração `0006` aplicada no banco local. Falha remota reverte a última conferência e permite repeti-la. Legado não é promovido a documento conferido automaticamente. Ata/comprovante são opcionais. O download B12 continua privado; exposição pública e eventos pertencem a P0-B/P0-C.

**Entrega restante:** commit/push do código e inclusão deliberada da documentação, pois `docs/` permanece ignorada pelo Git. Nenhum commit das alterações preexistentes de interface foi criado nesta implementação.

**Critério de conclusão:** usando contas reais, um trabalho aprovado sem ressalvas e outro com ressalvas podem ser publicados **apenas após** cumprir suas condições; todas as tentativas indevidas são barradas pela API e pela interface.

**Atenção:** o enunciado não exige verificar criptograficamente uma assinatura digital no termo; exige que o termo esteja **assinado**. Não inventar infraestrutura de assinatura digital sem definição do grupo/professor.

### P0-B — B13: repositório e API públicos

**Situação em 22/11/2026:** implementação e validação local finalizadas; commit/push pendentes conforme critério 8.6. O integrante esclareceu que a configuração existente era JWT; RabbitMQ próprio do B13 e worker foram preparados e iniciados localmente, preservando a configuração JWT.

**Exigência expressa:** qualquer visitante, sem login, deve pesquisar trabalhos **publicados** por **título, autor, orientador, curso, ano de defesa e palavras-chave**. A API deve expor JSON de **monografias publicadas**, **cursos** e **orientadores**.

**Checklist de implementação — realizado:**

- [x] Criar endpoints públicos **sem autenticação**, separados das rotas administrativas, com listagem de monografias `PUBLICADA` e listas de cursos/orientadores. **Prefixo `/api/publico/`; somente leitura e campos públicos. Exige também registro B12 consistente.**
- [x] Implementar todos os **seis campos de filtro** exigidos: título, autor, orientador, curso, ano de defesa e palavras-chave. **Filtros isolados e combinados testados; busca geral adicional em metadados/texto.**
- [x] Garantir que o **ano de defesa** venha da data da banca realizada, não seja confundido automaticamente com ano da publicação. **Fuso `America/Sao_Paulo` validado inclusive na virada de ano UTC.**
- [x] Criar página pública de busca, resultados e detalhes, integrada à API via JavaScript. **`/repositorio/` e `/repositorio/{id}/`, navegação, URL compartilhável e layout responsivo.**
- [x] Permitir leitura/download **somente do PDF final publicado**; manter versões anteriores, termo e documentos privados protegidos. **SHA-256 conferido; nenhum ID arbitrário de documento aceito nas rotas públicas.**
- [x] Implementar ordenação/paginação, mensagens de lista vazia e validações básicas de filtros. **12 por página, máximo 50; erros de parâmetros/rede, nova tentativa e filtros removíveis.**
- [x] Integrar a **indexação de texto** extraído do PDF ao mecanismo de busca, com indexação assíncrona conforme o enunciado. **Evento de publicação em outbox, RabbitMQ real, extração no worker e vetor PostgreSQL/GIN; B09/submissão permanece no P0-C.**
- [x] Criar testes garantindo que `RASCUNHO`, `SUBMETIDA`, `REPROVADA`, `APROVADA` mas ainda não publicada e `APROVADA_COM_RESSALVAS` não apareçam publicamente. **Também bloqueia `PUBLICADA` sem registro B12 e inconsistências de versão/vínculo.**
- [x] Testar acesso sem login, download autorizado e tentativa de acessar PDFs privados por URL direta. **20 testes de backend, 2 de navegador e 3 de integração RabbitMQ aprovados.**

**Evidência e operação:** [guia B13](DESENVOLVIMENTO.md#b13--repositório-api-pública-e-indexação-por-fila-22112026). Migrações `repositorio.0001/0002` aplicadas; publicações existentes são enfileiradas. Broker local em `5673`, painel em `15673`; worker `processar_repositorio` e diagnóstico `status_repositorio`. Nenhuma senha foi versionada.

**Entrega restante:** commit/push e inclusão deliberada de `docs/`, ainda ignorada pelo Git. Redis/cache/carga e notificações não foram marcados como concluídos por esta entrega.

**Critério de conclusão:** um visitante anônimo encontra o TCC publicado pelos seis filtros, vê os dados públicos e acessa apenas o arquivo final permitido; trabalhos não publicados não vazam por nenhuma rota pública.

### P0-C — Processamento de PDF e eventos (B09/B10/B11/B12/B13/B17)

**Exigência expressa:** extração de texto do PDF deve ocorrer **de forma assíncrona por fila**, não dentro do upload; o agendamento precisa produzir **notificações automáticas via eventos**. RabbitMQ ou Kafka é obrigatório como tecnologia do trabalho.

**Já existe:** RabbitMQ, um publicador/consumidor e eventos de submissão no microserviço; Redis para lock e limitação de submissões. No B13, **extração/indexação do PDF final via evento de publicação, outbox transacional, ACK após commit, idempotência, retentativas e DLQ foram implementados e testados com broker real**. Isso não comprova extração na submissão B09 nem entrega de notificações.

**Falta fazer:**

- [ ] Criar ou conectar um **consumidor real** para `monografia.submetida` (ou o evento definido pelo grupo) que faça leitura e **extração de texto** do PDF com biblioteca própria para PDF.
- [ ] Salvar texto/índice de forma consultável, com associação correta à monografia, à versão do PDF e ao status publicado.
- [ ] Garantir que upload termine sem esperar pela extração; testar processamento assíncrono e eventual falha do arquivo.
- [ ] Produzir evento `banca.agendada` **a partir do fluxo B10 de verdade**, e não somente por comando de simulação.
- [ ] Implementar consumidor de notificação que informe **todos os membros da banca e o aluno** sobre o agendamento por mecanismo efetivo (por exemplo, e-mail), usando RabbitMQ.
- [x] Conectar evento de publicação para atualizar o índice/repositório. **B13 implementado; aviso por e-mail ao aluno continua pendente.**
- [ ] Definir contrato mínimo de evento: ID único, monografia de origem, identificador do evento, ação, data e referência da versão; não misturar PKs dos dois bancos. **Contrato de publicação B13 pronto; padronização dos demais eventos pendente.**
- [ ] Prever mensagens duplicadas, falha do worker/broker e retomada; **não perder mudança de estado** se o banco confirmar e a publicação do evento falhar. Avaliar *transactional outbox* ou mecanismo equivalente.
- [ ] Registrar sucesso/falha/retentativa e inspecionar a DLQ existente quando houver mensagens inválidas. **B13 registra esses estados e sua DLQ foi testada; estender a comprovação aos demais fluxos.**

**Critério de conclusão:** envio de PDF gera processamento em worker, texto é indexado sem bloquear o upload; uma banca agendada causa **notificação entregue**; desligar e religar o consumidor não gera duplicações indevidas.

**Não obrigatório como desenho específico:** criar seis novos repositórios ou serviços só porque o enunciado os cita como **exemplos**. O importante é demonstrar independência das APIs/serviços, uso real de fila e distribuição das responsabilidades.

### P0-D — Redis, buscas, sessões e escalabilidade (B17)

**Exigência expressa:** Redis para **cache de sessões**, **cache de resultados de busca**, **controle de uploads em processamento** e **limitação de taxa de submissões**. Escalar consultas simultâneas do repositório.

- [x] Redis disponível no Docker do microserviço; health check reportou `redis: ok`.
- [x] Lock `upload_em_andamento:<id>` e throttle de submissão constam do microserviço.
- [ ] Configurar/validar **sessões com cache Redis** no componente responsável por sessões de usuários, com política de expiração e comportamento após indisponibilidade.
- [ ] Usar Redis para **cache dos resultados de busca públicos** (chaves por filtros/página, TTL e invalidação na publicação/atualização permitida).
- [ ] Confirmar liberação correta de lock em falhas e concorrência, incluindo PDFs enviados duas vezes simultaneamente.
- [ ] Demonstrar que chamadas repetidas usam cache e que conteúdo recém-publicado aparece após invalidação/expiração.
- [ ] Preparar execução e **teste de carga representativo** do repositório, registrando número de usuários virtuais, latência, taxa de erro, uso do cache e limitações do ambiente.

**Critério de conclusão:** os quatro usos de Redis do enunciado estão comprovados e há evidência reproduzível de comportamento sob carga. Não afirmar “suporta milhares” apenas porque o Redis está iniciado.

### P0-E — Dashboard: cinco gráficos exigidos (B15)

**Já existe:** painéis personalizados por papel e contadores simples. **Isso não substitui os gráficos obrigatórios.**

Criar, com dados autorizados, os seguintes gráficos:

- [ ] **Monografias por curso**.
- [ ] **Monografias por orientador**.
- [ ] **Monografias por ano de defesa**.
- [ ] **Taxa de aprovação** (definir numerador/denominador: por exemplo, decisões finais aprovadas ou com ressalvas ÷ defesas com resultado final).
- [ ] **Tempo médio entre submissão e defesa** (registrar em dias/horas; ignorar trabalhos sem ambas as datas).

Além disso:

- [ ] Criar API JSON de agregações e gráficos no frontend JavaScript (Chart.js/Plotly são sugestões do enunciado, não obrigações por marca).
- [ ] Reutilizar `data_submissao`, data real da banca, status final e vínculos curso/orientador; evitar dados fictícios.
- [ ] Respeitar escopo dos perfis, se o dashboard for privado; decidir se haverá visão institucional para administrador.
- [ ] Testar contagens/fórmulas com casos conhecidos, períodos vazios e bancas canceladas.

**Critério de conclusão:** os cinco gráficos aparecem e cada número pode ser conferido por consulta aos registros do sistema.

### P0-F — Controle IP/VPN na área administrativa (B04)

**O enunciado exige expressamente** que a área administrativa valide acesso pela **rede institucional (IP/VPN)**, mantendo o repositório público sem login. A equipe havia optado por não implementar essa restrição; portanto, **permanece uma divergência conhecida com o enunciado**.

- [ ] Definir com o grupo quais rotas integram a **área administrativa** e qual faixa IP/VPN será permitida no ambiente demonstrado.
- [ ] Aplicar restrição no proxy/middleware, com cuidado para não confiar cegamente em cabeçalhos `X-Forwarded-For` fornecidos pelo cliente.
- [ ] Negar acesso administrativo fora da rede e permitir dentro, sem restringir o catálogo público.
- [ ] Testar sessões/admin/rotas sensíveis em cenários dentro/fora da rede.

**Critério de conclusão:** proteção de rede funcional e teste demonstrável. **Decisão de projeto:** se o grupo mantiver a exclusão, documentar explicitamente o requisito não atendido; não marcar como concluído.

---

## 4. Ajustes e validações sobre funcionalidades já implementadas

Estes itens **não justificam refazer B09, B10 ou B11**. São verificações pontuais de conformidade e operação.

### B09 — Submissão/aprovação: somente fechamento e robustez

- [x] Aluno enviou PDF pelo principal; microserviço recebeu.
- [x] Orientador abriu o documento e aprovou; o fluxo principal funcionou na prática.
- [x] Vínculo por `microservico_id` ↔ `origem_id` e sincronização manual de estado implementados.
- [x] Testes do principal e do microserviço aprovados.
- [ ] Fazer **teste manual da devolução com motivo, edição e reenvio** (automatizado já passou).
- [ ] Verificar em teste prático que a aprovação muda para `APROVADA_ORIENTADOR` e libera a ação do B10, sem alteração direta no banco.
- [ ] Confirmar comportamento em queda de rede depois do upload, resposta duplicada, token expirado e sincronização posterior; incluir casos automatizados que faltarem.
- [ ] Decidir como tratar **monografias antigas** criadas somente no microserviço; o patch não vincula automaticamente esses registros.

**Aceite adicional:** percurso completo de ajustes e reenvio no navegador, com IDs/estados consistentes após falhas controladas.

### B10 — Agendamento: preservar núcleo entregue

- [x] Aprovação prévia obrigatória, propostas `PENDENTE`, confirmação interna/externa, conflito de horários e transição `AGENDADA` testados.
- [ ] **Notificação automática via fila** após `AGENDADA` (prioridade P0-C acima).
- [ ] Executar **teste real de duas confirmações concorrentes** e conflitos de professores/externos; o código já usa transações e bloqueios PostgreSQL.
- [ ] Definir composição/quórum acadêmico **se a disciplina/grupo exigir regra adicional**. O enunciado exige todos confirmados, mas não fixa número mínimo específico.
- [ ] Testar manualmente percurso orientador/coordenador → membros internos/externos → banca agendada.

**Não criar sem necessidade:** calendário visual ou reagendamento avançado. Para mudanças antes da banca, cancelar proposta e recriar pode ser suficiente, se aceito pelo grupo.

### B11 — Avaliações: preservar avaliação externa entregue

- [x] Registro da defesa e avaliação dos professores internos.
- [x] Avaliação de externo com **token próprio e temporário**, diferente do token de convite; acesso sem conta permanente.
- [x] Nota, parecer, recomendação, média aritmética e fechamento após todas as avaliações obrigatórias.
- [x] Regra de média mínima **6,00** adotada pelo grupo, com aprovação com ressalvas se houver recomendação correspondente.
- [x] Testes específicos e suíte geral aprovados.
- [ ] Verificar e, se necessário, restringir o **CRUD administrativo legado de avaliações**, que usa regras diferentes das ações acadêmicas: só o respectivo avaliador deve alterar sua avaliação antes do fechamento, como pede o enunciado.
- [ ] Demonstrar no navegador registro da avaliação externa e bloqueio após finalização (testes automatizados já passaram).
- [ ] Validar que histórico/consulta final e eventos associados à avaliação/resultado estejam coerentes com a arquitetura escolhida.

**Importante:** o código temporário de avaliação externa é gerado pelo responsável e o link/código ainda é enviado manualmente. **O enunciado exige token temporário, não necessariamente envio automático desse token**. Já a notificação automática da **banca agendada** é exigência explícita.

### Segurança, auditoria e rotas alternativas (B04/B07/B14/B17)

- [ ] Rever acesso por objeto e **curso** no microserviço, principalmente perfis de coordenador e tentativas de alterar `curso_id`, `aluno_id` e `orientador_id` sem autoridade.
- [ ] Revisar **admin Django e CRUD legado** para que não contornem regras de aprovação, avaliação, publicação, alteração de estado ou exclusão; se necessário, torná-los somente leitura ou encaminhar aos serviços de domínio.
- [ ] Confirmar que PDF e documentos privados não podem ser baixados anonimamente nem por usuário de outro trabalho, inclusive por `/media/` ou URL direta.
- [ ] Registrar e consultar quem fez cada mudança, o que foi alterado e quando; correlacionar `HistoricoAcao`, `simple-history` e eventos com IDs que não exponham segredos.
- [ ] Verificar política de senhas, recuperação de acesso, revogação de contas/tokens, HTTPS para comunicação fora de `localhost`, CSRF e autorização dos endpoints públicos/privados.
- [ ] Documentar tratamento de senhas/chaves do `.env`, configuração de proxy e retenção/backup de arquivos e bancos.

**Critério de conclusão:** testes de acesso indevido aprovados e nenhuma rota administrativa/legada consegue contornar as regras acadêmicas essenciais.

---

## 5. Checklist da demonstração final obrigatória

Percurso sugerido, sem alterar estados manualmente no banco:

1. [ ] Administrador vincula contas acadêmicas, sem promover permissões indevidas.
2. [ ] Aluno entra, cria rascunho, associa orientador e submete PDF válido.
3. [ ] O microserviço valida hash/tamanho/formato; envio dispara evento e extração assíncrona.
4. [ ] Orientador visualiza PDF, pede ajuste, aluno reenvia e orientador aprova.
5. [ ] Orientador/coordenador propõe banca; membros internos e externos confirmam; conflito é bloqueado.
6. [ ] Banca muda para `AGENDADA`; aluno e membros recebem notificação automática pela fila.
7. [ ] Responsável registra defesa; cada avaliador interno e externo registra nota/parecer; média/resultado são calculados só após todos.
8. [ ] Trabalho com ressalvas recebe versão corrigida; termo de autorização assinado é anexado.
9. [ ] A publicação ocorre automaticamente quando todos os requisitos são cumpridos, sem liberar reprovados ou não autorizados.
10. [x] Visitante **sem login** encontra o TCC publicado por título, autor, orientador, curso, ano de defesa e palavras-chave; consegue ler/baixar o PDF final, não documentos privados. **Comprovado na API e no Chrome com fixtures B13.**
11. [ ] Dashboard mostra os cinco gráficos obrigatórios com valores verificáveis.
12. [ ] Redis é usado para sessão, lock/throttle e cache de busca; RabbitMQ tem worker funcional; teste de carga e de falha documentados.
13. [ ] Acesso administrativo fora da rede institucional é negado; consulta pública continua acessível.
14. [ ] Histórico identifica autor, ação e data/hora das principais operações.

**Estado atual da demonstração:** passos **2 e a parte de aprovação do 4 foram testados realmente**; B10/B11 têm cobertura automatizada, B12 tem testes de navegador/HTTP real e a consulta pública do passo **10** foi demonstrada no Chrome. A indexação final foi comprovada com RabbitMQ real. Ainda falta o cenário completo com notificações, Redis/cache/carga, rede institucional e os gráficos.

---

## 6. Ordem de execução para terminar sem retrabalho

| Ordem | Entrega | Dependências | Resultado verificável |
|---|---|---|---|
| **1** | **B12: implementação e testes locais feitos; falta entrega Git** | B11 já concluído | Publicação bloqueada até critérios cumpridos; arquivo final definido e validado |
| **2** | **B13: implementação e testes locais feitos; falta entrega Git** | Publicação B12 | Visitante anônimo pesquisa por 6 filtros, conteúdo indexado e baixa somente o PDF final |
| **3** | **Fila: extração, indexação e notificações** | B09/B10/B13 | Upload gera processamento fora da requisição; agenda envia avisos |
| **4** | **Redis: sessões e cache de pesquisa** | B13 | Hits/expiração/invalidação demonstrados |
| **5** | **Cinco gráficos** | Dados de banca/submissão | Dashboard com fórmulas e números testados |
| **6** | **IP/VPN, rotas legadas e auditoria** | Fluxos existentes | Controles demonstrados contra acesso indevido |
| **7** | **Testes integrados, carga e documentação** | Todos os anteriores | Roteiro de demonstração reproduzível, evidências e limitações registradas |

**Prioridade prática:** 1–3 fazem o TCC ir da submissão até o repositório e são o maior ganho funcional. Gráficos, segurança e carga continuam **obrigatórios pelo enunciado**, mesmo que possam ser paralelizados entre integrantes.

### Divisão sugerida para a equipe (ajustável)

- **Frente A — publicação e documentos:** B12, validações, versão corrigida, termo e workflow.
- **Frente B — repositório/API/frontend:** B13, busca e downloads públicos.
- **Frente C — mensageria/Redis:** extração/indexação, notificações e cache.
- **Frente D — indicadores/validação:** cinco gráficos, auditoria, IP/VPN e testes de carga.

Evitar que duas pessoas modifiquem os mesmos arquivos sem combinar contratos de API, estados e nomes de eventos.

---

## 7. O que **não** deve ser colocado como pendência de implementação novamente

- [x] Autenticação allauth e perfis acadêmicos básicos.
- [x] CRUDs principais de alunos, professores, cursos, monografias e bancas.
- [x] Criação e edição do rascunho próprio.
- [x] Upload/submissão de PDF integrado ao microserviço e consulta privada do orientador.
- [x] Aprovação do orientador e reconhecimento do estado pelo B10.
- [x] Agendamento B10 com proposta, confirmação de membros e prevenção básica de conflito.
- [x] Registro de defesa e avaliação B11 por professores.
- [x] Registro de avaliação B11 por **membros externos** com token temporário.
- [x] Cálculo de resultado e fechamento após avaliações obrigatórias.
- [x] PostgreSQL em ambos os projetos, JWT interserviços do fluxo B09 e infraestrutura Docker básica do microserviço.

**Não confundir:** “já existe” não significa que precisa ser escrito novamente; os itens de segurança, eventos e testes acima são complementações objetivas, não uma nova implementação integral.

## 8. Critério para marcar tarefas como concluídas daqui para frente

Cada linha obrigatória só deve passar para **CONCLUÍDO** quando houver:

1. Código aplicado no repositório responsável.
2. Migração necessária aplicada e `makemigrations --check --dry-run` consistente.
3. Testes específicos e suíte aplicável passando, com contagem/resultado registrados.
4. Quando envolver dois serviços, **teste real de comunicação**, não apenas `mock`.
5. Para requisitos de interface, **fluxo demonstrado no navegador**.
6. Commit e push confirmados; limitações restantes listadas explicitamente.

**Versão desta lista:** consolidada após B09/B10/B11 e atualizada com implementação e validação local B12/B13 em 22/11/2026. Commit/push dessas entregas ainda não realizados. Atualizar este documento, em vez de criar novas listas conflitantes, sempre que os colegas concluírem uma frente.
