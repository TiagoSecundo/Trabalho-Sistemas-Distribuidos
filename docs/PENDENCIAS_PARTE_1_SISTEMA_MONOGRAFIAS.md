# Sistema de Monografias — Pendências da Parte 1

**Disciplina:** Sistemas Distribuídos — Prof. Alessandro Vivas Andrade  
**Escopo exclusivo:** **Parte 1 — Autenticação, Submissão e CRUD**  
**Atualização:** 22/11/2026  
**Objetivo:** acompanhar a implementação e as evidências da Parte 1, preservando o histórico de B09–B13.

**Fechamento técnico:** P1-01 a P1-09 implementados e comprovados localmente. A demonstração usa a rede local escolhida pelo usuário e SMTP de testes. A entrega Git está registrada em `COMMITS.md`; requisitos exclusivos da Parte 2 continuam separados.

> **Reconciliação em 22/11/2026:** B12 e B13 conferidos no código e nos testes; entrega `2fb7743`, integrada à `main` pelo merge `efb12ce`. Essa foi a situação inicial; as pendências restantes foram implementadas no principal em `affafe4` (já presente no remoto da branch). No microserviço, `a171803`/`b9dd9bb` foram integrados pelo merge local `9ee83f6`. Consulte `COMMITS.md` para o fechamento e a entrega remota.
>
> **Fontes de conferência históricas:** enunciado original do professor, código disponibilizado em `Trabalho SC(4).zip`, alterações B09/B10/B11 aplicadas posteriormente e resultados dos testes informados na conversa. Não houve uma nova auditoria independente dos commits posteriores feitos por outros integrantes.
>
> **Regra de acompanhamento:** marcar **CONCLUÍDO** somente depois de implementação, testes e — quando necessário — funcionamento real entre os serviços. Distinguir **falta implementar** de **falta verificar**.

## 1. Resumo rápido

| Frente | Estado | Situação objetiva |
|---|---|---|
| Autenticação `django-allauth`, contas e perfis | **CONCLUÍDO** | Validadores, recuperação SMTP/Chrome, cinco perfis e auditoria verificados |
| Modelos e CRUDs principais | **CONCLUÍDO** | Cadastros administrativos editáveis; escritas acadêmicas somente pelas ações autorizadas |
| **B09 — Rascunho, PDF e aprovação do orientador** | **CONCLUÍDO** | Chrome/HTTP: ajustes, duas versões e recuperação após resposta perdida, sem duplicação |
| **B10 — Proposta/agendamento de banca** | **CONCLUÍDO** | Confirmações reais e três avisos entregues via RabbitMQ/SMTP |
| **B11 — Avaliações internas e externas** | **CONCLUÍDO** | Avaliações no Chrome, média 8,50, bloqueios de fechamento e CRUD alternativo |
| **B12 — Correções, termo e publicação** | **CONCLUÍDO** | Documentos privados, conferência, integridade e publicação automática implementados e testados |
| **B13 — Pesquisa pública do repositório** | **CONCLUÍDO** | Catálogo anônimo, seis filtros, detalhe e PDF final; API pública também entregue |
| **Extração assíncrona do PDF** | **CONCLUÍDO** | Microserviço extrai cada submissão; principal mantém índice público final separado |
| **Integridade, IP/VPN e auditoria** | **CONCLUÍDO no ambiente aprovado** | Hash na leitura/aprovação, rede configurável, proxies controlados e auditoria com identidade |

**Evidências atuais B12/B13:** suíte principal com **216 testes encontrados, 201 aprovados e 15 opcionais ignorados**; testes opcionais B13 com RabbitMQ real (**3**) e navegador (**2**) aprovados; B12 com navegador (**2**) e HTTP real ao microserviço (**2**) aprovados. Os testes opcionais são executados separadamente. Detalhes em `DESENVOLVIMENTO.md`.

**Evidências históricas já obtidas:** sistema principal: **163 testes encontrados, 157 aprovados e 6 ignorados**; microserviço: **6/6 testes aprovados**. Na operação real, aluno enviou PDF e orientador consultou/aprovou. O envio do B09 foi confirmado nos dois repositórios. Esses testes **não** comprovam as partes ainda pendentes.

---

## 2. Pendências de implementação obrigatória — Parte 1

### P1-01 — Correções, termo assinado e publicação automática (**prioridade máxima**)

**Exigência do professor:** publicar somente depois da aprovação final da banca, entrega da versão corrigida **quando houver ressalvas** e existência do **termo de autorização de publicação assinado**.

**Aproveitar:** modelos `Monografia`, `DocumentoComplementar`, tipos `VERSAO_CORRIGIDA` e `TERMO_AUTORIZACAO`, estados `APROVADA`, `APROVADA_COM_RESSALVAS`, `CORRECOES_ENTREGUES` e `PUBLICADA`; resultado do B11.

**CONCLUÍDO — entrega `2fb7743`, merge `efb12ce`:**

- [x] Permitir ao aluno **anexar a versão corrigida** quando a banca determinar ressalvas.
- [x] Permitir anexar o **termo de autorização de publicação assinado**, identificando responsável e data.
- [x] Definir e implementar como será registrada a **conferência das correções**, se necessária para considerar a versão final aceita; a disciplina não especifica quem confere.
- [x] Validar arquivos e sua integridade, preservar a versão final e impedir que documentos privados sejam expostos por engano.
- [x] Criar **serviço de publicação automática**, disparado quando todas as pré-condições forem satisfeitas (não depender apenas de um administrador alterar o status manualmente).
- [x] Impedir publicação de monografia **reprovada**, sem termo ou sem correção obrigatória.
- [x] Registrar `PUBLICADA`, data de publicação e o PDF definitivo; bloquear edição/exclusão posterior da monografia publicada.
- [x] Registrar ações relevantes no histórico/auditoria.

**Critério de aceite:** demonstrar três situações: (1) aprovada sem ressalvas + termo → publica; (2) aprovada com ressalvas + correção + termo → publica; (3) reprovada ou documentação incompleta → **não** publica. Confirmar via interface e API/serviços, com testes automatizados.

**Não acrescentar sem necessidade:** assinatura digital criptográfica. O enunciado exige termo **assinado**, mas não determina tecnologia de assinatura digital.

### P1-02 — Repositório público pesquisável (**prioridade máxima**)

**Exigência do professor:** qualquer visitante deve consultar somente monografias **publicadas**, sem login, pesquisando por **título, autor/aluno, orientador, curso, ano de defesa e palavras-chave**.

**CONCLUÍDO — entrega `2fb7743`, merge `efb12ce`:**

- [x] Criar página pública de pesquisa, listagem e detalhes, acessível anonimamente.
- [x] Implementar **todos os seis filtros**: título, autor, orientador, curso, **ano da defesa** e palavras-chave.
- [x] Exibir **somente** monografias com status `PUBLICADA`.
- [x] Disponibilizar visualização/download do **PDF final publicado**, sem expor rascunhos, versões anteriores, pareceres ou termo de autorização.
- [x] Garantir que visitantes não alterem dados nem acessem PDFs privados por URL direta.
- [x] Testar filtros individualmente e em combinação, resultados vazios, acesso sem autenticação e tentativa de acessar trabalho não publicado.

**Critério de aceite:** em janela anônima, um visitante encontra um TCC publicado por cada um dos seis critérios e acessa apenas seu PDF final. Monografia não publicada não aparece nem pode ser baixada.

**Limite do escopo:** a **página pública e sua pesquisa são da Parte 1**. Os **endpoints públicos JSON** de monografias, cursos e orientadores são detalhados na **Parte 2**. Pode ser eficiente construí-los juntos, mas não confundir o que pertence a cada etapa.

### P1-03 — Extração de texto do PDF de forma assíncrona (**obrigatória na Parte 1**)

**Exigência literal do enunciado:** a extração do texto do PDF para indexação deve ser feita **via fila de eventos, e não durante a requisição de upload**.

**Aproveitar:** upload, validações do PDF, hash SHA-256, RabbitMQ e infraestrutura de consumidor existentes no microserviço.

**CONCLUÍDO — implementação e evidências em `DESENVOLVIMENTO.md`, seção Parte 1:**

- [x] Após submissão bem-sucedida, emitir evento de trabalho para extração do texto.
- [x] Criar/adaptar consumidor que obtenha o PDF de forma segura e execute a extração **fora da requisição HTTP**.
- [x] Guardar o texto extraído ou um índice utilizável pela pesquisa, associando-o à monografia/versão corretas.
- [x] Registrar estado/erro do processamento; impedir que falha de extração invalide ou bloqueie indevidamente um upload já aceito.
- [x] Evitar processamento duplicado indevido e comprovar que uma nova versão é processada corretamente.
- [x] Testar PDF válido, PDF sem texto extraível, erro temporário de processamento e repetição de evento.

**Critério de aceite:** o upload responde sem executar a extração; um worker consome o evento e processa o PDF depois. É possível mostrar essa sequência nos logs e consultar o texto/índice resultante.

**Atenção:** embora o uso de RabbitMQ e a arquitetura de eventos sejam aprofundados na Parte 2, **a extração assíncrona já está expressamente exigida na Parte 1**.

### P1-04 — Notificações automáticas após agendar a banca (**obrigatória na Parte 1**)

**Exigência do professor:** após o agendamento, notificar **automaticamente, via fila de eventos**, todos os membros da banca e o aluno.

**Aproveitar:** B10 já controla propostas `PENDENTE`, confirmações de professores e externos e passagem para `AGENDADA`.

**CONCLUÍDO — implementação e evidências em `DESENVOLVIMENTO.md`, seção Parte 1:**

- [x] Emitir evento apenas quando a banca se tornar efetivamente `AGENDADA` (não na proposta pendente).
- [x] Processar evento no consumidor e produzir notificações ao aluno e **todos os membros**.
- [x] Incluir dados necessários: trabalho, data/hora, modalidade, local/link e destinatários adequados.
- [x] Registrar falhas e evitar notificações duplicadas em caso de reprocessamento.
- [x] Testar destinatários, não envio antes das confirmações e comportamento quando a fila estiver temporariamente indisponível.

**Critério de aceite:** realizar um agendamento real, verificar a publicação e o consumo do evento e comprovar que aluno e membros receberam o aviso pelo canal definido pelo grupo.

**Importante:** enviar **manualmente** o token de confirmação/avaliação ao membro externo é uma limitação conhecida, mas não é a mesma exigência. O envio **automático do aviso de banca agendada** é expressamente obrigatório.

---

## 3. Pendências de segurança, CRUD e qualidade — completar ou comprovar

Estas tarefas **não significam refazer B09, B10 ou B11**. São verificações e correções específicas para cumprir regras expressas da Parte 1.

### P1-05 — Controle de acesso à área administrativa por IP/VPN

- [x] Restringir acesso à **área administrativa** a partir da rede institucional (IP/VPN), como exige o enunciado.
- [x] Definir o perímetro protegido (`/admin/` e eventuais rotas administrativas equivalentes), considerando proxy reverso e cabeçalhos confiáveis.
- [x] Testar acesso autorizado na rede e acesso bloqueado fora dela.
- [x] Manter **a pesquisa do repositório público acessível sem login** e sem exigência de IP institucional.

**Configuração aprovada pelo usuário:** variável no `.env`, rede local `192.168.3.188/24` (normalizada para `192.168.3.0/24`) e loopback para testes.

**Estado:** concluído. Middleware protege admin, CRUD HTML/REST e sessões administrativas; testes cobrem rede permitida, externa, lista vazia, proxy confiável e cabeçalho forjado. Catálogo público permanece acessível.

### P1-06 — Permissões de CRUD, avaliações e proteção contra exclusão

- [x] Revisar **Django Admin, CRUD administrativo legado e APIs** para impedir caminhos que contornem os serviços de domínio.
- [x] Garantir que **somente o próprio avaliador** possa atualizar sua avaliação, **antes do fechamento do resultado**, como diz o professor. Revisar principalmente o CRUD administrativo genérico.
- [x] Garantir que rascunhos sejam editáveis apenas por seus responsáveis e que bancas só sejam alteradas **enquanto ainda não realizadas**, respeitando confirmação/convites já enviados.
- [x] Garantir exclusão apenas para usuários autorizados e **nunca exclusão de monografias publicadas**.
- [x] Conferir permissões por objeto/curso, inclusive em chamadas ao microserviço; impedir alterações indevidas de aluno, orientador ou curso por parâmetros enviados pelo cliente.
- [x] Criar testes de autorização para perfis distintos, objetos de outro usuário e rotas alternativas.

**Estado:** concluído. Admin e CRUD genérico acadêmico são de consulta; rascunhos/B10/B11 usam as ações dos responsáveis. Cadastros básicos permanecem editáveis. Microserviço verifica objeto, curso e vínculos assinados.

### P1-07 — Integridade do arquivo após aprovação

- [x] Comprovar que SHA-256 é calculado e armazenado para o PDF submetido, associado à versão correta.
- [x] Implementar/verificar comparação do hash em operação de leitura/publicação ou outra rotina definida, de forma a **detectar alteração não autorizada após aprovação**.
- [x] Impedir substituição silenciosa do arquivo aprovado; uma versão corrigida deve manter seu próprio registro/identidade e hash.
- [x] Testar manipulação de arquivo e detecção de divergência.

**Estado:** concluído. Hash conferido na aprovação/download do original e leitura/publicação do PDF final; versões preservadas. Testes adulteram arquivos e comprovam bloqueio.

### P1-08 — Políticas de senha, auditoria e painel por perfil

- [x] Verificar as regras de senha do Django/allauth e o fluxo de criação/recuperação, sem substituir a autenticação existente.
- [x] Demonstrar login e permissões dos cinco perfis: administrador, coordenador, professor/orientador, aluno e **membro externo por token temporário**, sem conta permanente.
- [x] Conferir que o histórico identifica **quem fez, o que fez e quando** nas ações administrativas, upload/submissão, aprovação, agendamento e avaliações.
- [x] Registrar também, quando implementados, correções, termo e publicação; evitar guardar JWT, códigos temporários e senhas no histórico.
- [x] Verificar a página principal e os **painéis personalizados por perfil** previstos na Parte 1.

**Estado:** concluído. Cadastro, recuperação de senha e perfis exercitados; auditoria de cadastros administrativos e exclusão complementada, mantendo o ID original. O dashboard personalizado da Parte 1 não equivale aos **cinco gráficos estatísticos**, exigidos na Parte 2.

### P1-09 — Fechamento e demonstração do B09/B10/B11

- [x] Demonstrar no navegador **pedido de ajustes pelo orientador, edição e reenvio** do PDF. Esses casos já passaram nos testes automatizados.
- [x] Confirmar que a aprovação real do orientador coloca a monografia no estado reconhecido pelo B10 e libera a proposta de banca, sem intervenção manual no banco.
- [x] Demonstrar proposta, confirmação de participantes internos e externos, ausência de conflito e agendamento efetivo.
- [x] Demonstrar avaliação do membro **externo com token específico de avaliação**, além de avaliação dos professores, média/resultado somente após todas e bloqueio posterior.
- [x] Testar negativa de acesso a monografias/PDFs de outro usuário, token inválido/expirado e acesso público somente ao material publicado.
- [x] Conferir que o banco/arquivos permanecem consistentes após falha temporária de comunicação entre serviços.

**Estado:** concluído. Roteiro automatizado no Chrome com HTTP/JWT, RabbitMQ e SMTP reais, aguardando o término real da defesa. Teste adicional interrompe a resposta de submissão e comprova recuperação sem duplicar a versão remota.

---

## 4. O que já está feito e NÃO deve voltar como tarefa de desenvolvimento

- [x] Estrutura Django, PostgreSQL e autenticação com django-allauth.
- [x] Perfis acadêmicos básicos e membro externo com acesso por token temporário.
- [x] Modelos principais (Aluno, Professor, Curso, Monografia, Banca, Avaliação e Documento Complementar).
- [x] CRUDs principais e criação/edição de rascunhos.
- [x] Upload de PDF com validação de tipo/tamanho, SHA-256 e integração com o microserviço.
- [x] Aprovação do orientador no sistema principal com comunicação real ao microserviço.
- [x] B10: proposta de banca, confirmação interna/externa, conflitos e agendamento.
- [x] B11: notas, pareceres, recomendações, avaliações internas e externas, cálculo e fechamento.
- [x] Infraestrutura RabbitMQ, consumidor real de extração no microserviço e avisos de banca no principal, com outbox, retentativas e DLQ.

### Evidências de teste que o grupo pode citar

| Projeto | Resultado registrado |
|---|---|
| Principal após B09 | 163 testes, **157 aprovados / 6 ignorados / 0 falhas** |
| Microserviço após B09 | **6 testes aprovados / 0 falhas** |
| B10 | **12 testes específicos aprovados** |
| B11 — avaliação externa | **13 testes específicos aprovados** |
| Comunicação real | Aluno enviou PDF, orientador acessou e aprovou pelo navegador |

**Evidências finais da Parte 1:** regressão principal com Chrome/RabbitMQ/HTTP: **226 encontrados, 224 aprovados e 2 cenários P1 separados**; esses 2 passaram com serviços reais, assim como um terceiro cenário adicionado de perda de resposta HTTP. Descoberta atual: **227 testes**. Microserviço: **20 testes aprovados**. As capturas e os comandos constam em `DESENVOLVIMENTO.md`.

**Limites das evidências:** rede local de demonstração, PDFs/termos fictícios, SMTP local sem retransmissão externa. A perda de confirmação SMTP pode causar duplicação em uma tentativa futura; o registro por destinatário evita reenviar entregas já confirmadas. Sem OCR, cache de busca/sessões, gráficos ou teste de carga nesta etapa.

---

## 5. Ordem executada e divisão originalmente sugerida

| Ordem | Entrega | Depende de | Responsabilidade sugerida |
|---|---|---|---|
| **1** | **P1-01 Publicação e documentos** | B11 (pronto) | Integrante A: regras, modelos/arquivos e testes |
| **2** | **P1-02 Repositório público** | Estado `PUBLICADA` da entrega 1 | Integrante B: filtros, página e permissões |
| **3** | **P1-03 Extração assíncrona** | B09 e RabbitMQ existentes | Integrante C: evento, worker, indexação básica |
| **4** | **P1-04 Avisos de banca agendada** | B10 e RabbitMQ existentes | Integrante C: evento, consumidor e teste |
| **5** | **P1-05 a P1-08 Segurança e CRUD** | Fluxos e rotas atuais | Integrante D: revisão de acesso e auditoria |
| **6** | **P1-09 Demonstração final** | Entregas anteriores | Todos: testar e registrar evidências |

As frentes acima foram encerradas nesta revisão. O texto privado das submissões está no microserviço; o índice público pertence à versão final publicada no principal.

## 6. Checklist de demonstração da Parte 1

- [x] Administrador consegue cadastrar/vincular contas, com permissões corretas.
- [x] Aluno cria rascunho, associa orientador e envia PDF; formato, tamanho e SHA-256 são validados.
- [x] Upload dispara **extração assíncrona**, sem aguardar a extração na requisição HTTP.
- [x] Orientador consulta PDF, solicita ajustes ou aprova; aprovação habilita o B10.
- [x] Orientador/coordenador propõe banca; todos confirmam; conflitos são bloqueados.
- [x] Após `AGENDADA`, aluno e membros são **notificados via fila**.
- [x] Professores e membros externos avaliam; resultado só é calculado após todas as avaliações obrigatórias.
- [x] Se houver ressalvas, versão corrigida é entregue; termo assinado é anexado.
- [x] Publicação ocorre **automaticamente** somente com todos os requisitos satisfeitos.
- [x] Visitante anônimo pesquisa monografias publicadas pelos **seis filtros** e acessa apenas PDF final.
- [x] Monografia publicada não pode ser excluída; avaliador não altera avaliação após fechamento.
- [x] Hash detecta alterações indevidas após aprovação; administrador é barrado fora da rede IP/VPN institucional.
- [x] Auditoria mostra usuário, ação e data/hora; perfis veem seus respectivos painéis.

---

## 7. Delimitação: exigências da Parte 2 (não incluir como pendência exclusiva da Parte 1)

O professor detalha na **Parte 2 — REST API com Django REST Framework**:

- Endpoints públicos **JSON** de monografias publicadas, cursos e orientadores; CRUD REST restrito.
- Arquitetura de microsserviços e APIs independentes (embora parte da infraestrutura já seja utilizada para cumprir a Parte 1).
- Redis para **cache de sessões**, **cache de resultados de pesquisa**, controle de uploads em andamento e *rate limiting*.
- Fluxos adicionais de eventos e integração de serviços.
- Estratégias específicas de escalabilidade e suporte a milhares de visitantes simultâneos.
- **Cinco gráficos estatísticos:** por curso, por orientador, por ano, taxa de aprovação e tempo médio submissão–defesa.
- Frontend JavaScript consumindo a API e requisitos detalhados de histórico de alterações.

**Atenção às dependências cruzadas:** a **pesquisa pública**, a **extração assíncrona** e os **avisos automáticos por fila** pertencem explicitamente à **Parte 1**, mesmo que usem tecnologias discutidas novamente na Parte 2. Não adiar esses três itens apenas por envolverem RabbitMQ.

---

## 8. Critério para marcar a Parte 1 como concluída

1. Todas as tarefas de implementação **P1-01 a P1-05** cumpridas e testadas; verificações **P1-06 a P1-09** encerradas e eventuais falhas corrigidas.
2. Testes automatizados específicos e suíte completa dos dois projetos aprovados; migrações consistentes.
3. Fluxo real entre serviços demonstrado, sem depender apenas de mocks.
4. Publicação bloqueada quando faltarem termo/correção/aprovação; busca anônima mostra somente TCCs publicados.
5. Acesso externo por token e controle IP/VPN administrativo demonstrados.
6. Commits e *push* documentados para ambos os repositórios, com a versão efetivamente usada pelo grupo.

**Entrega Git concluída:** o commit principal `affafe4` foi preservado e integrado à `main` pelo merge `f983206`, enviado ao GitHub. O microserviço também teve sua `main` publicada em `9ee83f6`. Ambos os pushes foram aceitos, sem sobrescrever o histórico. O item 6 de entrega ao grupo está encerrado; este registro documental também acompanha a `main` do principal.

**Recomendação:** manter este documento como referência da **Parte 1**. Quando um colega concluir uma tarefa, marcar a caixa, acrescentar o commit e um teste/evidência, em vez de abrir uma nova lista de pendências.
