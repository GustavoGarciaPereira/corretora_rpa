# Plano de Execução — Corretor RPA

> **Status em 2026-10-30:** fase 0 concluída; plugin Bradesco com **adapter da
> API oficial** de Propostas Pendentes (OAuth2/JWT) pronto, mas onboarding em
> standby. A operação usa fallback HTML com sessão assistida; a página
> `/sessions` abre o navegador, espera o login manual e salva o `state.json`
> automaticamente. “Parcelas em Atraso” está pronto, mas desativado por flag.
> Próximo marco: adapter Allianz e retomada do onboarding da API.

## Princípios

- Entregas **verticais**: cada etapa termina com algo funcionando de ponta a
  ponta (coleta → banco → painel), não apenas camadas isoladas.
- Toda etapa termina com **demo + testes + documentação**.
- Nenhuma credencial real entra no repositório, em chats ou em logs.
- Até o primeiro portal real, o desenvolvimento usa **dados demo fictícios**.
- Primeiro em **modo sombra** (coleta real comparada ao processo manual), depois
  em produção.

## Visão das etapas

| Etapa | Entrega | Estimativa |
|---|---|---|
| 0 | Fundação: Clean Architecture + plugins + adapter demo + painel + testes | 1–2 dias |
| 1 | Primeiro portal real (Allianz) + receita declarativa + evidências | 3–5 dias |
| 2 | Operação diária: scheduler, watchdog, workflow, digest, CSV | 2–3 dias |
| 3 | Expansão: Bradesco/Porto, mutação de HTML, fallback LLM, Postgres/Docker | 1–2 semanas |
| 4 | Integração com ERP/CRM, papéis de acesso, deploy e monitoramento | 1 semana |

> Estimativas para 1 desenvolvedor. Não incluem tempo de liberação de acesso,
> negociação com seguradoras ou validação jurídica dos termos de uso.

---

## Etapa 0 — Fundação (1–2 dias)

**Objetivo:** ter a plataforma rodando localmente com dados fictícios e o
caminho completo de coleta, sem depender de portal real.

### Passos

1. **Ambiente**
   - Criar `pyproject.toml` com Python 3.12, dependências e extras `dev`/`rpa`.
   - Criar `.env.example`, `.gitignore` e README de setup.
   - Validar `uv venv` + `uv pip install -e ".[dev]"`.

2. **Domínio**
   - Entidades: `RawInstallment`, `Insurer`, `Policy`, `Installment`,
     `Pendency`, `CollectionRun`, `PendencyEvent`, `AdapterManifest`.
   - Enums: `WorkflowStatus`, `RunStatus`.
   - Erros: `AdapterError`, `ValidationError`, `PluginError`.
   - Porta `InsurerAdapter` e `Clock`.

3. **Aplicação**
   - Normalização e validação dos dados coletados.
   - Diff puro: novo, visto, ausente, reaberto, descartado.
   - Casos de uso: coletar seguradora, coletar todas, atualizar status,
     atualizar tratamento, marcar vencidas.
   - DTOs de leitura para o painel.

4. **Infraestrutura**
   - SQLAlchemy 2.0 + SQLite; criação de schema.
   - Store transacional implementando as portas.
   - Evidência em JSON por execução.
   - Configuração via `.env`.
   - Loader de plugins com validação de manifest e isolamento de erro.

5. **Plugin demo**
   - `manifest.yaml`, `plugin.py`, `adapter.py`.
   - Dados fictícios com vencimentos fixos: um vencido, um próximo, um futuro.
   - `_template/` para novas seguradoras.

6. **Interface web**
   - FastAPI + Jinja + HTMX vendorizado.
   - Painel com cards, filtros, tabela, atualização inline de status.
   - Página de detalhe com histórico.
   - Páginas `/plugins`, `/runs`, `/healthz`.
   - Exportação CSV.

7. **CLI**
   - `init-db`, `seed`, `collect`, `plugins`, `mark-overdue`.

8. **Testes**
   - Normalização, diff, coleta idempotente, regularização, falha, reabertura.
   - Loader de plugins (demo encontrado, `_template` ignorado, plugin quebrado
     isolado).
   - Rotas principais, partial HTMX, atualização de status e CSV.

### Critério de aceite da Etapa 0

- `uv run pytest -q` e `uv run ruff check .` passam.
- `uv run python -m corretor.cli seed` popula o painel com dados fictícios.
- `uvicorn corretor.main:app` exibe o painel funcionando.
- Coleta manual é idempotente.
- Simular falha do adapter mantém os dados anteriores e marca a execução como
  falha — nunca esvazia o painel.
- `/plugins` mostra o plugin demo e eventuais erros de carregamento.

---

## Etapa 1 — Primeiro portal real (3–5 dias)

**Objetivo:** coletar dados reais de uma seguradora, em modo sombra, sem
intervenção manual diária.

**Seguradora sugerida:** Allianz (portal Angular, mais previsível para começar).

### Passos

1. **Descoberta (meio dia)**
   - Login manual e navegação até “parcelas pendentes”.
   - DevTools → Network: identificar XHR/JSON reaproveitáveis.
   - Verificar MFA, captcha, certificado, tempo de sessão e termos de uso.
   - Documentar em `docs/adapters/allianz.md` **sem credenciais**.

2. **Decisão de estratégia**
   - API oficial > endpoint interno > DOM com Playwright.
   - Registrar a decisão e os riscos no documento do adapter.

3. **Implementação do plugin**
   - Criar `plugins/allianz/`.
   - Implementar `fetch_pending()` retornando snapshot completo.
   - Criar `recipe.yaml` com seletores semânticos e fallbacks.
   - Validar campos obrigatórios e quantidade mínima/plausível.

4. **Evidência e resiliência**
   - Salvar JSON bruto e screenshot/trace em falha.
   - Health check e estados `SUCCESS`/`FAILED`/`PARTIAL`.
   - Teste com fixture HTML/JSON anonimizada.
   - Primeiro teste de mutação: mudar classes, ordem de colunas e labels.

5. **Modo sombra (3–5 dias)**
   - Comparar o resultado automático com a conferência manual.
   - Medir divergências, tempo economizado e falhas.
   - Ajustar seletores e validações antes de ativar em produção.

### Critério de aceite da Etapa 1

- Coleta real diária concluída sem intervenção por 3 dias consecutivos.
- 100% das pendências encontradas manualmente também aparecem no painel.
- Falha de portal/layout gera `FAILED`/`PARTIAL` com evidência e alerta, sem
  falso “sem pendências”.
- Nenhuma credencial no repositório ou nos logs.

---

## Etapa 2 — Operação diária (2–3 dias)

**Objetivo:** transformar a coleta em rotina confiável e utilizável pela equipe.

### Passos

- Agendador diário em dias úteis (fuso America/Sao_Paulo) + execução manual.
- Watchdog de coleta: alerta se uma seguradora ficar mais de 26h sem sucesso.
- Rotina diária de vencimento (`VENCIDA` para pendências abertas vencidas).
- Workflow completo na tela de detalhe + histórico de eventos.
- Digest interno diário para a operação (sem notificar clientes).
- Exportação CSV e filtros salvos.
- Estados de tela: atualizado, atualizando, parcial, desatualizado e vazio.
- Ajustes de acesso: operador, gestor e produtor.

### Critério de aceite da Etapa 2

- Uma semana em produção assistida com zero parcelas perdidas.
- Toda falha detectada no mesmo dia e visível no painel.
- Operador consegue tratar uma pendência do início ao fim sem planilha.

---

## Etapa 3 — Expansão (1–2 semanas)

**Objetivo:** cobrir as demais seguradoras e aumentar a resistência a mudanças.

### Passos

- Plugins Bradesco e Porto, um por vez, com descoberta documentada.
- Testes de mutação de HTML para todos os adapters.
- Fallback com LLM apenas para recuperação de layout, com validação e aprovação
  humana.
- Receita declarativa com hot reload e versionamento.
- Migração para PostgreSQL + Docker Compose + backup.
- Página de saúde por seguradora e métricas de coleta.

### Critério de aceite da Etapa 3

- Três seguradoras coletando diariamente.
- Mudança simples de layout corrigida por configuração, sem deploy de código.
- Tempo médio de detecção de falha < 1 execução e correção < 1 dia útil.

---

## Etapa 4 — Integração e produção (1 semana)

**Objetivo:** levar os dados para o sistema da corretora com segurança.

### Passos

- API de leitura + webhook/outbox idempotente para o ERP/CRM.
- Autenticação e papéis; trilha de auditoria.
- Deploy com IP fixo, HTTPS, backup e restauração testada.
- Monitoramento: logs, Sentry, health check, alerta de coleta parada.
- Política de retenção/LGPD e revisão de acessos.
- Runbook operacional: o que fazer quando um portal falha.

### Critério de aceite da Etapa 4

- Dados chegam ao sistema destino sem duplicidade.
- Falha de integração não perde evento (retry + outbox).
- Backup e restauração validados.
- Operação consegue resolver incidentes com o runbook.

---

## O que preciso de você em cada fase

| Momento | Informação/ação |
|---|---|
| Antes da Etapa 0 | Confirmar que podemos começar sem credenciais (dados demo) |
| Etapa 1 | Escolher a primeira seguradora; liberar acesso de teste por cofre/env; confirmar termos de uso |
| Etapa 1 | Dizer o que é “parcela pendente”: não paga pelo cliente ou comissão da corretora? |
| Etapa 2 | Definir quem usa o painel, quem recebe o digest e o horário da coleta |
| Etapa 2 | Confirmar onde hospedar (IP fixo é importante) |
| Etapa 3 | Priorizar Bradesco ou Porto e indicar contatos/API oficial, se existirem |
| Etapa 4 | Informar o sistema destino (ERP/CRM) e a interface de integração |

## Ritual de trabalho

1. Implementar uma entrega vertical pequena.
2. Rodar testes e lint.
3. Demonstrar o fluxo funcionando.
4. Atualizar docs (PRD/AGENTS/README) se o escopo ou a arquitetura mudarem.
5. Seguir para a próxima entrega.

## Próximo passo

Executar a **Etapa 0**, começando por:

1. `pyproject.toml` + estrutura `src/corretor` + configuração.
2. Domínio + aplicação (normalização, diff, casos de uso).
3. Banco + loader de plugins + plugin demo.
4. Painel Jinja/HTMX + CLI.
5. Testes e validação local.

Nenhuma credencial real é necessária nesta etapa.
