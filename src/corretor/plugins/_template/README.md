# Template de plugin

Copie esta pasta para `plugins/<slug>/` (sem o `_`) e ajuste:

1. `manifest.yaml`: `slug`, `name`, `version`, `status`, `requires_session`.
2. `adapter.py`: implemente `fetch_pending()` retornando
   `list[RawInstallment]`.
3. `plugin.py`: mantenha `create_adapter(manifest, context)`.

Regras:

- `fetch_pending()` devolve um **snapshot completo**.
- Falha/parse parcial deve levantar `AdapterError` (nunca lista vazia).
- Sem credenciais no código; use `PluginContext`/variáveis de ambiente.
- Não importe `infrastructure`/`interfaces`.
- Rode os testes de contrato e o lint antes de ativar.
