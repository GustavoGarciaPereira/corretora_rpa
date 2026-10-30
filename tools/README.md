# Ferramentas de descoberta

## `discover_portal.py`

Abre um portal de seguradora em um navegador **visível** para que você faça o
login manualmente. O script registra a navegação e as chamadas de rede
(XHR/fetch/document) e, ao final, salva uma captura completa da tela.

**O script não pede, não lê e não grava senha.** Ele também não lê
`links.txt` nem o arquivo `senha`.

### Pré-requisitos

- Python 3.12
- Google Chrome instalado (o script usa o canal `chrome`)
- Playwright disponível:

```bash
uv run --python 3.12 --with playwright python tools/discover_portal.py --slug bradesco
```

Alternativa com ambiente local:

```bash
uv venv --python 3.12 .venv
uv pip install playwright
uv run playwright install chromium
uv run python tools/discover_portal.py --slug bradesco
```

### Uso

```bash
# Abre o portal do Bradesco e espera o login manual
uv run --python 3.12 --with playwright python tools/discover_portal.py --slug bradesco

# Portal ainda não mapeado
uv run --python 3.12 --with playwright python tools/discover_portal.py \
  --slug porto --url "https://..."

# Smoke test sem interface e sem espera (não serve para login)
uv run --python 3.12 --with playwright python tools/discover_portal.py \
  --slug teste --url https://example.com --headless --no-wait
```

Durante a execução:

1. Faça o login no navegador que abrir.
2. Navegue até a tela de **parcelas pendentes** (ou equivalente).
3. Volte ao terminal e pressione **ENTER**.
4. Copie a URL final e os endpoints para `docs/adapters/<slug>.md`.

### O que é salvo

Em `data/discovery/<slug>/<timestamp>/`:

| Arquivo | Conteúdo |
|---|---|
| `summary.json` | URL inicial/final, título, frames, navegações e contagem de rede |
| `network.jsonl` | Método, URL, status e content-type de XHR/fetch/document |
| `page.png` | Screenshot da tela final |
| `page.html` | HTML da tela final |
| `trace.zip` | Trace do Playwright (snapshots e screenshots) |
| `state.json` | Cookies/sessão para reutilização |

`state.json`, `trace.zip`, `page.png` e `page.html` podem conter **dados
pessoais e tokens de sessão**. A pasta `data/` é ignorada pelo Git; não
compartilhe nem commite esses arquivos.

## `capture_bradesco_parcelas.py`

Captura específica da lista **Parcelas em Atraso** do Bradesco Auto. Reutiliza
um `state.json` já autenticado, fecha o modal promocional (ex.: Seguros Friday)
e o banner de cookies (`#adopt-reject-all-button`), clica em “Ver detalhes” do
card e salva o payload JSON de `/api/parcelas/v1/list`.

```bash
python3.12 tools/capture_bradesco_parcelas.py \
  --url "<url-da-area-auto>" \
  --state data/discovery/bradesco/<timestamp>/state.json
```

Saída em `data/discovery/bradesco/<timestamp>/`:

- `page.html`, `page.png`, `trace.zip`, `state.json`
- `network.jsonl`
- `payloads/` com os corpos das chamadas de API
- `payloads.json` com o índice dos corpos
- `summary.json`

A sessão pode expirar; nesse caso o script avisa e é necessário fazer login
manual novamente. O script não automatiza captcha.

### Depois da descoberta

Preencha `docs/adapters/<slug>.md` com:

- tipo de autenticação (senha, MFA, certificado, captcha);
- caminho de navegação até a consulta;
- endpoints reaproveitáveis;
- seletores semânticos e fallbacks;
- riscos e termos de uso.

Não copie credenciais para o documento.
