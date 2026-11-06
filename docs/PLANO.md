# Plano de Execução — Corretor RPA

> **Status em 2026-11-06:** etapa 0 concluída. O Bradesco já tem adapter da
> **API oficial** de Propostas Pendentes (OAuth2/JWT), fallback HTML com sessão
> assistida, renovação/login automático e **Parcelas em Atraso** atrás de flag;
> o manifest segue `discovery` e o onboarding comercial da API está em
> **standby**. O painel já cobre workflow, planilha/CSV, scheduler e `/health`.
>
> **Próximo marco:** fechar o **Bradesco em produção assistida** e endurecer
> segurança/LGPD antes de ampliar a cobertura. Adicionar a Allianz agora
> aumentaria a superfície de falha sem antes provar a operação diária do único
> portal real.

## Princípios

- Entregas **verticais**: cada etapa termina com algo funcionando de ponta a
  ponta (coleta → banco → painel), não apenas camadas isoladas.
- **Uma seguradora estável em produção antes de iniciar a próxima.**
- **Segurança e LGPD antes de expor o painel** para a equipe ou para a rede.
- Falha de coleta **nunca** vira lista vazia; resultados parciais são visíveis.
- Toda etapa termina com **demo + testes + documentação**.
- Nenhuma credencial real entra no repositório, em chats ou em logs.
- Até a validação de cada portal, o desenvolvimento usa **dados demo fictícios**.
- Primeiro em **modo sombra** (coleta real comparada ao processo manual), depois
  em produção assistida.

## Visão das etapas

| Etapa | Entrega | Estimativa | Estado |
|---|---|---|---|
| 0 | Fundação: Clean Architecture + plugins + adapter demo + painel + testes | 1–2 dias | **Concluída** |
| 1 | Bradesco em produção assistida: sombra, promoção, dias úteis, `PARTIAL`, retenção e proteção do `/sessions` | 3–5 dias | **Em andamento** |
| 2 | Operação diária e segurança: autenticação/papéis, watchdog com alerta, digest e workflow auditável | 1–1,5 semana | Pendente |
| 3 | Cobertura e resiliência: Allianz, receita declarativa, testes de mutação e Porto | 2–3 semanas | Pendente |
| 4 | Infraestrutura e deploy: Alembic/Postgres/Docker, backup, métricas e runbook | 1 semana | Pendente |
| 5 | Integração com ERP/CRM via API/webhook idempotente | 1 semana | Pendente |

> Estimativas para 1 desenvolvedor. Não incluem tempo de liberação de acesso,
> negociação com seguradoras, validação jurídica dos termos de uso ou onboarding
> comercial da API.

---

## Etapa 0 — Fundação (concluída)

**Objetivo:** plataforma rodando localmente com dados fictícios e o caminho
completo de coleta, sem depender de portal real.

### Entregue

- Domínio, aplicação, infraestrutura e interfaces separados por Clean
  Architecture; composition root em `container.py`.
- SQLAlchemy 2.0 + SQLite, store transacional, evidência JSON por execução.
- Loader de plugins com validação de manifest e isolamento de plugin quebrado.
- Plugin demo com dados fictícios e `_template/` para novos adapters.
- Painel FastAPI + Jinja/HTMX: cards, filtros, tabela, detalhe, histórico de
  eventos, atualização inline de status, `/planilha` e exportação CSV.
- CLI: `init-db`, `seed`, `collect`, `mark-overdue`, `plugins`, `scheduler`,
  `credentials`.
- Coleta idempotente; falha preserva os dados anteriores e marca a execução
  como `FAILED`, sem esvaziar o painel.
- `/plugins`, `/runs`, `/health` (alias `/healthz`) e testes verdes.

### Critérios de aceite atendidos

- `uv run pytest -q` e `uv run ruff check .` passam.
- `uv run python -m corretor.cli seed` popula o painel com dados fictícios.
- `uvicorn corretor.main:app` exibe o painel funcionando.
- Coleta manual é idempotente.
- Simular falha do adapter mantém os dados anteriores.
- `/plugins` mostra o plugin demo e eventuais erros de carregamento.

---

## Etapa 1 — Bradesco em produção assistida (3–5 dias) — EM ANDAMENTO

**Objetivo:** provar que o único portal real funciona diariamente em modo sombra
e promover o plugin com segurança, sem ampliar a cobertura.

### 1.1 Modo sombra (3 dias úteis)

- Comparar diariamente o resultado automático com a conferência manual no
  portal.
- Registrar divergências, tempo economizado e falhas em
  `docs/adapters/bradesco.md`, **sem credenciais**.
- Só promover quando **100% das pendências encontradas manualmente** aparecerem
  no painel por **3 dias úteis consecutivos**.

### 1.2 Promoção controlada do plugin

- Promover o manifest de `discovery` para `ready` após o modo sombra.
- Fazer a coleta (scheduler, CLI e web) respeitar o status do manifest; hoje
  `collect_all()` considera apenas `insurers.active` no banco.
- Deixar explícito o comportamento de `seed` e do scheduler para plugins
  `discovery`/`disabled`.
- Documentar a decisão no guia do adapter.

### 1.3 Confiabilidade da coleta

- **Dias úteis:** agendar a coleta de segunda a sexta (`day_of_week=mon-fri`),
  tanto no scheduler web quanto no CLI.
- **`PARTIAL`:** usar quando uma fonte da mesma seguradora concluir e outra
  falhar (ex.: Propostas OK e Parcelas em Atraso com erro). Um adapter que não
  consegue ler o snapshot completo continua obrigado a levantar `AdapterError`;
  nunca retornar lista incompleta como se fosse sucesso.
- **Evidência de falha:** salvar JSON de erro e, no fallback HTML, screenshot ou
  trace quando disponível.
- **Testes:** `mark_overdue`/`VENCIDA`, `run_daily_job`, filtro por status do
  manifest, `PARTIAL` e sessão expirada.

### 1.4 Segurança mínima e LGPD

- Proteger `/sessions`: exigir autenticação ou restringir a execução local
  (loopback) e manter o recurso desabilitado por padrão fora do ambiente local.
- **Retenção de evidências:** configuração `EVIDENCE_RETENTION_DAYS` (padrão
  **90 dias**) e rotina de expurgo no job diário/CLI, com teste.
- Revisar PII em evidências e logs; mascarar dados pessoais não essenciais e
  nunca registrar credenciais, tokens ou payload bruto com PII.
- Corrigir o README, que hoje afirma que CPF é mascarado e que a retenção está
  definida antes de essas rotinas existirem.

### Critérios de aceite da Etapa 1

- Coleta real em modo sombra por 3 dias úteis consecutivos, sem intervenção
  diária, com 100% de correspondência com a conferência manual.
- Plugin promovido a `ready` e scheduler coletando apenas plugins `ready` e
  seguradoras ativas.
- Falha de portal/layout gera `FAILED` ou `PARTIAL` com evidência, sem falso
  “sem pendências”.
- `/sessions` inacessível sem autenticação ou fora do loopback.
- Retenção de evidências configurada, testada e documentada.
- `pytest`, `ruff check` e `ruff format --check` passam; docs atualizados.

---

## Etapa 2 — Operação diária e segurança (1–1,5 semana)

**Objetivo:** transformar a coleta em rotina confiável, utilizável pela equipe e
com acesso controlado.

### Passos

- **Autenticação e papéis:** operador e gestor veem toda a carteira; produtor vê
  apenas seus clientes. Toda alteração registra o autor.
- **Watchdog com alerta:** notificar falha, `PARTIAL` ou seguradora sem sucesso
  há mais de `STALE_AFTER_HOURS` (padrão 26h). Canal interno a definir (e-mail,
  Telegram ou digest no painel).
- **Digest interno diário** para a operação, sem notificar clientes.
- **Workflow auditável:** validar transições, exigir justificativa para
  `DESCARTADA`, registrar diff dos campos alterados e autor do evento.
- **Estados de tela:** atualizado, atualizando, parcial, desatualizado e vazio;
  banner por seguradora com motivo, último sucesso e ação de tentar novamente.
- **Filtros:** incluir produtor, manter filtros salvos e exibir a próxima
  execução prevista.
- **Testes:** autenticação/papéis, watchdog, transições e estados de tela.

### Critérios de aceite da Etapa 2

- Operador consegue tratar uma pendência do início ao fim sem planilha.
- Produtor vê somente as pendências dos seus clientes.
- Toda falha é detectada e visível no mesmo dia, com alerta interno.
- Toda alteração é auditável com autor, data e valores anteriores/novos.
- Uma semana em produção assistida com zero parcelas perdidas.

---

## Etapa 3 — Cobertura e resiliência (2–3 semanas)

**Objetivo:** cobrir as demais seguradoras e aumentar a resistência a mudanças
de layout sem aumentar o risco operacional.

### Passos

- **Allianz** (primeira da etapa): descoberta documentada em
  `docs/adapters/allianz.md`, login manual, Network/DevTools, verificação de
  MFA/captcha/certificado e termos de uso.
- Estratégia de coleta, nesta ordem: **API oficial > endpoint interno (XHR/JSON)
  > DOM com Playwright**.
- **Receita declarativa** (`mode: recipe`): loader, `recipe.yaml` versionado por
  seguradora, seletores semânticos com fallback por campo e validação de schema.
- **Testes de mutação de HTML** para todos os adapters DOM: classes, ordem de
  colunas, wrappers e labels.
- **Saúde por seguradora e métricas** de coleta (última execução, último
  sucesso, duração, itens e falhas).
- **Porto** depois da Allianz estável, um portal por vez.
- Retomar o onboarding da API Bradesco quando o acesso comercial for liberado,
  em paralelo e sem bloquear a operação HTML.
- **Fallback com LLM** apenas depois de receita e testes de mutação; nunca como
  caminho principal, sempre com PII mascarada, saída estruturada e aprovação
  humana.

### Critérios de aceite da Etapa 3

- Três seguradoras coletando diariamente.
- Mudança simples de layout corrigida por configuração, sem deploy de código.
- Tempo médio de detecção de falha menor que uma execução e correção em até um
  dia útil.
- Todo adapter DOM coberto por testes de mutação.

---

## Etapa 4 — Infraestrutura e deploy (1 semana)

**Objetivo:** operar com banco de produção, backup e monitoramento confiáveis.

### Passos

- Introduzir **Alembic** antes da migração; substituir `create_all` por
  migrações versionadas.
- **PostgreSQL + Docker Compose**, com backup e restauração testada.
- Deploy com **IP fixo**, HTTPS, segredos em cofre e `/sessions` sem exposição
  pública.
- Logs estruturados, Sentry/métricas, healthchecks e alerta de coleta parada.
- Rotina de retenção/LGPD: prazo de evidências, mapa de dados pessoais, revisão
  de acessos e descarte seguro.
- **Runbook operacional:** o que fazer quando um portal falha ou uma sessão
  expira.

### Critérios de aceite da Etapa 4

- Backup e restauração validados.
- Nenhum segredo ou PII em logs, imagens ou repositório.
- Health check e monitoramento ativos, com alerta de coleta parada.
- Operação consegue resolver incidentes com o runbook.

---

## Etapa 5 — Integração com ERP/CRM (1 semana)

**Objetivo:** levar os dados para o sistema da corretora com segurança e sem
duplicidade.

### Passos

- API de leitura + webhook/outbox idempotente para o ERP/CRM.
- Autenticação de API, papéis e trilha de auditoria.
- Retry com idempotência; falha de integração não perde evento.
- Monitoramento e runbook específicos da integração.

### Critérios de aceite da Etapa 5

- Dados chegam ao sistema destino sem duplicidade.
- Falha de integração não perde evento (retry + outbox).
- Operação consegue reprocessar e auditar a integração.

---

## Decisões e dependências

| Momento | Decisão/ação necessária |
|---|---|
| Antes da Etapa 1 | Confirmar o **Bradesco** como primeiro portal em produção assistida |
| Antes da Etapa 1 | Confirmar janela de modo sombra (3 dias úteis) e retenção de evidências (padrão 90 dias) |
| Etapa 1 | Confirmar acesso à API oficial ou manter o fallback HTML durante o standby comercial |
| Etapa 2 | Definir quem usa o painel, papéis, destinatários do digest e horário da coleta |
| Etapa 2 | Confirmar onde hospedar; autenticação é pré-requisito para acesso da equipe |
| Etapa 3 | Liberar acesso/teste da Allianz e confirmar termos de uso |
| Etapa 3 | Priorizar Porto e indicar contatos/API oficial, se existirem |
| Etapa 4 | Definir destino de backup, política de LGPD e responsável por incidentes |
| Etapa 5 | Informar o sistema destino (ERP/CRM) e a interface de integração |

## Riscos e mitigação

| Risco | Mitigação |
|---|---|
| Layout do portal muda | API/XHR primeiro; receita com fallbacks; testes de mutação; evidência de falha |
| Sessão expira ou exige captcha/MFA | Renovação automática, fallback manual e `NEEDS_ATTENTION`; nunca contornar proteção |
| Coleta falha e parece “sem pendências” | `FAILED`/`PARTIAL` explícitos, dados anteriores preservados e alerta |
| PII em evidências/logs | Retenção, mascaramento, acesso restrito e revisão de logs |
| Plugin `discovery` entra na rotina | Coleta filtra status do manifest e seguradora ativa |
| Escopo cresce antes da base estabilizar | Uma seguradora por vez; critérios de aceite por etapa |

## Ritual de trabalho

1. Implementar uma entrega vertical pequena.
2. Rodar testes e lint.
3. Demonstrar o fluxo funcionando.
4. Atualizar docs (PRD/AGENTS/README) se o escopo ou a arquitetura mudarem.
5. Seguir para a próxima entrega.

## Próximo passo

Começar a **Etapa 1** por:

1. Iniciar o modo sombra do Bradesco e registrar divergências.
2. Fazer a coleta respeitar `manifest.status`.
3. Agendar em dias úteis e definir a semântica de `PARTIAL`.
4. Implementar retenção de evidências e proteção do `/sessions`.
5. Adicionar os testes de `mark_overdue`, scheduler, `PARTIAL` e retenção.

Nenhuma credencial real é necessária para desenvolver ou testar esta etapa.
