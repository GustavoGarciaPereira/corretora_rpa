from .domain_error import DomainError


class PluginError(DomainError):
    """Manifest ou contrato de plugin inválido."""
