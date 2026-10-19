import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError

from watchtower.api.errors import ApiError, api_error_handler
from watchtower.api.operator_auth import (
    OPERATOR_ROLE,
    PUBLISHER_ROLE,
    CognitoTokenVerifier,
    OperatorAuthenticator,
    OperatorIdentityUnavailable,
    OperatorPrincipal,
    Publisher,
    require_operator,
)
from watchtower.core.config import Settings
from watchtower.main import create_app

ISSUER = "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_example"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
CLIENT_ID = "watchtower-client"


@dataclass
class SigningKey:
    key: Any


class StaticSigningKeyClient:
    def __init__(self, key: Any) -> None:
        self.key = SigningKey(key)

    def get_signing_key_from_jwt(self, token: str) -> SigningKey:
        return self.key


class FixedVerifier:
    def __init__(self, principal: OperatorPrincipal) -> None:
        self.principal = principal

    def verify(self, token: str) -> OperatorPrincipal:
        return self.principal


class UnavailableVerifier:
    def verify(self, token: str) -> OperatorPrincipal:
        raise OperatorIdentityUnavailable


@pytest.fixture(scope="module")
def rsa_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def oidc_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": SecretStr("postgresql+psycopg://user:secret@localhost/watchtower"),
        "operator_auth_mode": "oidc",
        "oidc_issuer": ISSUER,
        "oidc_jwks_url": JWKS_URL,
        "oidc_client_id": CLIENT_ID,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]


def access_token(
    key: rsa.RSAPrivateKey,
    *,
    groups: list[str],
    issuer: str = ISSUER,
    client_id: str = CLIENT_ID,
    token_use: str = "access",
    expires_in: timedelta = timedelta(minutes=5),
    include_jti: bool = True,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "iss": issuer,
        "sub": "cognito-subject-123",
        "client_id": client_id,
        "token_use": token_use,
        "username": "analyst@example.test",
        "cognito:groups": groups,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
    }
    if include_jti:
        claims["jti"] = "token-id-123"
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-key"})


def verifier(key: rsa.RSAPrivateKey) -> CognitoTokenVerifier:
    return CognitoTokenVerifier(
        oidc_settings(),
        jwks_client=StaticSigningKeyClient(key.public_key()),
    )


def auth_app(authenticator: OperatorAuthenticator) -> FastAPI:
    app = FastAPI()
    app.state.operator_authenticator = authenticator
    app.add_exception_handler(ApiError, api_error_handler)  # pyright: ignore[reportArgumentType]

    @app.get("/operator", dependencies=[Depends(require_operator)])
    def operator_route() -> dict[str, str]:
        return {"status": "operator"}

    @app.post("/publish")
    def publisher_route(principal: Publisher) -> dict[str, str]:
        return {"subject": principal.subject}

    return app


def test_cognito_access_token_verification_and_roles(rsa_key: rsa.RSAPrivateKey) -> None:
    token_verifier = verifier(rsa_key)
    operator = token_verifier.verify(access_token(rsa_key, groups=["operator"]))
    publisher = token_verifier.verify(access_token(rsa_key, groups=["publisher"]))

    assert operator == OperatorPrincipal(
        subject="cognito-subject-123",
        display_identity="analyst@example.test",
        roles=frozenset({OPERATOR_ROLE}),
        auth_method="oidc",
        token_id="token-id-123",
    )
    assert publisher.roles == frozenset({OPERATOR_ROLE, PUBLISHER_ROLE})


@pytest.mark.parametrize(
    "token_overrides",
    [
        {"issuer": "https://issuer.example.test/wrong"},
        {"client_id": "wrong-client"},
        {"token_use": "id"},
        {"expires_in": timedelta(minutes=-5)},
        {"include_jti": False},
    ],
)
def test_cognito_rejects_invalid_access_tokens(
    rsa_key: rsa.RSAPrivateKey,
    token_overrides: dict[str, object],
) -> None:
    token = access_token(rsa_key, groups=["operator"], **token_overrides)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as captured:
        verifier(rsa_key).verify(token)

    assert captured.value.status_code == 401
    assert captured.value.code == "operator_auth_failed"


def test_operator_routes_enforce_bearer_roles_and_do_not_log_tokens(
    rsa_key: rsa.RSAPrivateKey,
    caplog: pytest.LogCaptureFixture,
) -> None:
    authenticator = OperatorAuthenticator(oidc_settings(), oidc_verifier=verifier(rsa_key))
    operator_token = access_token(rsa_key, groups=["operator"])
    publisher_token = access_token(rsa_key, groups=["publisher"])
    outsider_token = access_token(rsa_key, groups=["unrelated"])
    headers = {"Authorization": f"Bearer {operator_token}"}
    app = auth_app(authenticator)
    audit_logger = logging.getLogger("watchtower.api.operator_auth")

    audit_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.INFO, logger="watchtower.api.operator_auth"):
            with TestClient(app) as client:
                missing = client.get("/operator")
                static_only = client.get(
                    "/operator",
                    headers={"X-WATCHTOWER-Operator-Token": "ignored-static-token"},
                )
                operator = client.get("/operator", headers=headers)
                outsider = client.get(
                    "/operator",
                    headers={"Authorization": f"Bearer {outsider_token}"},
                )
                forbidden = client.post("/publish", headers=headers)
                published = client.post(
                    "/publish",
                    headers={"Authorization": f"Bearer {publisher_token}"},
                )
    finally:
        audit_logger.removeHandler(caplog.handler)

    assert missing.status_code == static_only.status_code == 401
    assert operator.status_code == 200
    assert outsider.status_code == 403
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "operator_forbidden"
    assert published.json() == {"subject": "cognito-subject-123"}
    assert operator_token not in caplog.text
    assert publisher_token not in caplog.text
    assert any(
        getattr(record, "fields", {}).get("subject") == "cognito-subject-123"
        for record in caplog.records
    )


def test_jwks_outage_returns_stable_unavailable_error() -> None:
    authenticator = OperatorAuthenticator(
        oidc_settings(),
        oidc_verifier=UnavailableVerifier(),
    )
    with TestClient(auth_app(authenticator)) as client:
        response = client.get(
            "/operator",
            headers={"Authorization": "Bearer opaque-token"},
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "operator_auth_unavailable"


def test_production_settings_fail_closed_without_complete_edge_and_oidc() -> None:
    database_url = SecretStr("postgresql+psycopg://user:secret@localhost/watchtower")
    with pytest.raises(ValidationError, match="OPERATOR_AUTH_MODE=oidc"):
        Settings(
            _env_file=None,  # pyright: ignore[reportCallIssue]
            database_url=database_url,
            environment="production",
        )
    with pytest.raises(ValidationError, match="OIDC authentication requires"):
        Settings(
            _env_file=None,  # pyright: ignore[reportCallIssue]
            database_url=database_url,
            environment="production",
            operator_auth_mode="oidc",
        )
    with pytest.raises(ValidationError, match="TRUSTED_HOSTS allowlist"):
        oidc_settings(environment="production")
    with pytest.raises(ValidationError, match="PROXY_TRUSTED_HOSTS allowlist"):
        oidc_settings(environment="production", trusted_hosts=["api.watchtower.example"])

    configured = oidc_settings(
        environment="production",
        trusted_hosts=["api.watchtower.example"],
        proxy_trusted_hosts=["10.0.0.0/16"],
    )
    assert configured.operator_token is None


def test_static_token_is_forbidden_in_production() -> None:
    with pytest.raises(ValidationError, match="OPERATOR_TOKEN is forbidden"):
        oidc_settings(
            environment="production",
            operator_token=SecretStr("a" * 32),
            trusted_hosts=["api.watchtower.example"],
            proxy_trusted_hosts=["10.0.0.0/16"],
        )


def test_production_host_allowlist_rejects_unapproved_host() -> None:
    settings = oidc_settings(
        environment="production",
        trusted_hosts=["api.watchtower.example"],
        proxy_trusted_hosts=["10.0.0.0/16"],
    )
    engine = MagicMock()
    with patch("watchtower.main.build_engine", return_value=engine):
        with TestClient(
            create_app(settings),
            base_url="https://api.watchtower.example",
        ) as client:
            allowed = client.get("/health")
            rejected = client.get("/health", headers={"Host": "evil.example"})

    assert allowed.status_code == 200
    assert rejected.status_code == 400
