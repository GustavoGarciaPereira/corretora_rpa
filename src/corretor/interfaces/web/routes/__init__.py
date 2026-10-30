from . import dashboard, export, health, pendencies, plugins, runs

ROUTERS = (
    dashboard.router,
    pendencies.router,
    runs.router,
    plugins.router,
    export.router,
    health.router,
)

__all__ = ["ROUTERS"]
