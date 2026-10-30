from .adapter_error import AdapterError


class AdapterNotConfigured(AdapterError):
    """Adapter existe, mas falta configuração (sessão, URL etc.)."""
