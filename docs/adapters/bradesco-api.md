# Bradesco Seguros — API oficial (Propostas Pendentes)

> **Status:** adapter implementado, mas o onboarding comercial da Bradesco está
> em **standby** (burocracia de credenciais/certificados). A operação atual usa
> o adapter HTML com sessão assistida; este caminho fica pronto para quando o
> acesso for liberado.

## Por que API

- Sem navegador, sem reCAPTCHA e sem sessão de 8–9h.
- Token OAuth2 renovável; a coleta pode rodar diariamente sozinha.
- Contrato documentado, com JSON estável.
- Não exige guardar a senha do portal.

## API descoberta

Portal: `https://apiportal.bradescoseguros.com.br/`

Documentação da jornada Auto:
`https://apiportal.bradescoseguros.com.br/pages/Portal_UI_Bundle/auto.html`

Swagger de propostas:
`https://www.bradescoseguros.com.br/portalapis/Portal/api/auto/proposta.html`

```text
POST https://sauto.bradescoseguros.com.br/V2/WSBL-GerenciaCarteiraCsp/service/pendentes
Authorization: Bearer <JWT>
Content-Type: application/json
```

Corpo:

```json
{
  "propostasPendentesRequestDTO": {
    "cnpjProvedor": "<CNPJ da corretora/provedor>",
    "cpfCnpjCorretor": "<CPF/CNPJ do corretor>",
    "featureToggle": "0"
  }
}
```

Resposta (resumo):

```json
{
  "propostas": [
    {
      "proponente": {"nome": "...", "cpfCnpjProponente": 0},
      "vigencia": {
        "dtEfetivacao": "dd/mm/aaaa",
        "dtInicioVigencia": "dd/mm/aaaa",
        "dtFimVigencia": "dd/mm/aaaa"
      },
      "sucursal": "...",
      "agencia": "...",
      "numProposta": "...",
      "tpProposta": "...",
      "origem": "...",
      "modalidade": "...",
      "veiculo": {"modelo": "...", "anoFabricacao": 0, "anoModelo": 0, "placa": "..."},
      "vencimento": {
        "status": "...",
        "dtVencimento": "dd/mm/aaaa",
        "formaPagamento": "..."
      },
      "criticas": [
        {"descricao": "...", "causa": "...", "acoes": "...", "impacto": "..."}
      ],
      "statusVistoria": "...",
      "statusRastreador": "...",
      "statusRetificacao": "...",
      "statusLivelo": {"pendente": true, "mensagem": "..."}
    }
  ],
  "mensagemErro": null
}
```

Limitação: a API de propostas **não devolve o valor da 1ª parcela** nem o nome
do produtor. O adapter grava `amount_cents=0` e `producer=""`; a planilha
operacional não tem coluna de valor, então isso não bloqueia o MVP.

## Autenticação

1. O parceiro recebe `client-id` e `client-secret` pelo canal comercial/TI da
   Bradesco Seguros.
2. O token é obtido por **OAuth2 client credentials**:

```text
POST https://sauto.bradescoseguros.com.br/V2/Auth/
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
scope=web
client_id=<client-id>
client_secret=<client-secret>
```

3. A API usa `Authorization: Bearer <access_token>`.
4. Produção pode exigir **mTLS/certificado de cliente**. O adapter aceita
   `BRADESCO_API_CERT_PATH`, `BRADESCO_API_KEY_PATH` e
   `BRADESCO_API_CA_BUNDLE`.

Ambientes:
- Desenvolvimento: `https://sauto.dsv.bradescoseguros.com.br/V2/...`
- Homologação: `https://sauto.hml.bradescoseguros.com.br/V2/...`
- Produção: `https://sauto.bradescoseguros.com.br/V2/...`

O Swagger de autenticação lista o servidor DSV; confirme com a Bradesco o host
de homologação/produção antes de ligar em produção.

### Pontos a confirmar com a Bradesco

- O Swagger de autenticação lista o campo `token` como obrigatório, embora o
  fluxo `client_credentials` padrão não use esse campo. O adapter só o envia se
  `BRADESCO_API_TOKEN_EXTRA` for preenchido.
- O portal de credenciais cita um token em
  `https://susc.hml.bradescoseguros.com.br:8443/V3/Auth`; o Swagger da jornada
  Auto usa `https://sauto.../V2/Auth`. Confirmar qual host vale para cada
  ambiente.
- Confirmar os valores de `cnpjProvedor` e `cpfCnpjCorretor` e se há
  certificado mTLS/IP allowlist em produção.

## Onboarding (resumo do portal)

1. Ponto focal da corretora solicita ao contato comercial da Bradesco Seguros.
2. Comercial encaminha para TI-BS; TI abre chamado e gera as credenciais.
3. Credenciais voltam pelo comercial.
4. Para produção, o time de TI/Segurança do parceiro participa do processo.
5. O uso precisa estar liberado para a empresa parceira.

Documentação:
`https://apiportal.bradescoseguros.com.br/pages/Portal_UI_Bundle/documentacaotecnica/credenciais.html`

## Configuração no projeto

```env
BRADESCO_MODE=auto          # auto | api | html
BRADESCO_API_BASE_URL=https://sauto.bradescoseguros.com.br/V2/WSBL-GerenciaCarteiraCsp/service
BRADESCO_API_TOKEN_URL=https://sauto.bradescoseguros.com.br/V2/Auth
BRADESCO_API_CLIENT_ID=
BRADESCO_API_CLIENT_SECRET=
BRADESCO_API_SECRET_SOURCE=env   # env | keyring
BRADESCO_API_KEYRING_SERVICE=corretor-rpa
BRADESCO_API_KEYRING_USERNAME=bradesco-api
BRADESCO_API_CNPJ_PROVEDOR=
BRADESCO_API_CPF_CNPJ_CORRETOR=
BRADESCO_API_SCOPE=web
BRADESCO_API_FEATURE_TOGGLE=0
BRADESCO_API_TOKEN_EXTRA=
BRADESCO_API_CERT_PATH=
BRADESCO_API_KEY_PATH=
BRADESCO_API_CA_BUNDLE=
BRADESCO_API_VERIFY_TLS=true
BRADESCO_API_TIMEOUT_MS=60000
```

Modos:

- `auto`: usa API se `client-id`, `cnpjProvedor`, `cpfCnpjCorretor` e segredo
  estiverem configurados; senão usa HTML.
- `api`: força API e falha explicitamente se faltar configuração.
- `html`: força o adapter de sessão/HTML.

### Cofre

- **Local:** `BRADESCO_API_SECRET_SOURCE=keyring` e
  `keyring set corretor-rpa bradesco-api` (ou o comando do seu gerenciador).
- **Servidor:** injetar `BRADESCO_API_CLIENT_SECRET` via Vault/SOPS/systemd
  credentials; nunca commitar `.env`.
- Certificado e chave privada ficam fora do repositório, com permissão `600`.
- O segredo nunca é logado; o token fica em memória.

## Mapeamento para o domínio

| API | Campo interno |
|---|---|
| `proponente.nome` | `insured_name` |
| `sucursal` + `agencia` + `numProposta` | `policy_number` |
| `tpProposta` + `modalidade` + `origem` | `branch` |
| `vencimento.dtVencimento` | `due_date` |
| `vencimento.formaPagamento` | `payment_method` |
| `vencimento.status` | `insurer_status` |
| `vigencia.dtInicioVigencia` + `dtFimVigencia` | `adjusted_vigency` |
| `criticas[]` + status de vistoria/rastreador/retificação/Livelo | `alerts` |
| `numProposta` | `external_id` |
| — | `installment_number=1`, `kind=PROPOSTA` |
| — | `amount_cents=0` (não retornado pela API) |

## APIs relacionadas (para depois)

- `POST /parcelas` — Parcelas em Atraso (exige `chaveApolice`)
- `POST /parcelas-abertas` — Parcelas em Aberto
- `POST /listarParcelasApolice` — Parcelas por Apólice
- `POST /apolicesRenovar` — Apólices a Renovar
- `POST /historicoApolices` — Listar Apólices
- `POST /downloadParcela` — 2ª via de boleto
- `POST /efetivar` — Efetivar proposta

## Testes

O adapter é testado com `httpx.MockTransport`:

- fluxo OAuth + `/pendentes`;
- mapeamento do payload;
- erro de credenciais;
- configuração incompleta.

Não há chamada real sem credenciais. A homologação deve ser feita após o
onboarding, comparando o resultado com a tela de Propostas Pendentes.
