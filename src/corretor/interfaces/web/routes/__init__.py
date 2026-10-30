from . import dashboard, export, health, pendencies, planilha, plugins, runs

ROUTERS = (
    dashboard.router,
    pendencies.router,
    planilha.router,
    runs.router,
    plugins.router,
    export.router,
    health.router,
)

__all__ = ["ROUTERS"]
