# Bradesco Seguros — descoberta do portal

> Status: **descoberta avançada**. O caminho preferencial agora é a **API
> oficial** (`docs/adapters/bradesco-api.md`): Propostas Pendentes via
> OAuth2/JWT. Este documento descreve o fallback HTML/sessão, usado enquanto as
> credenciais oficiais não forem liberadas.

## Portal

- URL inicial: `https://wwwn.bradescoseguros.com.br/pnegocios2/wps/portal/portaldenegociosnovo/`
- Área logada (Auto): `https://wwwn.bradescoseguros.com.br/pnegocios/wps/myportal/portalnegocios/arealogada/auto/!ut/p/...#/`
- Data da descoberta: 2026-10-30
- Navegador: Playwright 1.64.0 + Google Chrome
- Evidências:
  - `data/discovery/bradesco/20261030T034210Z/` — login (sem autenticação)
  - `data/discovery/bradesco/20261030T035459Z/` — Propostas Pendentes
  - `data/discovery/bradesco/20261030T040647Z/` — Parcelas em Atraso + payload JSON

## Autenticação

- Login + senha.
- **Google reCAPTCHA v2 invisível** na tela de login.
- MFA/certificado: não verificável sem login; validar com a corretora.
- Sessão: reutilizável via `storage_state.json` do Playwright.
- Quando a sessão expirar: pausar e pedir **login manual**. Não automatizar
  captcha.

## Overlays que bloqueiam cliques

Antes de interagir com os cards, fechar os dois overlays:

1. **Modal promocional** (ex.: “Live de lançamento da Seguros Friday”):
   - container: `div.modal-aviso` contendo o texto `Seguros Friday`;
   - fechar: `button.close[data-dismiss="modal"][data-analytics-label*="Seguros Friday"]`;
   - se o clique for interceptado, usar clique forçado/JS e remover o
     `.modal-backdrop` residual do Bootstrap.
2. **Banner de cookies do AdOpt**:
   - botão: `#adopt-reject-all-button` (`Rejeitar cookies não necessários`).

O modal promocional pode reaparecer em novas sessões. O checkbox
`#checkbox-view` (“Não quero mais visualizar esta mensagem”) grava a dispensa
em cookie; usar apenas se a corretora quiser suprimir esse aviso de vez.

## Caminho — Parcelas em Atraso (implementado, desativado por padrão)

1. Login manual.
2. Home logada → **AUTO**.
3. No dashboard, localizar o card **Parcelas em Atraso**.
4. Clicar em **Ver detalhes**.
5. A tabela é carregada por uma chamada JSON.

### Card e tabela

- Card: `bspn-card` contendo o texto `Parcelas em Atraso`.
- Botão: `.bspn-card-ver-detalhes-btn` com texto `Ver detalhes`.
- Após abrir, o botão muda para `Ocultar detalhes`.
- Tabela visível: colunas Segurado, Suc-Ag/Apól/End, Modalidade, Parcela,
  Valor (R$), Vencimento, Vigência ajustada, Data Limite, Boleto e Alertas.

### Endpoint principal

```text
GET /pnegocios/wps/PA_BSPN-DBoardAuto-PU/api/parcelas/v1/list
Content-Type: application/json
```

A chamada usa a sessão autenticada. Não foram observados parâmetros de query
na captura; validar se filtros de data/paginação são enviados em outros fluxos.

### Estrutura do payload (nomes de campos)

```text
{
  "parcelas": [
    {
      "idParcela": int,
      "segurado": {
        "nome": str,
        "email": str,
        "cpfCnpj": str,
        "telefones": ...
      },
      "corretor": { "codigo": ... },
      "sucursal": str,
      "apolice": int,
      "item": int,
      "endosso": str,
      "prestacao": str,
      "pagamento": str,
      "premio": float,
      "vencimento": str,
      "dataLimite": str,
      "vigAjustada": str,
      "criticidade": bool,
      "ramoSeguro": int,
      "companhiaSeguradora": int,
      "parcSistemaCobranca": str,
      "dvParcSistemaCobranca": int,
      "modalidade": str,
      "agenciaProdutora": str,
      "historicoEmail": ...,
      "outrasParcelas": ...,
      "qtdOutrasParcelas": int,
      "sinistro": bool,
      "apoliceEmCancelamento": bool
    }
  ],
  "situacaoSistemas": {
    "sistemasDisponiveis": bool,
    "mensagem": str
  },
  "exibirSinistro": bool,
  "pagamentoCartao": bool,
  "corretor": { ... },
  "produtor": bool
}
```

### Mapa para o domínio

| JSON | Campo interno |
|---|---|
| `parcelas[].idParcela` | chave externa da parcela |
| `segurado.nome` | `insured_name` |
| `segurado.cpfCnpj` | CPF/CNPJ (mascarar) |
| `sucursal` + `apolice` + `item` + `endosso` | `policy_number` / identificação |
| `prestacao` | `installment_number` |
| `premio` | `amount` |
| `vencimento` | `due_date` |
| `dataLimite` | `deadline` |
| `vigAjustada` | `adjusted_vigency` |
| `pagamento` | `payment_method` |
| `parcSistemaCobranca` + `dvParcSistemaCobranca` | boleto |
| `criticidade` | alerta de crítica |
| `sinistro` | alerta de sinistro |
| `apoliceEmCancelamento` | alerta de cancelamento |
| `ramoSeguro` | ramo |
| `companhiaSeguradora` | seguradora |
| `modalidade` | modalidade/produto |
| `corretor.codigo` | produtor/corretor |
| `segurado.email`, `segurado.telefones` | contato (PII; usar com cautela) |

### Validação obrigatória

- Se `situacaoSistemas.sistemasDisponiveis` for `false`, a coleta deve ser
  `PARTIAL`/`FAILED` e nunca “sem pendências”.
- Comparar `len(parcelas)` com a quantidade exibida no card/contador.
- Validar `idParcela`, `apolice`, `prestacao`, `vencimento` e `premio` antes de
  gravar.
- Se o payload vier vazio com `sistemasDisponiveis=true`, é um vazio válido;
  registrar evidência mesmo assim.

## Propostas Pendentes (escopo atual)

A tela **Propostas Pendentes** é outra funcionalidade: primeira parcela (CCB)
aguardando pagamento para emissão da apólice. Não confundir com parcelas em
atraso de apólices emitidas. O painel diferencia os tipos com `PARCELA` e
`PROPOSTA`.

- Container: `#container-propostas-pendentes-table`
- Tabela: `#propostas-pendentes`
- Endpoint: `GET /pnegocios/wps/PA_BSPN-DBoardAuto-PU/api/propostas/pendentes/v1/view`
  (retorna fragmento HTML)
- Exportação declarada: `.../api/propostas/pendentes/v1/xls-propostas-pendentes`
- Contadores: `GET .../api/propostas/v1/contadores`
- Linhas: `tbody tr[data-proposta]`
- Quantidade esperada: `data-qtd-propostas-pendentes` na tabela.

Campos usados no parser:

| Dado | Origem |
|---|---|
| Proponente | `data-nome-segurado` |
| Proposta | `data-proposta` + `data-sucursal` + `data-agencia` |
| Vencimento da 1ª parcela | `td.td-data-vencimento` (fallback `data-order` de `td.td-vencimento`) |
| Valor da 1ª parcela | `data-valor-primeira-parcela` (fallback regex no texto da célula) |
| Boleto | `data-codigo-boleto` |
| Segmento | `data-especialidade` |
| Status da 1ª parcela | `data-vencimento-status` |
| Retificação/vistoria/rastreador | `data-retificacao`, `data-vistoria-status`, `data-rastreador-status` |
| Produtor | `data-corretor` / `data-nome-corretor` |
| Tipo | fixo `PROPOSTA`; parcela = `PARCELA` |

O parser valida a quantidade de linhas contra
`data-qtd-propostas-pendentes`; divergência gera `AdapterError` (nunca
snapshot parcial silencioso).

## Decisão de estratégia

- [x] **API JSON** para Parcelas em Atraso.
- [x] **HTML do endpoint** para Propostas Pendentes.
- [x] DOM/Playwright como fallback e para login manual.
- [x] API/integração oficial — adapter implementado em `bradesco-api.md`;
  acesso/credenciais pendentes de onboarding.
- [ ] Exportação XLS — avaliar como contingência.

Justificativa: `/api/parcelas/v1/list` entrega JSON; propostas só têm o
fragmento HTML. Ambos usam a mesma sessão e são normalizados para o mesmo
contrato `RawInstallment`, diferenciados por `kind`.

## Riscos e observações

- reCAPTCHA no login: intervenção humana obrigatória.
- Sessão expira; prever `AGUARDANDO_INTERVENCAO`.
- Banner de cookies pode bloquear cliques no modo navegador.
- Payload contém PII (nome, CPF/CNPJ, e-mail, telefone): mascarar, restringir
  acesso e nunca commitar evidências.
- Termos de uso/automação: validar antes de produção.
- `situacaoSistemas=false` ou resposta incompleta deve gerar falha explícita.

## Plugin implementado (2026-10-30)

O plugin `src/corretor/plugins/bradesco/` está implementado:

- `adapter.py`: abre o Playwright com `storage_state`, chama o endpoint JSON e
  valida a sessão;
- `mapping.py`: converte o payload JSON de parcelas em `RawInstallment`;
- `proposals.py`: parseia o HTML de propostas e gera `RawInstallment` com
  `kind=PROPOSTA`;
- `plugin.py` / `manifest.yaml`: registro plug-and-play, `status: discovery`,
  `requires_session: true`;
- evidência bruta salva por execução em `data/evidence/`.

Teste real:

```bash
cp data/discovery/bradesco/<timestamp>/state.json data/sessions/bradesco.json
uv run python -m corretor.cli collect bradesco
# [OK] Bradesco Seguros: Sucesso itens=1 novas=1 resolvidas=0
```

O teste padrão retorna **1 proposta pendente**. A proposta veio com
`Boleto`, vigência `22/10/2026 a 22/10/2027` e status de portal
`Processando nova chance`.

Para incluir também as parcelas em atraso:

```bash
BRADESCO_COLLECT_PARCELAS=true uv run python -m corretor.cli collect bradesco
# [OK] Bradesco Seguros: Sucesso itens=2 novas=2 resolvidas=0
```

A visão `/planilha` e o `export-planilha.csv` expõem essas colunas no formato
do controle operacional.

## Renovação assistida pela web

A página `/sessions` tem o botão **Renovar sessão agora**:

1. o backend executa `tools/renew_bradesco.py`;
2. o Chrome abre na máquina do operador;
3. o operador faz o login manual (reCAPTCHA/MFA);
4. ao detectar a área logada, o script salva o `state.json` automaticamente;
5. a página faz polling e mostra “Sessão renovada”;
6. o operador volta ao painel e clica em “Coletar agora”.

O script não lê senha, não contorna captcha e não sobrescreve a sessão se o
login não for concluído. Em servidor sem `DISPLAY`, usar noVNC ou agente local.
Não expor a aplicação publicamente sem autenticação.

### Login automático (tentativa)

Se `BRADESCO_AUTO_LOGIN_ENABLED=true` e houver credenciais no cofre, a página
`/sessions` mostra **Tentar login automático**. O backend executa
`tools/auto_login_bradesco.py` em background, preenche CPF/CNPJ e senha e
salva o `state.json` se a área logada aparecer.

- Credenciais: keyring (`corretor credentials set bradesco`) ou
  `BRADESCO_CREDENTIAL_SOURCE=env` com `BRADESCO_LOGIN` (CNPJ/login do campo
  CPF/CNPJ), `BRADESCO_LOGIN_USER` (CPF fallback) e
  `BRADESCO_LOGIN_PASSWORD` injetados por Vault.
- Se o portal exigir reCAPTCHA/MFA, o worker retorna `captcha` e **não
  contorna**; a UI oferece a renovação manual.
- A coleta automática e o “Coletar agora” também tentam renovar sozinhos
  quando a sessão expira (`NEEDS_ATTENTION`) e repetem a coleta após sucesso.
- O worker não usa a senha em argumentos de linha de comando e não a grava em
  logs. Validar os termos de uso antes de habilitar.

## Próximo passo

1. Solicitar à Bradesco as credenciais da **API oficial de Propostas
   Pendentes** (homologação e produção) e confirmar `cnpjProvedor` /
   `cpfCnpjCorretor`.
2. Configurar o cofre (`BRADESCO_API_SECRET_SOURCE=keyring` ou Vault) e validar
   o adapter da API em homologação.
3. Manter o HTML como fallback até a API estar liberada.
4. Manter **Propostas Pendentes** como escopo atual; parcelas seguem atrás de
   `BRADESCO_COLLECT_PARCELAS=true`.
5. Repetir a descoberta para Allianz/Porto usando o mesmo contrato.

**Nunca** registrar credenciais neste documento ou nos testes.
