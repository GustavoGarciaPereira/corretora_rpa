from __future__ import annotations

import json
from dataclasses import dataclass

from pydantic import SecretStr

from .config import Settings


class CredentialsError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LoginCredentials:
    user: str
    password: str


def _keyring():
    try:
        import keyring
    except ImportError as exc:
        raise CredentialsError("keyring não instalado; instale o extra 'vault'") from exc
    return keyring


def resolve_bradesco_credentials(settings: Settings) -> LoginCredentials:
    if settings.bradesco_credential_source == "env":
        user = settings.bradesco_login_user.strip()
        secret = settings.bradesco_login_password
        password = secret.get_secret_value() if isinstance(secret, SecretStr) else ""
        if not user or not password:
            raise CredentialsError("BRADESCO_LOGIN_USER/BRADESCO_LOGIN_PASSWORD não configurados")
        return LoginCredentials(user=user, password=password)

    keyring = _keyring()
    try:
        raw = keyring.get_password(
            settings.bradesco_keyring_service, settings.bradesco_keyring_username
        )
    except Exception as exc:  # noqa: BLE001
        raise CredentialsError(
            "falha ao acessar o keyring; verifique o backend do sistema"
        ) from exc
    if not raw:
        raise CredentialsError("credenciais do Bradesco não cadastradas no keyring")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise CredentialsError("credenciais inválidas no keyring") from exc
    user = str(data.get("user", "")).strip()
    password = str(data.get("password", ""))
    if not user or not password:
        raise CredentialsError("credenciais incompletas no keyring")
    return LoginCredentials(user=user, password=password)


def credentials_available(settings: Settings) -> bool:
    try:
        resolve_bradesco_credentials(settings)
        return True
    except CredentialsError:
        return False


def store_bradesco_credentials(settings: Settings, user: str, password: str) -> None:
    if not user.strip() or not password:
        raise CredentialsError("usuário e senha são obrigatórios")
    keyring = _keyring()
    keyring.set_password(
        settings.bradesco_keyring_service,
        settings.bradesco_keyring_username,
        json.dumps({"user": user.strip(), "password": password}),
    )


def clear_bradesco_credentials(settings: Settings) -> None:
    keyring = _keyring()
    try:
        keyring.delete_password(
            settings.bradesco_keyring_service, settings.bradesco_keyring_username
        )
    except Exception as exc:  # noqa: BLE001
        raise CredentialsError(f"não foi possível remover: {exc.__class__.__name__}") from exc
