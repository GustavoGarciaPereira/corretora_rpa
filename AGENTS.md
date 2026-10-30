# AGENTS.md — Corretor RPA

## 1. Visão geral

Automação para uma corretora de seguros monitorar **parcelas pendentes** nos
portais das seguradoras e consolidar tudo em um painel único.

**Dor:** todos os dias alguém entra no portal de cada seguradora (4–5 cliques
por portal) para verificar parcelas pendentes; não há visão consolidada e uma
parcela esquecida pode deixar o cliente sem cobertura e gerar perda de comissão.

**Objetivo do MVP:** coletar diariamente (somente leitura), normalizar, detectar
novidades, listar no painel e registrar evidências. Alertas externos e
integração com ERP/CRM ficam para fases posteriores.

**Estado em 2026-10-30:** fase 0 concluída. Painel FastAPI + Jinja/HTMX,
loader de plugins, adapter demo, CLI e testes verdes. O plugin Bradesco tem
**adapter da API oficial** de Propostas Pendentes (OAuth2/JWT), mas o onboarding
comercial está em **standby**; a operação usa o **fallback HTML** com sessão
assistida. A página `/sessions` mostra o status e como renovar. A coleta de
**Parcelas em Atraso** está implementada, mas desativada por
`BRADESCO_COLLECT_PARCELAS=false`; falta Allianz/receita declarativa.

**Fora de escopo (não implementar sem pedido explícito):**

- pagar, emitir boleto, cancelar apólice ou qualquer ação financeira;
- burlar captcha, MFA ou mecanismos anti-bot;
- contornar termos de uso dos portais;
- notificar clientes por WhatsApp/e-mail/SMS nesta versão;
- integração bidirecional com ERP/CRM nesta versão.

## 2. Documentos de referência

| Documento | Papel |
|---|---|
| `docs/PRD.md` | **Fonte da verdade de produto**: problema, escopo, regras, critérios de aceitação e UX |
| `docs/PLANO.md` | Passo a passo de execução, entregas, estimativas e critérios de aceite por etapa |
| `AGENTS.md` | Guia de engenharia: arquitetura, convenções, segurança e comandos |
| `ideia_fluxo.txt` | Contexto original da dor (histórico) |
| `links.txt` | Portais e acessos — **sensível, não copiar para código/docs** |
| `senha` | **NUNCA abrir, ler, copiar ou imprimir** |

Em caso de conflito, o `docs/PRD.md` define **o quê/porquê**; este arquivo
define **como** implementar com segurança.

## 3. Regras de segurança (invioláveis)

- **NUNCA abrir, ler, copiar ou imprimir o arquivo `senha`.**
- **NUNCA** colocar credenciais de `links.txt` em código, templates, testes,
  logs, docs ou commits. `links.txt` contém login e usuário — é dado sensível.
- **NUNCA** commitar `.env`, banco, evidências ou dumps. Segredos vivem em
  variáveis de ambiente / cofre; no código, apenas referências.
- A raiz do repositório Git é `/home/gustavo` (a home inteira). **Nunca** rodar
  `git add .` ou `git add -A` a partir da home. Adicionar caminhos explícitos:
  `git add rpas/corretor/...`.
- LGPD: nomes, CPF e dados de apólice são dados pessoais. Fixtures e seeds
  devem ser **fictícios e anonimizados**; mascarar CPF no painel; definir
  retenção de evidências (padrão: 90 dias).
- Não contornar autenticação. Se o portal exigir MFA/captcha, a execução vira
  `AGUARDANDO_INTERVENCAO` e um humano conclui o login.
- A coleta é **read-only**. Nenhum adapter pode clicar em pagar/emitir.

## 4. Stack

- **Python 3.12** (o `python3` do sistema é 3.8; usar `uv` com 3.12).
- **FastAPI** + **Jinja2** + **HTMX** (vendorizado em `app/static/htmx.min.js`,
  sem CDN em produção).
- **SQLAlchemy 2.0** (estilo `Mapped`) + **SQLite** em dev / **PostgreSQL** em
  produção.
- **Pydantic v2** + **pydantic-settings** para configuração.
- **PyYAML** para manifests e receitas declarativas de plugins.
- **APScheduler** para coleta diária (MVP); Celery/Redis só se houver escala.
- **pytest** + **httpx** (TestClient) para testes.
- **Playwright** como dependência opcional (extra `rpa`), apenas nos adapters
  que realmente precisarem de navegador.
- **ruff** para lint/format.

## 5. Arquitetura — Clean Architecture

Dependências apontam **sempre para dentro**. O centro é o domínio; detalhes
(FastAPI, SQLAlchemy, Playwright, arquivos) ficam nas bordas.

```
src/corretor/
  domain/                 # entidades, enums, erros e portas puras (sem IO)
    entities/             # uma classe por arquivo + __init__ reexportando
      adapter_manifest.py
      plugin_context.py
      raw_installment.py
      insurer.py
      policy.py
      installment.py
      pendency.py
      pendency_event.py
      collection_run.py
    enums/
      workflow_status.py
      run_status.py
    errors/               # uma exceção por arquivo
    ports/
      insurer_adapter.py
      clock.py
  application/            # casos de uso e regras de aplicação
    dto/                  # um DTO por arquivo
    ports/                # Store, AdapterProvider, EvidenceStore etc.
    logic/                # funções puras: normalization.py, diff.py
    services/             # CollectionService, PendencyService
  infrastructure/         # implementações concretas
    config/settings.py
    clock/system_clock.py
    persistence/
      database.py
      store.py            # SqlAlchemyStore
      models/             # um model ORM por arquivo
        base.py
        insurer.py
        policy.py
        installment.py
        pendency.py
        pendency_event.py
        collection_run.py
    evidence/file_evidence_store.py
    plugins/
      registry.py
      loaded_plugin.py
      plugin_load_error.py
    container.py          # composition root (wiring manual)
  interfaces/             # entrada/saída
    web/
      app.py
      dependencies.py
      filters.py
      routes/             # um módulo de rotas por domínio
      templates/
      static/
    cli.py
  plugins/                # adapters plug-and-play (não são camada de negócio)
    demo/
      manifest.yaml
      plugin.py
      adapter.py
    bradesco/
      manifest.yaml
      plugin.py
      adapter.py          # fallback HTML/sessão
      mapping.py
      api_adapter.py      # API oficial OAuth2/JWT
      api_mapping.py
      proposals.py
    _template/            # modelo para nova seguradora; ignorado pelo loader
  main.py                 # app = create_app()
tests/
  application/
  interfaces/
  plugins/
docs/
  PRD.md
  PLANO.md
  adapters/bradesco.md
  adapters/bradesco-api.md
```

### Regra de dependência (não violar)

- `domain` **não importa** nada de `application`, `infrastructure` ou
  `interfaces`. Sem SQLAlchemy, FastAPI, requests ou Playwright.
- `application` importa apenas `domain` e suas próprias portas.
- `infrastructure` implementa as portas de `application`/`domain`; pode usar
  SQLAlchemy, filesystem, HTTP e bibliotecas de automação.
- `interfaces` importa `application` e, na composição, `infrastructure`.
- `plugins` implementam `domain.ports.InsurerAdapter` e **não importam**
  `infrastructure` nem `interfaces`.
- `container.py` é o único lugar que conhece todas as implementações concretas.
- Regra de negócio não mora em rota, template, model ORM ou plugin.

### Convenção de arquivos (obrigatória)

- **Uma classe por arquivo.** Exceções: funções puras, constantes e tipos
  auxiliares podem compartilhar o arquivo da classe a que pertencem.
- Arquivos do mesmo domínio ficam na mesma pasta: `entities/`, `enums/`,
  `errors/`, `ports/`, `dto/`, `services/`, `models/`, `routes/`.
- Cada pasta tem `__init__.py` que **reexporta** os nomes públicos, para que os
  imports externos fiquem curtos (`from corretor.domain.entities import ...`).
- Rotas são funções agrupadas por domínio (`routes/dashboard.py`,
  `routes/pendencies.py`); não criar classe de rota.
- Nome de arquivo em `snake_case`; classe em `PascalCase`; protocolos e DTOs
  também em `PascalCase`.
- Um arquivo novo de model ORM deve ser importado em
  `persistence/models/__init__.py` para registrar no metadata.
- Não criar “utils.py” genérico: a função deve morar no domínio mais próximo.

### Fluxo de coleta

```
Scheduler/CLI/Web → CollectInsurer (application)
    → AdapterProvider.get(slug) → InsurerAdapter.fetch_pending()
    → normalize → diff (puro) → Store.apply_diff (transação)
    → CollectionRun (SUCCESS/FAILED/PARTIAL) + evidência
    → painel/consultas
```

### Contrato de adapter

```python
@dataclass(frozen=True)
class RawInstallment:
    policy_number: str
    insured_name: str
    branch: str
    installment_number: int
    due_date: date
    amount_cents: int
    producer: str = ""
    boleto_url: str = ""


class InsurerAdapter(Protocol):
    manifest: AdapterManifest

    def fetch_pending(self) -> list[RawInstallment]: ...
```

Regras do contrato:

- `fetch_pending()` retorna um **snapshot completo** das pendências. Parse
  parcial deve levantar `AdapterError`, nunca retornar lista incompleta.
- O adapter não grava no banco nem conhece templates/HTTP.
- Credenciais vêm de configuração/segredo, nunca hardcoded.
- Erros de autenticação, layout ou dados devem ser explícitos.

## 6. Plataforma plug-and-play (requisito do contratante)

Adicionar uma seguradora **não pode exigir mudança no núcleo**. O núcleo
descobre plugins; o plugin entrega o adapter.

### Estrutura de um plugin

```
src/corretor/plugins/<slug>/
  manifest.yaml     # metadados
  plugin.py         # create_adapter(manifest) -> InsurerAdapter
  adapter.py        # implementação (opcional; pode ficar em plugin.py)
  recipe.yaml       # seletores/fallbacks (quando o modo for "recipe")
```

`manifest.yaml`:

```yaml
slug: demo
name: Seguradora Demo
version: 0.1.0
description: Adapter fictício para desenvolvimento
mode: python        # python | recipe
status: ready       # ready | discovery | disabled
capabilities:
  - read_only
requires_session: false
```

`plugin.py`:

```python
from corretor.domain.entities import AdapterManifest, PluginContext
from .adapter import DemoAdapter


def create_adapter(manifest: AdapterManifest, context: PluginContext) -> DemoAdapter:
    return DemoAdapter(manifest)
```

### Regras do loader

- Varre `src/corretor/plugins/` e os caminhos de `PLUGIN_PATHS`
  (`:`-separados), ignorando diretórios que começam com `_`.
- Valida `manifest.yaml`, unicidade de `slug` e o contrato `create_adapter`.
- Plugin quebrado **não derruba a plataforma**: entra em `errors` e aparece em
  `/plugins` com status de erro.
- `status: discovery|disabled` não é coletado automaticamente.
- Novo plugin não pode alterar `domain`, `application` ou `infrastructure`.
- Contrato coberto por teste em `tests/plugins/`; todo plugin deve passá-lo.
- Receita declarativa (`mode: recipe`) entra na fase 1; o loader já reserva o
  campo.

### Resiliência a mudança de HTML

Prioridade de coleta, nesta ordem:

1. API/integração oficial;
2. endpoints internos (XHR/JSON) capturados no portal;
3. DOM com seletores semânticos;
4. fallback com LLM (fase futura, nunca caminho principal).

Regras obrigatórias:

- **Proibido** seletor posicional/frágil (`nth-child`, XPath absoluto, classes
  geradas como `_ngcontent-*`). Preferir `data-testid`, `name`, `aria-label`,
  `role`, label/texto visível e âncoras semânticas.
- Cada campo tem **lista de seletores com fallback** na receita declarativa
  versionada por seguradora, não espalhada no código.
- Colunas de tabela são mapeadas por **texto do cabeçalho**, nunca por índice.
- Todo resultado passa por validação de schema e de negócio (data, valor,
  formato de apólice, quantidade plausível).
- **Fail loud:** `SUCCESS`, `FAILED` ou `PARTIAL` por execução. “Zero
  pendências” só é válido se a coleta terminou 100%. Falha nunca vira lista
  vazia.
- Toda execução guarda evidência: JSON bruto + screenshot/trace em caso de erro.
- Watchdog: seguradora sem coleta bem-sucedida há mais de `STALE_AFTER_HOURS`
  (padrão 26h) gera alerta operacional.
- Auto-reparo só **sugere** nova receita; mudança em produção exige aprovação
  humana (dado financeiro).
- Testes de mutação de HTML (classes, ordem de colunas, wrappers, labels) são
  parte da definição de pronto da camada de extração.
- LLM, quando existir: recebe apenas o recorte necessário, com PII mascarada,
  saída estruturada e validação obrigatória; confiança baixa = `PARTIAL`.

## 7. Modelo de dados (MVP)

| Tabela | Campos principais |
|---|---|
| `insurers` | `id`, `slug` UNIQUE, `name`, `adapter`, `active`, `last_run_at`, `last_success_at` |
| `collection_runs` | `id`, `insurer_id`, `status`, `started_at`, `finished_at`, `items_found`, `new_count`, `resolved_count`, `error`, `evidence_path` |
| `policies` | `id`, `insurer_id`, `kind`, `policy_number`, `insured_name`, `branch`, `producer`; UNIQUE (`insurer_id`, `kind`, `policy_number`) |
| `installments` | `id`, `policy_id`, `number`, `due_date`, `amount_cents`, `boleto_url`, `boleto_code`, `external_id`, `alerts`, `payment_method`, `adjusted_vigency`, `insurer_status`, `is_active`, `first_seen_at`, `last_seen_at`; UNIQUE (`policy_id`, `number`, `due_date`) |
| `pendencies` | `id`, `installment_id` UNIQUE, `workflow_status`, `action`, `action_date`, `new_due_date`, `deadline`, `assigned_to`, `notes`, timestamps |
| `pendency_events` | `id`, `pendency_id`, `from_status`, `to_status`, `note`, `created_at` (auditoria) |

Convenções:

- dinheiro em **centavos** (`amount_cents`, inteiro); nunca float;
- datas de vencimento em `date` (ISO); timestamps em **UTC** (naive no SQLite);
- exibição no fuso `America/Sao_Paulo`;
- sem soft delete; presença no snapshot é controlada por `installments.is_active`.

### Tipos de pendência (`kind`)

- `PARCELA`: parcela de apólice já emitida (ex.: “Parcelas em Atraso”).
- `PROPOSTA`: proposta pendente / 1ª parcela (CCB) aguardando emissão
  (ex.: “Propostas Pendentes”).
- A chave de deduplicação inclui o tipo: (`kind`, `policy_number`,
  `installment_number`, `due_date`). Uma proposta e uma apólice com o mesmo
  número não colidem.
- O painel deve exibir o tipo e permitir filtrar por ele.
- O status exibido na visão planilha é derivado: abertos → `PENDENTE`;
  regularizada → `REGULARIZADA`; vencida → `VENCIDA`; descartada → `DESCARTADA`.
- A **visão planilha** (`/planilha`) e o `export-planilha.csv` devem manter as
  colunas operacionais: DATA AÇÃO, CIA, TIPO, SEGURADO, RAMO, FORMA PAGTO,
  VENCIMENTO, PARCELA PENDENTE, VIGENCIA AJUSTADA, AÇÃO, PRODUTOR, NOVO VENC,
  DATA LIMITE, STATUS.

### Status do workflow

```
DETECTADA → EM_ANALISE → AVISADA → REGULARIZADA
                                  ├→ VENCIDA
                                  └→ DESCARTADA
```

- Abertos: `DETECTADA`, `EM_ANALISE`, `AVISADA`.
- Fechados: `REGULARIZADA`, `VENCIDA`, `DESCARTADA` (VENCIDA ainda exige ação,
  mas sai da fila de “a vencer”).
- Se uma parcela regularizada reaparece no snapshot, reabre como `DETECTADA`
  com evento.
- `DESCARTADA` é decisão manual e **não** reabre automaticamente; se
  reaparecer, registrar evento e sinalizar para humano.
- `VENCIDA` é aplicada por rotina diária quando `due_date < hoje` e o status
  está aberto; a UI também calcula o atraso para exibição.

### Regras de diff

- Chave de deduplicação: (`insurer`, `kind`, `policy_number`,
  `installment_number`, `due_date`).
- Execução bem-sucedida: parcelas ativas ausentes do snapshot viram
  `is_active=False` e a pendência aberta vira `REGULARIZADA` automaticamente,
  com evento “não consta na coleta de <data>”.
- Execução falha: **nada** é marcado como resolvido; status anterior é mantido
  e o painel indica dados desatualizados.
- Reexecutar no mesmo dia deve ser idempotente (sem duplicar parcela, pendência
  ou evento).

## 8. Interface (Jinja + HTMX)

- Rótulos em **português**; código e nomes de domínio em inglês.
- `base.html` + partials: `dashboard_content`, `summary`, `table`, `row`,
  `runs_table`.
- Filtros (seguradora, status, busca) ficam **fora** do bloco trocado pelo
  HTMX, para não perder foco durante a digitação.
- `GET /dashboard` devolve partial; `GET /` devolve a página completa.
- `POST /collect` dispara coleta e devolve o partial atualizado com mensagem.
- Atualização de status na linha via `hx-post` + swap da `<tr>`.
- Página de detalhe da pendência com formulário completo e histórico de eventos.
- Exportação CSV com os filtros atuais.
- Página `/plugins` lista plugins carregados, versões, status e erros.
- Página `/sessions` lista o status da sessão por portal e o comando de
  renovação assistida. Falha de sessão no `POST /collect` abre um aviso com os
  portais afetados e link para `/sessions`.
- Acessibilidade básica: labels associados, foco visível, contraste, tabela
  semântica.
- Sem framework de frontend/build step. CSS próprio e enxuto.

## 9. Comandos (após o scaffold)

```bash
uv venv --python 3.12
uv pip install -e ".[dev,rpa]"
cp .env.example .env

uv run python -m corretor.cli init-db
uv run python -m corretor.cli seed          # demo + dados fictícios
uv run python -m corretor.cli collect all   # coleta manual
uv run python -m corretor.cli collect bradesco  # exige sessão salva
uv run python -m corretor.cli plugins       # lista plugins e erros
uv run uvicorn corretor.main:app --reload

uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Bradesco: gere a sessão com login manual (nunca salve a senha), copie o
`state.json` para `data/sessions/bradesco.json` e rode
`uv run python -m corretor.cli collect bradesco`. O plugin está com
`status: discovery`; a coleta manual funciona, mas ele não entra no seed nem no
agendador até ser promovido a `ready`.

Configuração por ambiente (`.env`): `DATABASE_URL`, `EVIDENCE_DIR`,
`ENABLE_SCHEDULER`, `SCHEDULER_HOUR`, `SCHEDULER_MINUTE`, `TIMEZONE`,
`STALE_AFTER_HOURS`, `PLUGIN_PATHS`, `SEED_DEMO`, `LOG_LEVEL`,
`BRADESCO_STATE_PATH`, `BRADESCO_ENDPOINT`, `BRADESCO_PROPOSALS_ENDPOINT`,
`BRADESCO_COLLECT_PARCELAS`, `BRADESCO_COLLECT_PROPOSALS`,
`BRADESCO_HEADLESS`, `BRADESCO_TIMEOUT_MS`.

API Bradesco: `BRADESCO_MODE` (`auto|api|html`), `BRADESCO_API_BASE_URL`,
`BRADESCO_API_TOKEN_URL`, `BRADESCO_API_CLIENT_ID`,
`BRADESCO_API_CLIENT_SECRET`, `BRADESCO_API_SECRET_SOURCE` (`env|keyring`),
`BRADESCO_API_KEYRING_SERVICE`, `BRADESCO_API_KEYRING_USERNAME`,
`BRADESCO_API_CNPJ_PROVEDOR`, `BRADESCO_API_CPF_CNPJ_CORRETOR`,
`BRADESCO_API_SCOPE`, `BRADESCO_API_FEATURE_TOGGLE`,
`BRADESCO_API_TOKEN_EXTRA`, `BRADESCO_API_CERT_PATH`,
`BRADESCO_API_KEY_PATH`, `BRADESCO_API_CA_BUNDLE`, `BRADESCO_API_VERIFY_TLS`,
`BRADESCO_API_TIMEOUT_MS`. Segredos vêm de cofre/keyring, nunca do repositório.

## 10. Convenções de código

- Type hints em todo código público; `from __future__ import annotations`.
- Modelos SQLAlchemy 2.0 com `Mapped[...]`; sem queries em templates/rotas.
- Erros de domínio explícitos (`AdapterError`, `ValidationError`); proibido
  `except` genérico que engole falha.
- Logs estruturados; nunca `print`. Nunca logar credenciais, CPF ou payload
  bruto com PII.
- Funções pequenas e testáveis; regra de negócio em `domain/` ou `application/`,
  não em rotas, templates ou plugins.
- Comentários em português apenas quando explicarem o “porquê”; código em inglês.
- Sem `sleep` fixo em automação de navegador: esperar por condição semântica.
- Datas: usar `date`/`datetime` tipados; nunca strings soltas no domínio.
- Plugin novo não altera o núcleo; se precisar de uma porta nova, primeiro
  atualize `domain`/`application` e este documento.

## 11. Testes

- `pytest` com banco SQLite temporário; **sem rede** nos testes.
- Fixtures de HTML/JSON **anonimizadas** por seguradora.
- Cobertura mínima obrigatória:
  - coleta cria parcelas/pendências e é idempotente;
  - parcela ausente em run de sucesso é regularizada;
  - run com falha não resolve nada e registra `FAILED`;
  - dados inválidos do adapter viram erro, não registro corrompido;
  - atualização de status gera evento;
  - página inicial e partial HTMX respondem 200;
  - filtros e exportação CSV;
  - loader de plugins descobre `demo`, ignora `_template` e isola plugin quebrado.
- Testes de mutação de HTML entram junto com o primeiro adapter real.
- Nenhum teste pode depender de `links.txt` ou da seguradora real.

## 12. Definição de pronto

Uma entrega só termina quando:

- `uv run pytest -q` passa;
- `uv run ruff check .` e `uv run ruff format --check .` passam;
- caminho de erro está testado (não só o caminho feliz);
- nenhum segredo/PII no diff;
- `docs/PRD.md`, README e AGENTS.md atualizados se escopo/arquitetura mudarem.

## 13. Roadmap

| Fase | Entrega |
|---|---|
| 0 | **Concluída:** Clean Architecture + loader de plugins + adapter demo + painel Jinja/HTMX + CLI + testes |
| 1 | **Bradesco Propostas:** API oficial implementada (onboarding em standby) + fallback HTML com `/sessions`; Parcelas em Atraso prontas atrás de flag; falta Allianz e receita declarativa com fallbacks |
| 2 | Scheduler diário, watchdog, digest interno, workflow completo e `/healthz` |
| 3 | Porto, testes de mutação, fallback LLM, Postgres/Docker; Bradesco em produção assistida |
| 4 | Integração com o sistema da corretora (API/webhook com idempotência) |

## 14. Perguntas em aberto

- “Parcela pendente” é parcela não paga pelo cliente ou comissão da corretora?
- Qual sistema receberá os dados (ERP/CRM) e por qual interface?
- Quantas seguradoras, apólices e usuários no escopo?
- Algum portal exige MFA, certificado ou captcha?
- Canal de alerta interno preferido (e-mail, WhatsApp, Telegram)?
- Onde hospedar (IP fixo é importante; portais podem bloquear datacenter)?
- Haverá mais de uma corretora (multi-tenant) ou apenas uma?
- Prazo de retenção de evidências e política de LGPD da corretora?

## 15. Não faça

- Não ler `senha` nem expor credenciais de `links.txt`.
- Não implementar adapter real sem spike de descoberta documentado.
- Não usar seletor posicional/frágil.
- Não retornar lista vazia quando a coleta falhar.
- Não adicionar pagamento/emissão de boleto.
- Não introduzir React/Vue/build step no MVP.
- Não rodar `git add .` a partir da home.
- Não commitar `data/`, `.env`, banco, evidências ou imagens com dados pessoais.
- Não colocar regra de negócio em plugin, rota ou template.
- Não fazer plugin importar `infrastructure`/`interfaces`.
