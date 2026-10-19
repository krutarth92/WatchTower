"""Identity-aware authentication and authorization for administrative routes."""

import logging
from dataclasses import dataclass
from hmac import compare_digest
from typing import Annotated, Any, Literal, Protocol

import jwt
from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

from watchtower.api.errors import ApiError, get_request_id
from watchtower.core.config import Settings

OPERATOR_HEADER = "X-WATCHTOWER-Operator-Token"
OPERATOR_ROLE = "operator"
PUBLISHER_ROLE = "publisher"
operator_header = APIKeyHeader(name=OPERATOR_HEADER, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("watchtower.api.operator_auth")


@dataclass(frozen=True, slots=True)
class OperatorPrincipal:
    subject: str
    display_identity: str
    roles: frozenset[str]
    auth_method: Literal["static", "oidc"]
    token_id: str | None = None

    def has_role(self, role: str) -> bool:
        return role in self.roles


class SigningKeyClient(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class TokenVerifier(Protocol):
    def verify(self, token: str) -> OperatorPrincipal: ...


class OperatorIdentityUnavailable(RuntimeError):
    pass


class CognitoTokenVerifier:
    """Verify Cognito access tokens with a bounded, rotating JWKS cache."""

    def __init__(
        self,
        settings: Settings,
        jwks_client: SigningKeyClient | None = None,
    ) -> None:
        assert settings.oidc_issuer is not None
        assert settings.oidc_jwks_url is not None
        assert settings.oidc_client_id is not None
        self.issuer = settings.oidc_issuer
        self.client_id = settings.oidc_client_id
        self.operator_group = settings.oidc_operator_group
        self.publisher_group = settings.oidc_publisher_group
        self.clock_skew_seconds = settings.oidc_clock_skew_seconds
        self.jwks_client = jwks_client or PyJWKClient(
            settings.oidc_jwks_url,
            cache_keys=True,
            max_cached_keys=16,
            cache_jwk_set=True,
            lifespan=float(settings.oidc_jwks_cache_seconds),
            timeout=float(settings.oidc_http_timeout_seconds),
            cooldown_duration=30,
        )

    def verify(self, token: str) -> OperatorPrincipal:
        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                issuer=self.issuer,
                leeway=self.clock_skew_seconds,
                options={
                    "verify_aud": False,
                    "require": ["exp", "iat", "iss", "sub", "token_use", "client_id", "jti"],
                },
            )
        except PyJWKClientConnectionError as error:
            raise OperatorIdentityUnavailable from error
        except (PyJWTError, AttributeError, TypeError, ValueError):
            raise ApiError(401, "operator_auth_failed", "Operator authentication failed.") from None

        if claims.get("token_use") != "access" or claims.get("client_id") != self.client_id:
            raise ApiError(401, "operator_auth_failed", "Operator authentication failed.")

        subject = claims.get("sub")
        token_id = claims.get("jti")
        username = claims.get("username")
        groups = claims.get("cognito:groups", [])
        if (
            not isinstance(subject, str)
            or not subject
            or len(subject) > 255
            or not isinstance(token_id, str)
            or not token_id
            or len(token_id) > 255
            or not isinstance(groups, list)
            or any(not isinstance(item, str) for item in groups)
        ):
            raise ApiError(401, "operator_auth_failed", "Operator authentication failed.")

        roles = set()
        if self.operator_group in groups:
            roles.add(OPERATOR_ROLE)
        if self.publisher_group in groups:
            roles.update((OPERATOR_ROLE, PUBLISHER_ROLE))
        display_identity = (
            username if isinstance(username, str) and 0 < len(username) <= 255 else subject
        )
        return OperatorPrincipal(
            subject=subject,
            display_identity=display_identity,
            roles=frozenset(roles),
            auth_method="oidc",
            token_id=token_id,
        )


class OperatorAuthenticator:
    def __init__(
        self,
        settings: Settings,
        oidc_verifier: TokenVerifier | None = None,
    ) -> None:
        self.settings = settings
        self.oidc_verifier = oidc_verifier
        if settings.operator_auth_mode == "oidc" and self.oidc_verifier is None:
            self.oidc_verifier = CognitoTokenVerifier(settings)

    def authenticate(
        self,
        bearer_token: str | None,
        static_token: str | None,
    ) -> OperatorPrincipal:
        if self.settings.operator_auth_mode == "oidc":
            if not bearer_token or self.oidc_verifier is None:
                raise ApiError(401, "operator_auth_failed", "Operator authentication failed.")
            try:
                return self.oidc_verifier.verify(bearer_token)
            except OperatorIdentityUnavailable:
                raise ApiError(
                    503,
                    "operator_auth_unavailable",
                    "Operator identity verification is unavailable.",
                ) from None

        configured = self.settings.operator_token
        if configured is None:
            raise ApiError(
                503,
                "operator_auth_unavailable",
                "Operator endpoints are not configured.",
            )
        expected = configured.get_secret_value()
        supplied = static_token or ""
        if not compare_digest(supplied, expected):
            raise ApiError(401, "operator_auth_failed", "Operator authentication failed.")
        return OperatorPrincipal(
            subject="local-static-operator",
            display_identity="local static operator",
            roles=frozenset((OPERATOR_ROLE, PUBLISHER_ROLE)),
            auth_method="static",
        )


def build_operator_authenticator(settings: Settings) -> OperatorAuthenticator:
    return OperatorAuthenticator(settings)


def require_operator(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    provided: Annotated[str | None, Depends(operator_header)],
) -> OperatorPrincipal:
    principal = request.app.state.operator_authenticator.authenticate(
        credentials.credentials if credentials is not None else None,
        provided,
    )
    if not principal.has_role(OPERATOR_ROLE):
        raise ApiError(403, "operator_forbidden", "Operator authorization failed.")
    request.state.operator_principal = principal
    logger.info(
        "operator_authenticated",
        extra={
            "fields": {
                "request_id": get_request_id(request),
                "subject": principal.subject,
                "display_identity": principal.display_identity,
                "roles": sorted(principal.roles),
                "auth_method": principal.auth_method,
                "jti": principal.token_id,
            }
        },
    )
    return principal


def require_publisher(
    principal: Annotated[OperatorPrincipal, Depends(require_operator)],
) -> OperatorPrincipal:
    if not principal.has_role(PUBLISHER_ROLE):
        raise ApiError(403, "operator_forbidden", "Publisher authorization is required.")
    return principal


Operator = Annotated[OperatorPrincipal, Depends(require_operator)]
Publisher = Annotated[OperatorPrincipal, Depends(require_publisher)]
