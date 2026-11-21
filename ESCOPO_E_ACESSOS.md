# Comparação do escopo e dos acessos

Revisão de 20/11/2026. Fonte: [enunciado anexado](<Trabalho_SistemasDistribuidos_Monografias (1) (2).md>), lido antes das alterações. A comparação considera o código executável deste repositório; o relatório de outro microserviço não comprova integração. O detalhamento do backlog está em [PENDENCIAS.md](PENDENCIAS.md).

## Diagnóstico anterior às alterações

`usuarios/roles.py` retornava apenas Administrador para qualquer conta com `is_staff=True`. O mesmo sinal liberava os CRUDs, menus e emissão de convites. Assim, marcar uma conta como equipe no Django ocultava seus papéis acadêmicos e concedia gestão geral. Sem staff, os papéis exigiam grupo e vínculo, mas os formulários de aluno/professor não ofereciam o campo de conta: era fácil deixar usuários sem perfil.

O painel docente mostrava apenas orientações/coorientações, ignorando participação como avaliador. A emissão externa estava restrita à administração e coordenação, embora o enunciado também atribua convites ao orientador.

## Matriz aplicada nesta revisão

Todos os papéis internos exigem conta autenticada e ativa. Os vínculos são atribuídos pela administração; o cadastro público não escolhe privilégios.

| Perfil | Origem da autorização | Tela e leitura disponíveis | Escritas disponíveis |
| --- | --- | --- | --- |
| Aluno | `Aluno.usuario` | Painel próprio, trabalhos e bancas dos próprios trabalhos | Criar/editar/excluir rascunho próprio; dono e curso definidos no servidor |
| Professor/orientador | `Professor.usuario` | Painel docente, orientações/coorientações, trabalhos em cujas bancas não canceladas participa; filtro de vínculo e lista de participações | Orientador principal pode emitir convite externo de seu trabalho quando atendidos os estados exigidos |
| Coordenador | Professor da conta indicado em `Curso.coordenador` | Painel dos cursos coordenados; pode alternar para Professor | Convites externos de trabalhos desses cursos, sujeitos às mesmas condições |
| Administrador | Superusuário ou grupo explícito `Administradores` | Painel de gestão e oito CRUDs administrativos | Cadastros e vínculos de contas; operações já existentes dos CRUDs |
| Membro externo | Token específico, temporário e válido | Tela de confirmação sem conta permanente | Confirmar a participação correspondente; o token não permite avaliar ou baixar documentos |
| Conta sem vínculo/papel | Somente identidade autenticada | Painel orientando a solicitar vínculo e `/api/usuarios/me/` | Nenhuma operação acadêmica ou administrativa |
| Público anônimo | Sem autenticação | Início, cadastro/login e entrada para confirmação de convite | Cadastro de conta sem privilégios; catálogo público ainda pendente |

`is_staff` sozinho não concede administração. `/admin/` exige também papel Administrador e mantém os requisitos de staff e permissões Django de cada model. Superusuário/grupo administrativo não apaga papéis acadêmicos coexistentes. O painel padrão prioriza Administrador, Coordenador, Professor e Aluno; somente papéis realmente disponíveis aparecem na navegação.

Vincular/remover a conta no cadastro ou trocar a coordenação altera o acesso na próxima requisição. Os grupos acadêmicos antigos são compatíveis, mas não concedem acesso isoladamente nem são necessários para um vínculo válido. Não há associação automática por nome ou e-mail. As telas e a API usam a mesma resolução; URLs e chamadas JSON diretas continuam protegidas.

## Enunciado versus implementação local

| Requisito | Situação após a revisão | Trabalho restante |
| --- | --- | --- |
| Allauth, senha protegida e perfis distintos | Login/cadastro, validação de senha, sessão e papéis por vínculo; telas próprias e bloqueio administrativo verificados | Recuperação de senha completa e identidade compartilhada entre serviços |
| Aluno cadastra trabalho e acompanha estados | Rascunhos próprios e acompanhamento implementados | Upload privado, validação PDF/tamanho (~50 MB), SHA-256, submissão, extração assíncrona e reenvio |
| Professor acompanha/aprova orientação | Leitura de orientações/coorientações e participações; convites pelo orientador implementados | Aprovação/devolução integrada, com registro de decisão e autorização do orientador |
| Coordenador ou orientador agenda após aprovação | CRUD de banca existe; leitura e convites por vínculo | Ação acadêmica de agendar para ambos; impedir agendamento prematuro, validar agenda/quórum/confirmações e notificar por fila |
| Avaliadores registram apenas suas notas/pareceres após defesa | Model/CRUD administrativo e consulta docente de participação existem | Endpoint/tela do avaliador, autoria por participação confirmada, defesa realizada e bloqueio após encerramento; o CRUD administrativo atual ainda não satisfaz essa regra |
| Resultado somente após todas as avaliações | Estados e dados de avaliação modelados | Realização, cálculo/fechamento, pesos, nota mínima, quórum e tratamento de correções |
| Externo temporário sem conta | Confirmação de convite por token com hash/expiração | Entrega automática, recusa, acesso privado ao trabalho e avaliação limitada à participação |
| Publicação após aprovação, correções e termo assinado | Estados e DocumentoComplementar modelados | Validar documentos/versões/termo e publicar automaticamente somente após todos os requisitos |
| Catálogo e API pública de publicados/cursos/orientadores | Pendente; painel privado e CRUD não equivalem ao catálogo | Consulta pública sem autenticação, filtros de título/autor/orientador/curso/ano/palavras-chave e download autorizado |
| Dashboard com indicadores | Contadores e próximas bancas por perfil | Gráficos por curso/orientador/ano, taxa de aprovação e tempo médio submissão–defesa |
| IP/VPN institucional para ações restritas | Não implementado | Atender o requisito do enunciado; a retirada anterior pela equipe não equivale a atendimento |
| Microsserviços independentes, Redis e filas | Principal Django/PostgreSQL executável; serviço separado somente relatado | Integrar identidade/dados/APIs/eventos, sessão/cache/locks, extração/notificações, idempotência, retentativas e testes distribuídos |
| Auditoria de quem/o quê/quando | Sessão, cadastro, CRUD, rascunhos e convites auditados | Consulta autorizada, mudanças de acesso no admin, retenção, diffs e correlação entre serviços |

Não foram criados botões para processos ainda ausentes. O aluno continua limitado a alterações em RASCUNHO; professor/coordenador não recebem CRUD geral como substituto de aprovação, agendamento ou avaliação próprios.

## Provisionar e verificar um acesso

1. Crie a conta em `/accounts/signup/` ou na administração de usuários.
2. Como administrador, abra `/equipe/?tipo=aluno` ou `/equipe/?tipo=professor`, crie/edite o cadastro e selecione **Conta de acesso**.
3. Para coordenador, selecione o professor em `/equipe/?tipo=curso`.
4. Entre com a conta e consulte `/usuarios/painel/` e `/api/usuarios/me/`. Professor/aluno não devem abrir `/equipe/`, `/monografias/` ou os oito CRUDs; retornar 403 é o comportamento esperado.
5. Para administradores delegados, atribua explicitamente `Administradores`. Se também precisarem do admin Django, configure staff e permissões Django; não use essa concessão para liberar um painel acadêmico.

Nenhuma migração de schema é necessária. Contas staff existentes não são promovidas automaticamente ao novo grupo. No ambiente local, a conta acadêmica identificada pelo responsável foi vinculada ao aluno e curso informados e teve staff removido, com evento de manutenção no histórico; os demais cadastros foram preservados.

## Validação

Suíte completa: **110 testes aprovados**, incluindo seis cenários Chrome e doze regressões novas de autorização. Cobertura de staff sem acesso administrativo, vínculos sem grupo, grupo sem vínculo, revogação, coordenação por curso, participação em banca, convite do orientador e cadastro → vínculo pela interface → login docente. Os testes usam banco separado; esse resultado não valida os processos distribuídos ainda pendentes.
