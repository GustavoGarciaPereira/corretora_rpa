from .adapter_error import AdapterError


class AdapterSessionExpired(AdapterError):
    """Sessão do portal expirou; requer intervenção humana."""
