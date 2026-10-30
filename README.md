# Corretor RPA

Monitoramento diário de **parcelas pendentes** nas seguradoras, com painel
consolidado, workflow de tratamento e arquitetura plug-and-play para novos
portais.

> **Status:** fase 0 concluída. Painel FastAPI + Jinja/HTMX, loader de plugins,
> adapter demo, CLI e testes verdes. O plugin **Bradesco** coleta **Parcelas em
> Atraso** (JSON) e **Propostas Pendentes** (HTML) usando sessão manual salva;
> falta validação em produção e o adapter Allianz.

## Documentos

| Documento | Conteúdo |
|---|---|
| [`docs/PRD.md`](docs/PRD.md) | Fonte da verdade de produto: problema, escopo, regras, critérios de aceitação e UX |
| [`docs/PLANO.md`](docs/PLANO.md) | Passo a passo de execução, estimativas e critérios de aceite por etapa |
| [`AGENTS.md`](AGENTS.md) | Guia de engenharia: Clean Architecture, plugins, segurança e convenções |

## O problema

Hoje a equipe entra diariamente no portal de cada seguradora (4–5 cliques por
consulta) para verificar parcelas pendentes. O controle é fragmentado e manual;
uma parcela não percebida pode deixar o cliente sem cobertura e gerar perda de
comissão.

## A solução

- Coleta automática diária, **somente leitura**, nas seguradoras ativas.
- Painel único com seguradora, segurado, apólice, ramo, parcela, vencimento,
  valor, produtor e status.
- Destaque de pendências novas, a vencer e vencidas.
- Separação entre **Parcelas** (apólices emitidas) e **Propostas** (1ª parcela/
  CCB aguardando emissão), com filtro por tipo.
- Workflow: Detectada → Em análise → Avisada → Regularizada / Vencida / Descartada.
- Status de saúde da coleta por seguradora — falha nunca vira “sem pendências”.
- Novas seguradoras entram como **plugins**, sem alterar o núcleo.

## Arquitetura

Clean Architecture com dependências apontando para dentro:

```
interfaces (FastAPI/Jinja/HTMX, CLI)
        ↓
application (casos de uso, normalização, diff)
        ↓
domain (entidades, enums, portas)
        ↑
infrastructure (SQLAlchemy, arquivos, plugins, scheduler)
```

- `domain/`: entidades, enums, erros e contratos. Sem IO.
- `application/`: coleta, diff, atualização de pendências e DTOs.
- `infrastructure/`: banco, evidências, configuração, loader de plugins e
  composition root (`container.py`).
- `interfaces/`: painel web e CLI.
- `plugins/`: adapters de seguradoras, descobertos em runtime.

### Estrutura

```
src/corretor/
  domain/
    entities/       # uma classe por arquivo
    enums/
    errors/
    ports/
  application/
    dto/            # um DTO por arquivo
    ports/
    logic/          # normalização e diff (funções puras)
    services/       # CollectionService, PendencyService
  infrastructure/
    config/
    clock/
    persistence/
      models/       # um model ORM por arquivo
    evidence/
    plugins/
    container.py
  interfaces/
    web/
      routes/       # um módulo de rotas por domínio
      templates/
      static/
    cli.py
  plugins/
    demo/
    bradesco/
      manifest.yaml
      plugin.py
      adapter.py
      mapping.py
    _template/      # modelo para nova seguradora (ignorado pelo loader)
  main.py
tests/
  application/
  interfaces/
  plugins/
docs/
  PRD.md
  PLANO.md
  adapters/bradesco.md
```

Convenção: **uma classe por arquivo**, arquivos do mesmo domínio na mesma
pasta e `__init__.py` reexportando os nomes públicos.

## Como adicionar uma seguradora (plug-and-play)

1. Copie `src/corretor/plugins/_template/` para
   `src/corretor/plugins/<slug>/`.
2. Ajuste `manifest.yaml` (`slug`, `name`, `version`, `status`).
3. Implemente `create_adapter(manifest, context)` retornando um objeto com
   `fetch_pending() -> list[RawInstallment]`.
4. Garanta que a coleta devolva um **snapshot completo** e levante
   `AdapterError` em caso de falha/parse parcial.
5. Rode os testes de contrato e reinicie a aplicação. O plugin aparece em
   `/plugins`.

Nenhuma mudança em `domain`, `application` ou `infrastructure` é necessária.

## Descoberta de portais (Playwright)

Antes de implementar um adapter real, use o script de descoberta assistida.
Ele abre o portal em um navegador visível, espera o **login manual** e captura
URL final, frames, chamadas de rede, screenshot, HTML e trace.

```bash
uv run --python 3.12 --with playwright python tools/discover_portal.py --slug bradesco
```

- O script **não lê senha**, `links.txt` ou o arquivo `senha`.
- As capturas vão para `data/discovery/<slug>/<timestamp>/`, que é ignorado
  pelo Git.
- Preencha `docs/adapters/<slug>.md` com o caminho e os endpoints observados.

Detalhes em [`tools/README.md`](tools/README.md).

## Bradesco (plugin JSON)

O plugin `bradesco` usa dois endpoints, com a mesma sessão autenticada:

- **Parcelas em Atraso:** `/pnegocios/wps/PA_BSPN-DBoardAuto-PU/api/parcelas/v1/list`
  (JSON);
- **Propostas Pendentes:** `/pnegocios/wps/PA_BSPN-DBoardAuto-PU/api/propostas/pendentes/v1/view`
  (fragmento HTML).

Ele reutiliza uma sessão autenticada salva pelo Playwright — **nenhuma senha
fica no projeto**.

```bash
# 1. gere a sessão com login manual
uv run --python 3.12 --with playwright python tools/discover_portal.py --slug bradesco

# 2. copie o state.json da captura para o caminho configurado
cp data/discovery/bradesco/<timestamp>/state.json data/sessions/bradesco.json

# 3. colete
uv run python -m corretor.cli collect bradesco
```

O manifest está com `status: discovery`; a coleta manual funciona, mas o plugin
não entra no seed nem no agendador até ser promovido a `ready`. Se a sessão
expirar, a execução fica `AGUARDANDO_INTERVENCAO` e é preciso refazer o login
manual. Detalhes em [`docs/adapters/bradesco.md`](docs/adapters/bradesco.md).

## Stack

- Python 3.12 + `uv`
- FastAPI + Jinja2 + HTMX (vendorizado)
- SQLAlchemy 2.0 + SQLite (dev) / PostgreSQL (produção)
- Pydantic v2 + pydantic-settings + PyYAML
- APScheduler
- pytest + ruff
- Playwright (opcional, extra `rpa`)

## Setup

```bash
uv venv --python 3.12
uv pip install -e ".[dev,rpa]"
cp .env.example .env

uv run python -m corretor.cli init-db
uv run python -m corretor.cli seed
uv run uvicorn corretor.main:app --reload
```

Acesse `http://127.0.0.1:8000`.

### Comandos úteis

```bash
uv run python -m corretor.cli collect all
uv run python -m corretor.cli collect bradesco
uv run python -m corretor.cli mark-overdue
uv run python -m corretor.cli plugins
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

### Configuração (`.env`)

`DATABASE_URL`, `EVIDENCE_DIR`, `ENABLE_SCHEDULER`, `SCHEDULER_HOUR`,
`SCHEDULER_MINUTE`, `TIMEZONE`, `STALE_AFTER_HOURS`, `PLUGIN_PATHS`,
`SEED_DEMO`, `LOG_LEVEL`, `BRADESCO_STATE_PATH`, `BRADESCO_ENDPOINT`,
`BRADESCO_PROPOSALS_ENDPOINT`, `BRADESCO_COLLECT_PROPOSALS`,
`BRADESCO_HEADLESS`, `BRADESCO_TIMEOUT_MS`.

## Segurança e LGPD

- **Nunca** leia o arquivo `senha` nem copie credenciais de `links.txt` para o
  projeto.
- Segredos apenas em variáveis de ambiente/cofre; `.env` e `data/` não vão para
  o Git.
- Dados de segurados são pessoais: seeds e fixtures são fictícios, CPF é
  mascarado e evidências têm retenção definida.
- A solução é read-only: não paga, não emite boleto e não altera apólices.
- Não contorna MFA/captcha; quando necessário, a coleta aguarda intervenção
  humana.

## Roadmap

| Fase | Entrega |
|---|---|
| 0 | **Concluída:** Clean Architecture + plugins + adapter demo + painel + CLI + testes |
| 1 | **Bradesco concluído** (parcelas via JSON + propostas via HTML, sessão manual); falta Allianz e receita declarativa |
| 2 | Scheduler, watchdog, digest interno e workflow completo |
| 3 | Porto, testes de mutação, fallback LLM, Postgres/Docker |
| 4 | Integração com ERP/CRM via API/webhook idempotente |
