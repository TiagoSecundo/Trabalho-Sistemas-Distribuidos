# Acompanhamento do plano de refatoração

Revisão: **21/11/2026**. Base integrada local: `738df0c` (painéis e limpeza), `3448d33` (emissor JWT do PR #4),
com as atualizações de login, cadastro, vínculos e permissões presentes no workspace.
Referências: [enunciado do trabalho](<Trabalho_SistemasDistribuidos_Monografias (1) (2).md>),
plano original de 11/11, código atual e `docs/PENDENCIAS_ATUALIZADO.md` recebido da equipe.
A comparação do escopo está em [ESCOPO_E_ACESSOS.md](ESCOPO_E_ACESSOS.md);
o histórico de entregas e validações está em [COMMITS.md](COMMITS.md).

Este é o backlog canônico versionado. `docs/PENDENCIAS.md` é a cópia local
sincronizada; `docs/PENDENCIAS_ATUALIZADO.md` permanece como fonte recebida, sem reescrita.
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
- O enunciado anexado exige IP/VPN institucional para administração e submissões.
  A equipe havia retirado esse controle; ele continua ausente e passa a constar
  explicitamente como pendência de conformidade com o enunciado.
  `SecurityMiddleware`, CSRF e papéis não substituem a restrição de rede.
- O PR #4 adicionou um endpoint de emissão JWT com sessão, CSRF e papéis por
  vínculo. Sem chave compartilhada configurada ele responde 503. Verificação no
  microserviço, revogação, contratos e consistência de dados continuam pendentes.

## Entregas existentes — não recolocar como pendência

- `14543ac`, PR #1: modelagem, oito CRUDs, HTML/API, migrações e PostgreSQL.
- `39d076d`, `fda173a`, integrados em `9d04dc0`, PR #2: allauth, papéis,
  consultas acadêmicas, rascunhos próprios, convites externos e auditoria.
- `0178003`, integrado em `5f7857b`, PR #3: e-mail opcional e documentos da equipe.
- `b019850`, integrado em `3448d33`, PR #4: emissor JWT local, dependência
  SimpleJWT e rota `POST /api/usuarios/token-microservico/`.
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
- Login do sistema/API unificado, logout POST/CSRF e troca de conta na mesma
  sessão; cadastro público integrado, com persistência, validação e auditoria.
- Separação de administração e vínculos acadêmicos: `is_staff` sozinho não
  concede Administrador. Esse papel exige superusuário ou grupo `Administradores`;
  Aluno/Professor vêm dos respectivos vínculos, e Coordenador do Curso.
- Campo Conta de acesso nas telas de aluno/professor, com efeito imediato e
  revogação ao retirar/trocar o vínculo. Cadastro público não escolhe privilégios.
- Painel docente com orientações/coorientações, filtro por vínculo, participações
  em bancas não canceladas e convite externo emitido pelo orientador principal.
  Administração, API, menus e admin Django respeitam a separação de papéis.

## Situação por item do plano

| Item / prioridade | Estado | Entregue e critério restante |
| --- | --- | --- |
| B01 / P0 — baseline e backup | Concluído | Histórico, fontes e integrações preservados; backup local mantido. |
| B02 / P0 — configuração e legado | Concluído nesta revisão | Configuração ativa única, dependências e `.env` documentados; pacote alternativo, arquivos vazios, script/patch e documentos duplicados removidos; backup fora do Git. Migração de dados Equipe permanece em B06. |
| B03 / P0 — decisões do domínio | Parcial | Vínculos e constraints implementados. Confirmar notas, quórum, composição de banca, correções, publicação e matriz entre serviços. |
| B04 / P0 — autenticação e autorização | Parcial | Cadastro público com tela integrada, validação, conta/e-mail/auditoria atômicos e conta disponível na administração. Login do sistema/API unificado, e-mail opcional, logout POST/CSRF, sessão prioritária sobre Basic e acesso por perfil/objeto testados. Papéis acadêmicos agora vêm dos vínculos; `is_staff` não promove administrador. Emissor JWT local do PR #4 adicionado; faltam chave compartilhada no ambiente, validação/revogação no serviço, recuperação de senha completa e IP/VPN institucional. |
| B05 / P0 — Aluno, Professor e Curso | CRUD administrativo concluído; integração pendente | Models, migrações e CRUDs testados. Campo Conta de acesso disponível em Aluno/Professor (HTML/API); coordenação definida no Curso, com efeito imediato e sem exigir grupo. Definir IDs compartilhados com o microserviço. |
| B06 / P0 — Monografia e migração | Parcial | CRUD, rascunhos do dono e telas entregues. Mapear integrantes legados e definir fonte de verdade/sincronização entre o model principal e o microserviço. |
| B07 / P0 — API REST | CRUD principal concluído; integração parcial | Contratos administrativos e acadêmicos disponíveis; páginas reutilizam consultas e serviços. Conflitos de rascunhos usam a mesma tradução do CRUD. Administração exige superusuário/grupo Administradores; leitura acadêmica inclui participação docente em banca. Faltam contrato/versionamento entre serviços e autorizações das ações ainda ausentes. |
| B08 / P0 — Banca e auxiliares | Schema e CRUD concluídos; processo parcial | Banca, participação, membro externo e avaliação têm CRUD; painéis exibem bancas vinculadas. Receber evento externo não substitui agendamento seguro. |
| B09 / P0 — submissão e orientação | Pendente no principal; relatado no microserviço | Upload/submissão/aprovação/devolução constam do documento do serviço separado. Falta integração e teste com identidade real; impedir banca antes de aprovação. Rascunho não é submissão. |
| B10 / P0 — agenda e convites | Parcial | Emissão externa por Administrador, orientador principal ou coordenação do curso e confirmação por token têm API e telas. Falta agendamento autorizado ao orientador/coordenador após aprovação, entrega automática, internos, recusa, sobreposição, quórum, reagendamento, renovação e concorrência/eventos. |
| B11 / P0 — avaliação e resultado | Parcial | CRUD administrativo de notas e restrições básicas existente. Falta realização, avaliação pelo participante habilitado, cálculo e fechamento; evento de resultado no microserviço não comprova esses processos. |
| B12 / P0 — documentos e publicação | Parcial no trabalho geral; sem integração no principal | PDF/hash/integridade são relatados no microserviço. Faltam download privado, complementares, versões, correções, termo e publicação autorizada. |
| B13 / P1 — consulta pública | Pendente | Catálogo/API de PUBLICADA, endpoints públicos de cursos/orientadores, busca full-text/filtros e download autorizado. Painel privado e página inicial não são catálogo público. |
| B14 / P1 — auditoria | Parcial | Eventos de sessão, CRUD, rascunhos e convites; HTML/API acadêmicos gravam na mesma transação. Falta consulta autorizada, retenção, padronização, mudanças de papéis/admin e correlação com simple-history/eventos externos. |
| B15 / P1 — frontend | Perfis e funções existentes entregues; processo completo pendente | Quatro painéis, múltiplos papéis, busca/paginação, rascunhos e convites funcionam no navegador/celular. Professor tem orientações, filtro por vínculo e participações em bancas; conta pode ser vinculada pelas telas administrativas. Faltam telas de processo, catálogo e os cinco gráficos/indicadores do enunciado; dependem das APIs integradas. Não considerar o percurso acadêmico completo. |
| B16 / P1 — PostgreSQL | Principal local concluído | Banco e suíte isolada validados; Compose/banco do microserviço ainda não executados nesta entrega. |
| B17 / P0 — integração de microsserviços | Pendente | Integrar serviços independentes e suas APIs, autoridade de dados, consumo/revogação de JWT e reconciliação de claims/IDs, Redis (sessão, busca, lock, limites), filas/extração/notificações, entrega confiável, reconciliação, testes ponta a ponta e carga. |

## Pendências críticas confirmadas no código

1. **Agendamento sem aprovação:** o CRUD administrativo ainda permite criar Banca para monografia não aprovada. `BancaService` controla a edição pelo estado da banca, mas não valida a aprovação da orientação na criação.
2. **Avaliação sem autoria acadêmica:** o CRUD administrativo de Avaliacao ainda não exige defesa realizada nem que o autor da escrita seja o participante avaliador. O bloqueio atual verifica somente `finalizada_em` na alteração/exclusão.
3. **Caminhos alternativos:** os models registrados no admin Django não usam automaticamente os serviços de negócio nem sua auditoria. As regras de estado, exclusão e autoria devem valer também nesse acesso, sem permitir contornar os endpoints.
4. **Fluxo incompleto:** upload, submissão, aprovação, realização, resultado e publicação ainda não têm ações integradas no principal. A aprovação usada nos testes de convite é uma fixture, não uma ação disponível ao usuário.
5. **Arquitetura distribuída não demonstrada:** o serviço separado é descrito em um relatório. Não há execução conjunta comprovada com identidade, Redis, filas e serviços de banca/repositório/notificações.

## Checklist completo do que falta

Cada caixa aberta abaixo representa trabalho restante. **P0** indica bloqueio de autorização, integridade ou do percurso acadêmico; **P1** indica a próxima etapa de entrega e validação. P1 não torna opcionais os requisitos do enunciado. Os códigos B01–B17 preservam a referência do plano original. Os critérios de aceite devem ser comprovados por testes e execução do fluxo correspondente.

### 1. Decisões acadêmicas — B03 / P0

- [ ] Definir nota mínima, pesos, arredondamento, desempate e compatibilidade entre nota e recomendação de aprovação/reprovação.
- [ ] Definir composição e quórum da banca, participação do orientador/coorientador, presidente, suplente e quem precisa avaliar para permitir fechamento.
- [ ] Definir a sequência de estados e responsáveis por cada transição: submissão, análise, ajustes, aprovação, agendamento, realização, resultado, correções e publicação.
- [ ] Definir prazos de ajustes/correções, regras de reenvio, troca de orientador, limite de trabalhos ativos e preservação do histórico de bancas.
- [ ] Fixar tamanho máximo do PDF (o enunciado sugere 50 MB), política de deduplicação e tratamento de versões idênticas. O relatório do microserviço descreve bloqueio de hash repetido; confirmar a regra institucional antes da integração.
- [ ] Documentar a política de cancelamento, inativação/exclusão de cadastros, autorização de publicação, guarda de arquivos e retenção da auditoria. Preservar a proibição de excluir monografias publicadas.

**Aceite:** regras registradas na documentação de domínio e usadas nas validações e nos testes, sem decisões implícitas diferentes em cada serviço.

### 2. Identidade, contas e controle de acesso — B04/B05/B07 / P0

- [ ] Validar a emissão JWT do principal no serviço consumidor com chave compartilhada configurada, claims/IDs e papéis coexistentes; definir rotação de chave, renovação e revogação ao desativar conta ou alterar vínculo. O emissor local do PR #4 já existe; `gerar_token` manual do microserviço não substitui esse fluxo.
- [ ] Replicar nos serviços as restrições por aluno, orientador, curso e participação. Resolver como desativação da conta, troca de vínculo e perda da coordenação invalidam acessos já emitidos.
- [ ] Revisar o serviço de monografias descrito no relatório: coordenador não pode consultar indiscriminadamente todos os cursos; aluno não pode forjar autoria/curso ou trocar vínculos sem a regra correspondente.
- [ ] Completar e validar recuperação/troca de senha ponta a ponta, com telas integradas, entrega real de e-mail, expiração e uso único do link. O allauth fornece a base; o backend atual imprime e-mails no terminal.
- [ ] Implementar a restrição institucional IP/VPN exigida para a área administrativa; definir sua aplicação às rotas de submissão/gestão, considerar o proxy confiável e testar acesso permitido/negado sem bloquear o catálogo público.
- [ ] Levar autorização e regras de negócio aos caminhos do admin Django ou restringir as operações que não possam respeitá-las. Revisar também permissões diretas/grupos e auditar mudanças de acesso.

**Aceite:** contas reais usam o mesmo vínculo no principal e nos serviços; alteração de papel revoga acesso, ações indevidas são negadas também por requisição direta e o controle institucional funciona no ambiente de entrega.

### 3. Dados, legado e contratos entre serviços — B05/B06/B07/B17 / P0

- [ ] Definir a fonte de verdade de Monografia e de cada cadastro compartilhado. Evitar dois serviços alterando título, vínculo, arquivo ou estado independentemente.
- [ ] Mapear os IDs de usuário/aluno/professor/curso entre bancos e estabelecer sincronização, reconciliação e comportamento quando uma referência muda ou desaparece.
- [ ] Classificar os registros legados de Equipe e preparar migração explícita para Aluno/Professor, preservando vínculos. Só remover o model/tabelas quando o mapeamento e a validação estiverem concluídos.
- [ ] Documentar/versionar contratos REST e de eventos: campos, estados, erros, paginação, filtros, identificadores e compatibilidade entre versões.
- [ ] Completar os filtros previstos de aluno, orientador, curso, ano de defesa e palavras-chave nos recursos apropriados, respeitando o escopo de leitura de cada perfil.
- [ ] Obter/versionar o código dos serviços efetivamente usados e documentar como executá-los juntos. Definir limites e APIs dos serviços de autenticação, monografias, bancas, repositório/busca, notificações e relatórios; não basta separar apps Django.

**Aceite:** contratos reproduzíveis, referências consistentes e migração testada com dados legados; principal e serviços consultam o mesmo estado lógico do trabalho.

### 4. PDF, submissão e orientação — B06/B09/B12/B17 / P0

- [ ] Integrar upload privado de PDF pelo aluno dono, validando conteúdo/assinatura, formato, arquivo inválido e tamanho máximo; não confiar apenas na extensão do nome.
- [ ] Calcular e persistir SHA-256 por arquivo/versão, aplicar deduplicação conforme a regra definida e permitir verificar integridade, inclusive após aprovação.
- [ ] Implementar download privado autorizado por vínculo/participação; impedir acesso direto indevido pelo armazenamento ou pelas rotas de media, incluindo documentos complementares.
- [ ] Implementar submissão com arquivo válido, estado permitido, data e auditoria; impedir envio duplicado concorrente e alterações indevidas de aluno/curso/estado.
- [ ] Integrar entrada em análise, aprovação e solicitação de ajustes pelo orientador principal da monografia, sem conceder a ação a outros professores.
- [ ] Persistir o motivo dos ajustes e disponibilizar histórico e reenvio/novas versões pelas ações autorizadas. Hoje `AJUSTES_SOLICITADOS` não reabre a edição do rascunho.
- [ ] Enfileirar extração de texto e indexação, escolher a biblioteca de PDF e executar o processamento em worker; mostrar andamento/falha sem processar texto durante a requisição de upload.

**Dependências:** regras acadêmicas, identidade e fonte de verdade; processamento assíncrono depende da seção 9. **Aceite:** aluno envia PDF, acompanha o processamento e recebe aprovação/ajustes do orientador pelo sistema, sem editar estados no banco; acesso cruzado e arquivo adulterado são recusados.

### 5. Agenda, composição e convites — B08/B10/B17 / P0

- [ ] Criar ação de agendamento para orientador principal ou coordenador do curso, exigindo aprovação da orientação também no CRUD administrativo e no admin Django.
- [ ] Definir proposta de data/composição e confirmação definitiva: todos os membros exigidos devem confirmar disponibilidade antes da conclusão do agendamento.
- [ ] Validar quórum, composição, datas, duração, local/link e conflito de horários dos mesmos membros, incluindo requisições simultâneas.
- [ ] Implementar convite, aceite e recusa dos membros internos e recusa dos externos, com estados auditados e critérios de substituição de participante.
- [ ] Implementar reagendamento/cancelamento autorizado; revalidar agenda e confirmações, tratar convites/tokens antigos e impedir ações sobre a banca cancelada.
- [ ] Entregar convites e notificações por fila aos membros e ao aluno; manter reenvio e tratamento de falha de entrega.
- [ ] Completar renovação/revogação do acesso externo para o ciclo da defesa. A reemissão atual só substitui o token de confirmação ainda pendente; não representa autorização de download ou avaliação.

**Aceite:** somente trabalhos aprovados são agendados pelos responsáveis, sem conflitos de horário e com as confirmações exigidas; alteração de agenda não deixa token/convite com autorização indevida.

### 6. Avaliações, defesa e resultado — B08/B11/B17 / P0

- [ ] Implementar a realização/encerramento da defesa pelo responsável definido, com pré-condições e auditoria.
- [ ] Criar endpoints para nota, parecer e recomendação do próprio participante habilitado, após a defesa; impedir escrever em nome de outro membro.
- [ ] Disponibilizar avaliação de membro externo por credencial temporária própria e limitada à participação, sem criar conta permanente nem reutilizar indiscriminadamente o token de confirmação.
- [ ] Permitir correção da própria avaliação somente antes do fechamento; impedir alteração, exclusão ou troca de participante após o bloqueio, inclusive nos CRUDs/admin.
- [ ] Processar o evento de avaliação registrada e conferir se todas as avaliações obrigatórias chegaram antes de calcular o resultado.
- [ ] Calcular e fechar o resultado de forma atômica/idempotente segundo as regras aprovadas, atualizando banca/monografia e distinguindo aprovação, ressalvas e reprovação.
- [ ] Tratar concorrência, repetição de evento, resultado recebido fora de ordem e tentativa de finalizar sem todas as avaliações; preservar o histórico de decisões.

**Aceite:** cada membro registra apenas sua avaliação, o resultado não aparece antes do conjunto obrigatório, e não pode ser recalculado/alterado indevidamente após o fechamento.

### 7. Complementares, correções e publicação — B12/B17 / P0

- [ ] Criar APIs e serviços para ata de defesa, termo assinado de autorização, comprovante de correção e versão corrigida, com tipo, autor, data, versão, hash e validação de PDF.
- [ ] Implementar envio e validação das correções nos casos com ressalvas, mantendo versões anteriores e a decisão de aceite conforme a regra acadêmica.
- [ ] Registrar/verificar o termo de autorização assinado e definir quem valida o documento; um campo preenchido ou estado aprovado isolado não deve liberar publicação.
- [ ] Automatizar publicação somente após aprovação final, correções aceitas quando exigidas e termo válido; definir a versão do PDF destinada ao público.
- [ ] Emitir evento de publicação, atualizar o índice/cache e notificar o aluno sem produzir publicações ou mensagens duplicadas.
- [ ] Impedir exclusão/alteração indevida de trabalhos publicados em todos os caminhos; definir tratamento auditado de eventual correção administrativa ou retirada conforme política aprovada.

**Aceite:** nenhum trabalho aparece publicamente antes de cumprir todas as condições; a versão publicada corresponde ao arquivo autorizado e mantém integridade verificável.

### 8. Repositório e APIs públicas — B07/B13/B17 / P1

- [ ] Criar catálogo web e endpoint JSON sem autenticação, retornando exclusivamente monografias PUBLICADA.
- [ ] Oferecer busca/filtros por título, autor, orientador, curso, ano de defesa e palavras-chave, com ordenação e paginação; integrar o texto extraído à indexação full-text.
- [ ] Criar endpoints públicos de cursos e orientadores, com campos de exibição adequados; não abrir os CRUDs administrativos para visitantes.
- [ ] Implementar detalhe e download público somente da versão autorizada, sem expor rascunhos, avaliações ou documentos privados.
- [ ] Atualizar/remover resultados e invalidar caches quando publicação ou dados indexados mudarem, evitando conteúdo desatualizado e vazamento entre consultas privadas/públicas.

**Aceite:** visitante sem login encontra e baixa somente trabalhos publicados; todos os filtros do enunciado funcionam na tela e na API e a leitura continua pública fora da rede institucional.

### 9. Redis, filas e notificações — B09/B10/B11/B13/B17 / P0–P1

- [ ] Configurar e validar Redis para cache de sessões e resultados de busca, com chaves, expiração, invalidação e comportamento definido durante indisponibilidade.
- [ ] Integrar lock de upload/processamento e limite de taxa de submissões; validar expiração, recuperação de falha, liberação do lock e reenvios simultâneos.
- [ ] Escolher/configurar o broker do conjunto de serviços (o relatório usa RabbitMQ) e documentar filas, eventos, produtores, consumidores e versionamento.
- [ ] Conectar eventos reais de submissão, extração/indexação, aprovação, agendamento, avaliação e publicação, com usuário/objeto e identificador de correlação.
- [ ] Garantir entrega após confirmação da transação, com outbox ou mecanismo equivalente, retentativas e reconciliação. O relatório descreve falha de publicação apenas registrada em log.
- [ ] Garantir consumo idempotente por ID de evento, tratamento de ordem, mensagens inválidas e fila de falhas (DLQ); checar somente o estado final não é suficiente.
- [ ] Implementar envio assíncrono de convites/alertas e mensagens ao orientador, membros e aluno nos eventos previstos; configurar transporte real de e-mail e acompanhamento de falhas.
- [ ] Monitorar workers/consumidores e testar falha do Redis, broker, extração ou transporte de e-mail sem perder estados ou deixar uploads permanentemente bloqueados.

**Aceite:** processamento ocorre fora da requisição, notificações são efetivamente entregues e falhas/repetições podem ser recuperadas sem duplicar resultados. O Redis descrito no microserviço ainda não comprova sessão/cache do principal.

### 10. Indicadores e dashboards — B15/B17 / P1

- [ ] Definir fórmulas, denominadores, período e tratamento de registros sem data, cancelados ou ainda não concluídos.
- [ ] Criar endpoints de estatísticas e gráficos de monografias por curso, orientador e ano de defesa.
- [ ] Exibir taxa de aprovação e tempo médio entre submissão e defesa com base nos eventos/datas reais.
- [ ] Restringir agregações ao escopo do usuário e integrar o serviço de relatórios, quando adotado, aos demais dados/APIs.

**Aceite:** os cinco indicadores exigidos pelo enunciado têm gráficos e valores verificáveis; os contadores atuais dos painéis não são tratados como implementação desses indicadores.

### 11. Telas que ainda faltam — B15 / P0–P1

- [ ] Aluno: upload, progresso de extração, submissão, ajustes/reenvio, correções e envio dos documentos complementares.
- [ ] Professor/orientador: análise do PDF, aprovação/devolução com motivo e agendamento autorizado de seus trabalhos.
- [ ] Coordenador: agenda, composição/quórum, confirmações, conflitos, reagendamento/cancelamento e acompanhamento do resultado dos cursos coordenados.
- [ ] Avaliador interno: confirmação/recusa de convite, leitura autorizada e formulário da própria avaliação com bloqueio após fechamento.
- [ ] Membro externo: acesso temporário ao trabalho e avaliação, além da confirmação já existente, com estados de expiração/revogação e sem conta permanente.
- [ ] Público: busca, filtros, detalhe e download das monografias publicadas; administração: consulta de auditoria e processos pendentes de gestão.
- [ ] Integrar essas telas às APIs efetivas, com CSRF/autorização, erros de validação, sessão expirada, carregamento, uso por teclado e adaptação ao celular; incluir gráficos da seção 10 e recuperação de senha da seção 2.

**Aceite:** cada perfil conclui suas ações pelo navegador; não há botões sem backend nem acesso ampliado ao CRUD administrativo como substituto das ações acadêmicas.

### 12. Histórico e rastreabilidade — B14/B17 / P1

- [ ] Completar auditoria de mudanças de conta/vínculo/permissão, upload, aprovação, agenda, avaliações, resultado, correções e publicação, incluindo operações do admin Django.
- [ ] Registrar quem, o que mudou e quando, com referência padronizada de objeto, campos relevantes alterados e correlação entre serviços; não registrar senha, token ou credenciais.
- [ ] Criar consulta/tela de histórico com filtros e autorização, regras de retenção e proteção contra alteração indevida dos registros.
- [ ] Relacionar o HistoricoAcao do principal ao histórico/eventos dos outros serviços e registrar a identidade limitada do participante externo sem inventar uma conta permanente.

**Aceite:** é possível reconstruir as mudanças de um trabalho entre serviços e identificar o autor, preservando sigilo e consistência entre a escrita e o evento de auditoria.

### 13. Testes, escalabilidade e execução — B01/B07/B14/B16/B17 / P0–P1

- [ ] Implementar testes automatizados nos serviços separados; o relatório recebido aponta apenas esqueleto de testes no serviço de monografias.
- [ ] Cobrir autorização por objeto/curso/participação, recuperação de senha, IP/VPN, arquivo inválido/grande/adulterado/duplicado e proteção de download.
- [ ] Cobrir fluxo de estados, agendamento antes da aprovação, conflitos simultâneos, quórum, avaliação de outro membro, fechamento prematuro e publicação sem correção/termo.
- [ ] Testar concorrência e falhas/repetições/ordem de eventos, expiração/revogação de tokens, indisponibilidade de Redis/broker e recuperação das filas de erro.
- [ ] Executar o percurso completo com contas de cada perfil e membro externo: rascunho → PDF/submissão → orientação → banca → avaliações → correções/termo → publicação → consulta anônima.
- [ ] Subir e validar os serviços e seus bancos em conjunto, migrações, dados mínimos, APIs, workers e endpoints de saúde; incluir broker/consumidor na avaliação operacional, além de banco/Redis.
- [ ] Realizar teste de carga para milhares de visitantes simultâneos do repositório, medindo latência, erros, consultas ao banco, uso do cache e atraso das filas; registrar ambiente e resultado reproduzível.
- [ ] Documentar execução Linux, configuração por ambiente, versões de serviços/contratos, variáveis sem segredos, HTTPS/proxy, backups de bancos/PDFs e teste de restauração. O backup local preservado não comprova recuperação do conjunto distribuído.
- [ ] Consolidar a documentação e o roteiro de demonstração final com os serviços efetivamente executados, resultados de testes e limitações ainda abertas.

**Aceite:** ambiente reproduzível e fluxo integrado testado, com evidências de carga e recuperação de falhas. A suíte do principal não substitui esses testes distribuídos.

## Ordem sugerida de entrega

| Etapa | Pendências relacionadas | Saída verificável |
| --- | --- | --- |
| 1. Fechar regras e contratos | Seções 1–3 | Matriz de ações/estados, dados e identidade definidos; correção dos caminhos administrativos que contornam regras |
| 2. Preparar comunicação e arquivos | Seções 2–4 e 9 | Autenticação entre serviços, PDF privado, hash, Redis e workers operacionais |
| 3. Completar orientação | Seções 4 e 11 | Aluno submete e orientador aprova/devolve pela interface |
| 4. Completar banca e resultado | Seções 5–6 e 11 | Agenda válida, convites/aceites, defesa, avaliações próprias e fechamento correto |
| 5. Publicar e consultar | Seções 7–9 e 11 | Termo/correções, publicação automática e catálogo/API públicos com cache |
| 6. Concluir indicadores e evidências | Seções 10, 12–13 | Gráficos, histórico, testes integrados, carga e roteiro de execução |

Auditoria, autorização e testes acompanham cada entrega; a última etapa consolida a validação do conjunto. Os códigos B01–B17 e as caixas deste checklist devem ser atualizados à medida que cada critério for demonstrado.

## Microserviço — implementação relatada no documento recebido

| Área | Evidência localizada | Limite atual |
| --- | --- | --- |
| API REST de monografias | `MonografiaViewSet`, CRUD e filtros por status, curso, aluno, orientador; busca por título, resumo e palavras-chave | Banco/modelo separados do principal; regras de acesso precisam ser revisadas |
| Autenticação de chamadas | `JWTStatelessUserAuthentication` do SimpleJWT; claims `role`, `aluno_id`, `professor_id` | O principal agora tem emissor JWT ligado à sessão allauth; não há consumo/validação ponta a ponta demonstrados no microserviço. O comando `gerar_token` ainda é só desenvolvimento |
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

## Validação do código e limites desta atualização

Após o merge do PR #4, a suíte completa passou com **115 testes**, incluindo
seis cenários Chrome e cinco novos testes do emissor JWT,
no banco isolado `test_curso_django_dev`, sem testes ignorados. Os doze novos
casos de `usuarios/test_papeis.py` cobrem staff sem privilégio administrativo,
Aluno/Professor, grupos isolados, administrador explícito, revogação de vínculos,
coordenação por curso, participação em banca, convites e vínculo pela tela.
O Chrome cobre também cadastro público → vínculo de professor pela API do
formulário administrativo → logout/login → painel docente, além de responsividade.

Esta atualização detalha o backlog; não implementa nem valida os itens abertos.
Foi feita conferência documental com o enunciado, as rotas, os serviços e as
configurações locais. A suíte foi repetida após integrar o JWT do PR #4; a
edição final deste arquivo não altera o comportamento da aplicação.

A suíte mantém login, cadastro, rascunhos, CSRF, auditoria/rollback, migrações e
restrições dos CRUDs. O cenário de troca de conta usa professor marcado como
staff para reproduzir a causa original. Isso não comprova os processos
acadêmicos e a integração distribuída ainda pendentes.

## Decisões e itens externos à entrega

IP/VPN foi retirado anteriormente pela equipe, mas é exigido no enunciado
anexado. A restrição institucional permanece pendente e não é proteção ativa. Redis/RabbitMQ aparecem no relatório do serviço separado, sem integração comprovada.
O emissor JWT foi integrado ao principal, mas o consumo entre serviços não foi validado. Extração de PDF, repositório público, testes
de carga e implantação produtiva continuam sem comprovação nesta cópia.
O PDF original e os documentos de referência recebidos foram preservados.
