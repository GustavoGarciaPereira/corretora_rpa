from .domain_error import DomainError


class ValidationError(DomainError):
    """Dados retornados pelo adapter são inválidos."""
