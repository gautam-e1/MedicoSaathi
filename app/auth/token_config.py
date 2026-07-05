"""JWT token configuration (Backend Architecture §5.1, API Architecture §3).

Environment-driven settings for token lifetimes, signing algorithm, and key
material. All values are read from environment variables with sensible
development defaults — no secret is ever hardcoded for production use
(Engineering Constitution §14.2).
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenConfig:
    """Immutable token configuration resolved once at application startup.

    Attributes:
        secret_key: HMAC signing key for HS256.  In production this MUST be
            a high-entropy value from ``JWT_SECRET_KEY`` env var.
        algorithm: JWT signing algorithm.
        access_token_ttl_seconds: Access token lifetime (~15 min per §3.1).
        refresh_token_ttl_seconds: Refresh token lifetime (7 days default).
        shop_token_ttl_seconds: Shop-scoped token lifetime (same as access).
        issuer: ``iss`` claim value.
    """

    secret_key: str
    algorithm: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    shop_token_ttl_seconds: int
    issuer: str


def _resolve_secret_key() -> str:
    """Resolve the JWT signing key with environment-appropriate behaviour.

    * If ``JWT_SECRET_KEY`` is set, use it (any environment).
    * If not set and the environment is ``production``, raise immediately —
      a missing signing key in production is a fatal configuration error
      (Engineering Constitution §14.2).
    * Otherwise (development/staging/test), generate a cryptographically
      secure random 64-byte hex key.  This key is stable for the lifetime
      of the process but rotates on restart, which is acceptable for local
      development and CI.
    """
    explicit_key = os.environ.get("JWT_SECRET_KEY")
    if explicit_key:
        return explicit_key

    env = os.environ.get("FLASK_ENV", os.environ.get("APP_ENV", "development")).lower()
    if env == "production":
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is required in production. "
            "Generate a key with: python -c \"import secrets; print(secrets.token_hex(64))\""
        )

    return secrets.token_hex(64)


def load_token_config() -> TokenConfig:
    """Build a ``TokenConfig`` from environment variables.

    Environment variables:
        JWT_SECRET_KEY — signing key (REQUIRED in production; in dev a secure
            random key is generated automatically if not set)
        JWT_ALGORITHM — default HS256
        JWT_ACCESS_TOKEN_TTL — seconds, default 900 (15 min)
        JWT_REFRESH_TOKEN_TTL — seconds, default 604800 (7 days)
        JWT_SHOP_TOKEN_TTL — seconds, default 900 (15 min)
        JWT_ISSUER — default "medicosaathi"
    """
    return TokenConfig(
        secret_key=_resolve_secret_key(),
        algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
        access_token_ttl_seconds=int(
            os.environ.get("JWT_ACCESS_TOKEN_TTL", "900")
        ),
        refresh_token_ttl_seconds=int(
            os.environ.get("JWT_REFRESH_TOKEN_TTL", "604800")
        ),
        shop_token_ttl_seconds=int(
            os.environ.get("JWT_SHOP_TOKEN_TTL", "900")
        ),
        issuer=os.environ.get("JWT_ISSUER", "medicosaathi"),
    )
