# Bradesco Seguros — descoberta do portal

> Status: **em descoberta**. Nenhum adapter de produção deve ser implementado
> antes de concluir este documento e validar os termos de uso.

## Portal

- URL inicial: `https://wwwn.bradescoseguros.com.br/pnegocios2/wps/portal/portaldenegociosnovo/`
- Data da descoberta: 2026-10-30
- Responsável: descoberta assistida (headless, sem login)
- Navegador/canal usado: Playwright 1.64.0 + Google Chrome (headless)
- Pasta da evidência: `data/discovery/bradesco/20261030T034210Z/` (não versionar)

### Primeira captura (sem login)

- Título: `Login | Bradesco Seguros - Portal de Negócios`
- URL final: a mesma URL inicial (a página de login é renderizada no próprio portal)
- Frames: 5 (incluindo `recaptcha/api2/anchor` e `recaptcha/api2/bframe`)
- Rede: 19 entradas XHR/fetch/document, majoritariamente assets, analytics,
  consentimento e reCAPTCHA.

## Autenticação

- [x] Login + senha (formulário exibido)
- [ ] MFA (SMS/app/token) — não verificável sem login
- [ ] Certificado digital — não verificável sem login
- [x] Captcha — **Google reCAPTCHA v2 invisível** detectado
- [ ] Outro:

A página de login oferece os perfis **Corretor**, **Assessoria** e **Produtor**,
com botões `Continuar` e `Entrar`, além de `Esqueci a senha` e
`Faça aqui seu primeiro acesso`.

Observações de sessão (tempo de expiração, abas, popups): a descobrir após o
login manual.

## Caminho até as parcelas pendentes

1. Acessar a URL inicial do Portal de Negócios.
2. Na tela de login, selecionar o perfil **Corretor** (ou o perfil aplicável).
3. Informar login e senha **manualmente** (nunca por script/chat).
4. Resolver o reCAPTCHA apresentado.
5. Clicar em `Entrar`/`Continuar`.
6. Navegar até a consulta de parcelas pendentes.
7. Registrar a URL final e as chamadas de rede da consulta.

URL final da consulta: **pendente de login manual.**

Frames/iframes envolvidos: **pendente de login manual.**

## Endpoints observados

| Método | URL (sem query sensível) | Status | Uso |
|---|---|---|---|
| GET | `/pnegocios2/wps/portal/portaldenegociosnovo/` | 200 | Documento do portal/login |
| GET | `static.bradescoseguros.com.br/@bsds-lib-component/...` | 200 | Assets de UI |
| GET | `google.com/recaptcha/api2/anchor` | 200 | reCAPTCHA |
| GET | `google.com/recaptcha/api2/bframe` | 200 | reCAPTCHA |
| POST | `disclaimer-api.goadopt.io/api/tag/get-consent` | 200 | Consentimento/cookies |
| POST | `analytics-fe.digital-cloud-west.medallia.com/api/web/events` | 200 | Analytics |

Nenhum endpoint de parcelas pendentes foi observado sem autenticação.

## Seletores e âncoras

Ainda não aplicável à tela de dados. Na tela de login, foram observados textos
semânticos (`Corretor`, `Assessoria`, `Produtor`, `Entrar`, `Continuar`) e os
frames de reCAPTCHA. A receita de extração só deve ser escrita após a captura
da tela autenticada.

| Campo | Estratégia principal | Fallback | Observações |
|---|---|---|---|
| Seguradora | | | |
| Segurado | | | |
| Apólice | | | |
| Ramo | | | |
| Parcela | | | |
| Vencimento | | | |
| Valor | | | |
| Produtor | | | |
| Boleto | | | |

## Evidências

- `summary.json`: URL, título, frames, navegações e contagem de rede.
- `network.jsonl`: 19 entradas iniciais (assets, analytics, consentimento,
  reCAPTCHA).
- `page.png` / `page.html`: tela de login.
- `trace.zip`: trace do Playwright.
- `state.json`: sessão anônima (sem login).

## Riscos e observações

- **reCAPTCHA v2 invisível** no login: automação de autenticação não é
  permitida/confiável. O caminho correto é login manual assistido e reutilização
  de sessão.
- Headless pode ser tratado de forma diferente pelo portal; a captura
  autenticada deve ser feita em navegador visível.
- Termos de uso / restrições de automação: **validar antes de produção**.
- Necessidade de intervenção humana: provável no login (captcha/MFA).
- Dados pessoais observados na tela: nenhum nesta captura (pré-login).

## Decisão de estratégia

- [ ] API/integração oficial
- [ ] Endpoint interno
- [ ] DOM com Playwright
- [ ] Bloqueado (motivo):

Justificativa: **pendente**. A prioridade é verificar se existe API/integração
oficial para corretor; caso contrário, avaliar endpoint interno após login
manual e, por último, DOM com Playwright usando sessão assistida.

## Próximo passo

Executar a descoberta com navegador visível e login manual:

```bash
uv run --python 3.12 --with playwright python tools/discover_portal.py --slug bradesco
```

Navegar até a tela de parcelas pendentes, pressionar ENTER e atualizar este
documento com URL, frames, endpoints e seletores. **Não registrar credenciais.**
