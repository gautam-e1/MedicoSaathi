"""Token Manager — high-level JWT orchestration (Backend Architecture §5.1, API Architecture §3).

``TokenManager`` is the single entry point for token operations in the identity
domain.  It composes the low-level ``jwt_utils`` with ``TokenConfig`` to provide
a clean API for the future ``auth_service``:

    Login flow:
        auth_service → SessionService.create_session()
                     → TokenManager.issue_tokens(user_id, session_id)
                     → {access_token, refresh_token}

    Shop-select flow:
        auth_service → SessionService.switch_shop()
                     → TokenManager.issue_shop_token(user_id, session_id, shop_id, role_id)
                     → {shop_access_token}

    Refresh flow:
        auth_service → TokenManager.validate_refresh_token(token)
                     → SessionService (validate session still active)
                     → TokenManager.issue_tokens(user_id, session_id)
                     → {access_token, new_refresh_token}

This module does NOT:
  * Verify passwords or credentials (that is auth_service's job).
  * Issue cookies or HTTP responses (that is the API layer's job).
  * Enforce RBAC (that is the middleware layer's job).
  * Access the database (that is the service/repository layer's job).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.auth.jwt_utils import (
    TokenClaimMissing,
    TokenError,
    TokenExpired,
    TokenInvalid,
    build_access_claims,
    build_refresh_claims,
    build_shop_claims,
    decode_token,
    encode_token,
)
from app.auth.token_config import TokenConfig, load_token_config


@dataclass(frozen=True)
class TokenPair:
    """Access + refresh token pair returned on login and refresh."""

    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class AccessTokenPayload:
    """Validated claims from a base access token."""

    user_id: UUID
    session_id: UUID
    token_type: str


@dataclass(frozen=True)
class ShopTokenPayload:
    """Validated claims from a shop-scoped access token."""

    user_id: UUID
    session_id: UUID
    shop_id: UUID
    role_id: UUID
    token_type: str


@dataclass(frozen=True)
class RefreshTokenPayload:
    """Validated claims from a refresh token."""

    user_id: UUID
    session_id: UUID
    token_type: str


class TokenManager:
    """High-level token lifecycle operations.

    Constructed once per application (or per-request if config varies).
    Thread-safe — holds only immutable config.
    """

    def __init__(self, config: Optional[TokenConfig] = None) -> None:
        self._config = config or load_token_config()

    @property
    def config(self) -> TokenConfig:
        return self._config

    # -- Token issuance ----------------------------------------------------

    def issue_tokens(
        self, user_id: UUID, session_id: UUID
    ) -> TokenPair:
        """Issue an access + refresh token pair (post-login).

        Per API Architecture §3.1: access token carries user_id, session_id.
        Refresh token carries the same identifiers for session lookup during
        rotation.
        """
        access_claims = build_access_claims(
            user_id, session_id, self._config
        )
        refresh_claims = build_refresh_claims(
            user_id, session_id, self._config
        )
        return TokenPair(
            access_token=encode_token(access_claims, self._config),
            refresh_token=encode_token(refresh_claims, self._config),
        )

    def issue_shop_token(
        self,
        user_id: UUID,
        session_id: UUID,
        shop_id: UUID,
        role_id: UUID,
    ) -> str:
        """Issue a shop-scoped access token (post-shop-select).

        Per API Architecture §3.2: carries user_id, session_id, shop_id,
        role_id.  This is the token every tenant endpoint requires.
        """
        claims = build_shop_claims(
            user_id, session_id, shop_id, role_id, self._config
        )
        return encode_token(claims, self._config)

    def issue_access_token(
        self, user_id: UUID, session_id: UUID
    ) -> str:
        """Issue a standalone base access token (e.g., during refresh)."""
        claims = build_access_claims(
            user_id, session_id, self._config
        )
        return encode_token(claims, self._config)

    # -- Token validation --------------------------------------------------

    def validate_access_token(
        self, token: str
    ) -> AccessTokenPayload:
        """Validate a base access token and extract claims.

        Raises:
            TokenExpired: token has expired.
            TokenInvalid: signature invalid or malformed.
            TokenClaimMissing: required claim absent.
        """
        payload = decode_token(
            token,
            self._config,
            require_claims=["sub", "session_id", "token_type"],
        )
        if payload.get("token_type") != "access":
            raise TokenInvalid(
                f"Expected token_type 'access', got '{payload.get('token_type')}'."
            )
        return AccessTokenPayload(
            user_id=UUID(payload["sub"]),
            session_id=UUID(payload["session_id"]),
            token_type=payload["token_type"],
        )

    def validate_shop_token(
        self, token: str
    ) -> ShopTokenPayload:
        """Validate a shop-scoped access token and extract claims.

        Raises:
            TokenExpired: token has expired.
            TokenInvalid: signature invalid or malformed.
            TokenClaimMissing: required claim absent.
        """
        payload = decode_token(
            token,
            self._config,
            require_claims=[
                "sub", "session_id", "shop_id", "role_id", "token_type"
            ],
        )
        if payload.get("token_type") != "shop_access":
            raise TokenInvalid(
                f"Expected token_type 'shop_access', "
                f"got '{payload.get('token_type')}'."
            )
        return ShopTokenPayload(
            user_id=UUID(payload["sub"]),
            session_id=UUID(payload["session_id"]),
            shop_id=UUID(payload["shop_id"]),
            role_id=UUID(payload["role_id"]),
            token_type=payload["token_type"],
        )

    def validate_refresh_token(
        self, token: str
    ) -> RefreshTokenPayload:
        """Validate a refresh token and extract claims.

        Per API Architecture §3.3: the caller (auth_service) must
        additionally verify the session is still active in the DB
        before issuing new tokens (revocation check).

        Raises:
            TokenExpired: token has expired.
            TokenInvalid: signature invalid or malformed.
            TokenClaimMissing: required claim absent.
        """
        payload = decode_token(
            token,
            self._config,
            require_claims=["sub", "session_id", "token_type"],
        )
        if payload.get("token_type") != "refresh":
            raise TokenInvalid(
                f"Expected token_type 'refresh', "
                f"got '{payload.get('token_type')}'."
            )
        return RefreshTokenPayload(
            user_id=UUID(payload["sub"]),
            session_id=UUID(payload["session_id"]),
            token_type=payload["token_type"],
        )
