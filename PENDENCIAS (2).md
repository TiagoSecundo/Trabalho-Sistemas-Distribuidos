# Acompanhamento do plano de refatoração

Referência: `Plano_Refatoracao_CRUD_API_Monografias.pdf`, versão de 11/11/2026.
O diagnóstico do PDF descreve o legado naquela data. Este arquivo acompanha
o código atual e distingue CRUD administrativo de processo acadêmico completo.

| Item do plano | Estado | O que falta / critério de conclusão |
| --- | --- | --- |
| B01 — baseline e backup | Parcial | Backup local preservado e entrega registrada em 11 commits na branch `feature/refatoracao-crud-monografias`; detalhes em `COMMITS.md`. Resta revisar/integrar a branch e classificar o integrante legado antes de migrar ou remover `Equipe`. |
| B02 — configuração e legado | Parcial | Settings oficial, namespaces e dependências funcionam; revisar o pacote antigo `cursodjango`, o backup SQLite rastreado e separar segredos da configuração local. |
| B03 — decisões do domínio | Parcial | Vários trabalhos por aluno e coorientador opcional implementados. Confirmar nota mínima, pesos, quórum, papéis da comissão, correções e duplicidade de PDF com o professor. |
| B04 — autenticação e autorização | Parcial | Login por sessão e restrição a staff disponíveis. Faltam django-allauth, grupos acadêmicos, titularidade por objeto e política para membros externos. |
| B05 — Aluno, Professor e Curso | CRUD pronto | Vínculos com `auth.User` são opcionais; provisionamento de contas e atribuição de papéis ainda precisam de fluxo próprio. |
| B06 — Monografia e migração | Parcial | CRUD e schema novo aplicados com proteção contra conversão incorreta. Classificação de `Equipe` e migração de uma base com monografias legadas exigem mapeamento prévio. |
| B07 — API REST | CRUD pronto | Oito recursos com validação, paginação, busca, ordenação e exclusão protegida. Filtros acadêmicos específicos e permissões por objeto ainda pendentes. |
| B08 — Banca e modelos auxiliares | CRUD pronto | Banca, participação, membro externo e avaliação têm CRUD. DocumentoComplementar e HistoricoAcao possuem apenas model/tabela, com processos pendentes em B12/B14. |
| B09 — submissão e orientação | Pendente | Submeter com requisitos completos, aprovar ou devolver com justificativa; validar ator, estado e trilha de auditoria. |
| B10 — agenda e convites | Pendente | Disponibilidade e sobreposição de horários, quórum, confirmação/recusa, tokens com expiração e concorrência transacional. Cadastro de banca não confirma agenda. |
| B11 — avaliações e resultado | Parcial | Nota de 0 a 10, parecer e recomendação no CRUD administrativo. Faltam habilitação do avaliador, realização da defesa, cálculo e fechamento conforme regra acordada. |
| B12 — documentos e publicação | Pendente | Upload de PDF, extensão/MIME/assinatura/tamanho, SHA-256 em streaming, versões, termo assinado, download autorizado e ação de publicar. |
| B13 — consultas públicas | Pendente | Catálogo apenas de monografias PUBLICADA, filtros por título/autor/orientador/curso/ano/palavras-chave e metadados públicos sem dados privados. |
| B14 — auditoria | Pendente | Registrar ator, ação, objeto, horário e detalhes nas operações relevantes; definir acesso e retenção. |
| B15 — frontend integrado | Parcial: CRUD integrado | Telas para os oito recursos consomem a API. Fluxos acadêmicos por aluno/coordenação dependem dos serviços e permissões acima. |
| B16 — PostgreSQL | Pronto localmente | Instância própria na porta 5433, migrações e testes em banco separado. Implantação produtiva pertence a outra etapa. |

## Ordem sugerida das próximas entregas

1. Confirmar as decisões acadêmicas de B03 e implementar papéis/permissões B04.
2. Implementar documentos privados e submissão/orientação, com auditoria.
3. Implementar agenda, participação confirmada e avaliação autorizada.
4. Fechar resultados, tratar correções, autorizar publicação e liberar catálogo.

Cada etapa deve ter testes de sucesso, acesso indevido, estado inválido e
concorrência quando houver disputa pelo mesmo registro. Nenhum status pode ser
avançado apenas pela edição de um campo no formulário.

Redis, Kafka/RabbitMQ, filas, extração assíncrona, microsserviços, testes de carga,
dashboards analíticos e implantação produtiva continuam fora desta fase, conforme
a seção 1.2 do plano. A proteção institucional por IP/VPN fica na etapa de
segurança/implantação, junto das permissões da aplicação.

---
## Revisão do backlog após o trabalho de autenticação (20/11/2026)

Os estados da tabela original acima descrevem a entrega do CRUD. A atualização abaixo registra o trabalho posterior **sem pressupor que todas as alterações já foram integradas à branch principal ou enviadas ao Git remoto**.

| Item | Situação revisada | Próxima verificação/ação |
| --- | --- | --- |
| B04 — autenticação e autorização | **Em implementação avançada, não concluído** | Confirmar allauth, grupos, vínculos, permissões por objeto, rotas e testes no código atual; decidir apresentação do login |
| B09 — submissão e orientação | **Pendente** | API de rascunhos não substitui submissão formal, aprovação e devolução com justificativa |
| B10 — agenda e convites | **Parcial em segurança** | Há trabalho com emissão/confirmação de token temporário; validar testes e ainda implementar agenda, disponibilidade, quórum e fluxo completo |
| B14 — auditoria | **Parcial** | Foram trabalhados sinais/registros de auditoria; verificar eventos cobertos, integridade, acesso e retenção |
| B15 — frontend integrado | **Parcial** | CRUD administrativo pronto; painel acadêmico existe em versão básica, mas integração ao layout/navbar e fluxos completos precisam confirmação |
| Restrição IP/VPN | **Retirada por decisão do projeto** | Confirmar remoção do script residual; requisito do enunciado permanece não atendido |

### Verificações prioritárias

1. Executar `python manage.py check` e `python manage.py test --keepdb --noinput`; conferir especialmente o erro anterior de `select_for_update()` em relacionamento opcional na emissão de token.
2. Confirmar com `git grep` que não há referência ativa à restrição por IP/VPN; não confundir essa remoção com desligar o `SecurityMiddleware`.
3. Validar login, permissões de staff, aluno, professor e coordenador, além do acesso indevido a objetos de outros usuários.
4. Integrar o painel acadêmico aos templates compartilhados, após decidir se haverá login único ou separado.
5. Atualizar este backlog com resultados reais de testes e o commit/hash da implementação, sem atribuir conclusões ainda não verificadas.

**Escopo inalterado:** PDF/hash, submissão formal, aprovação, cálculo de resultado, publicação, catálogo público, Redis, filas e microsserviços não devem ser marcados como concluídos com base apenas na implementação de autenticação.
