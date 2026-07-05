"""Low-level JWT encode/decode utilities (Backend Architecture §5.1).

Pure functions — no service, repository, or Flask dependency.  The
``TokenManager`` (one layer up) composes these with business logic; this
module is deliberately kept dependency-free for testability and reuse
across both tenant and platform auth realms.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import jwt

from app.auth.token_config import TokenConfig


class TokenError(Exception):
    """Base for token-related failures."""


class TokenExpired(TokenError):
    """The token's ``exp`` claim is in the past."""


class TokenInvalid(TokenError):
    """The token failed signature verification or is malformed."""


class TokenClaimMissing(TokenError):
    """A required claim is absent from the token payload."""


def encode_token(
    payload: Dict[str, Any],
    config: TokenConfig,
) -> str:
    """Encode a JWT with the configured algorithm and key.

    The caller is responsible for building the payload (claims + exp/iat/iss).
    This function only handles the cryptographic signing step.
    """
    return jwt.encode(
        payload,
        config.secret_key,
        algorithm=config.algorithm,
    )


def decode_token(
    token: str,
    config: TokenConfig,
    *,
    require_claims: Optional[list[str]] = None,
) -> Dict[str, Any]:
    """Decode and validate a JWT.

    Raises:
        TokenExpired: if the ``exp`` claim is in the past.
        TokenInvalid: if signature verification fails or the token is
            malformed.
        TokenClaimMissing: if any claim in ``require_claims`` is absent.
    """
    try:
        payload = jwt.decode(
            token,
            config.secret_key,
            algorithms=[config.algorithm],
            issuer=config.issuer,
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpired("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalid(f"Token is invalid: {exc}") from exc

    if require_claims:
        for claim in require_claims:
            if claim not in payload:
                raise TokenClaimMissing(
                    f"Required claim '{claim}' is missing."
                )

    return payload


def build_access_claims(
    user_id: UUID,
    session_id: UUID,
    config: TokenConfig,
) -> Dict[str, Any]:
    """Build claims for a base access token (post-login, no shop context).

    Per API Architecture §3.1: claims = user_id, session_id only.
    """
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user_id),
        "session_id": str(session_id),
        "token_type": "access",
        "iss": config.issuer,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + config.access_token_ttl_seconds,
    }


def build_shop_claims(
    user_id: UUID,
    session_id: UUID,
    shop_id: UUID,
    role_id: UUID,
    config: TokenConfig,
) -> Dict[str, Any]:
    """Build claims for a shop-scoped access token (post-shop-select).

    Per API Architecture §3.2: claims = user_id, session_id, shop_id, role_id.
    """
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user_id),
        "session_id": str(session_id),
        "shop_id": str(shop_id),
        "role_id": str(role_id),
        "token_type": "shop_access",
        "iss": config.issuer,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + config.shop_token_ttl_seconds,
    }


def build_refresh_claims(
    user_id: UUID,
    session_id: UUID,
    config: TokenConfig,
) -> Dict[str, Any]:
    """Build claims for a refresh token.

    Per API Architecture §3.3: the refresh token is tied to the
    ``auth_sessions`` row. It carries only enough to identify the session
    for rotation and re-issuance.
    """
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user_id),
        "session_id": str(session_id),
        "token_type": "refresh",
        "iss": config.issuer,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + config.refresh_token_ttl_seconds,
    }
