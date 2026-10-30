from __future__ import annotations

import pytest
from pydantic import SecretStr

from corretor.infrastructure.config import Settings
from corretor.infrastructure.credentials import (
    CredentialsError,
    credentials_available,
    resolve_bradesco_credentials,
)


def test_resolve_credenciais_por_env_separa_cnpj_e_cpf() -> None:
    settings = Settings(
        bradesco_credential_source="env",
        bradesco_login="11222333000181",
        bradesco_login_user="12345678901",
        bradesco_login_password=SecretStr("segredo"),
    )
    credentials = resolve_bradesco_credentials(settings)
    assert credentials.login == "11222333000181"
    assert credentials.user == "12345678901"
    assert credentials.password == "segredo"
    assert credentials_available(settings) is True


def test_login_user_e_fallback_quando_login_vazio() -> None:
    settings = Settings(
        bradesco_credential_source="env",
        bradesco_login="",
        bradesco_login_user="12345678901",
        bradesco_login_password=SecretStr("segredo"),
    )
    credentials = resolve_bradesco_credentials(settings)
    assert credentials.login == "12345678901"
    assert credentials.user == "12345678901"


def test_env_incompleto_falha() -> None:
    settings = Settings(
        bradesco_credential_source="env",
        bradesco_login="",
        bradesco_login_user="",
        bradesco_login_password=None,
    )
    with pytest.raises(CredentialsError):
        resolve_bradesco_credentials(settings)
    assert credentials_available(settings) is False
