# Corretor RPA

Monitoramento diário de **parcelas pendentes** nas seguradoras, com painel
consolidado, workflow de tratamento e arquitetura plug-and-play para novos
portais.

> **Status:** fase 0 (scaffold). A documentação de produto e engenharia está
> pronta; a aplicação será construída sobre ela.

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
  application/
  infrastructure/
  interfaces/
    web/            # templates Jinja + partials HTMX + static
    cli.py
  plugins/
    demo/
      manifest.yaml
      plugin.py
      adapter.py
    _template/      # modelo para nova seguradora (ignorado pelo loader)
  main.py
tests/
  application/
  interfaces/
  plugins/
docs/
  PRD.md
```

## Como adicionar uma seguradora (plug-and-play)

1. Copie `src/corretor/plugins/_template/` para
   `src/corretor/plugins/<slug>/`.
2. Ajuste `manifest.yaml` (`slug`, `name`, `version`, `status`).
3. Implemente `create_adapter(manifest)` retornando um objeto com
   `fetch_pending() -> list[RawInstallment]`.
4. Garanta que a coleta devolva um **snapshot completo** e levante
   `AdapterError` em caso de falha/parse parcial.
5. Rode os testes de contrato e reinicie a aplicação. O plugin aparece em
   `/plugins`.

Nenhuma mudança em `domain`, `application` ou `infrastructure` é necessária.

## Stack

- Python 3.12 + `uv`
- FastAPI + Jinja2 + HTMX (vendorizado)
- SQLAlchemy 2.0 + SQLite (dev) / PostgreSQL (produção)
- Pydantic v2 + pydantic-settings + PyYAML
- APScheduler
- pytest + ruff
- Playwright (opcional, extra `rpa`)

## Setup (após o scaffold da fase 0)

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
cp .env.example .env

uv run python -m corretor.cli init-db
uv run python -m corretor.cli seed
uv run uvicorn corretor.main:app --reload
```

Acesse `http://127.0.0.1:8000`.

### Comandos úteis

```bash
uv run python -m corretor.cli collect all
uv run python -m corretor.cli plugins
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
```

### Configuração (`.env`)

`DATABASE_URL`, `EVIDENCE_DIR`, `ENABLE_SCHEDULER`, `SCHEDULER_HOUR`,
`SCHEDULER_MINUTE`, `TIMEZONE`, `STALE_AFTER_HOURS`, `PLUGIN_PATHS`,
`SEED_DEMO`, `LOG_LEVEL`.

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
| 0 | Scaffold Clean Architecture + plugins + adapter demo + painel + testes |
| 1 | Primeiro adapter real (Allianz) + receita declarativa + evidências |
| 2 | Scheduler, watchdog, digest interno e workflow completo |
| 3 | Bradesco/Porto, testes de mutação, fallback LLM, Postgres/Docker |
| 4 | Integração com ERP/CRM via API/webhook idempotente |
