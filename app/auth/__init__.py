"""Authentication infrastructure — JWT token management (Backend Architecture §5).

This package provides:

* ``TokenConfig`` / ``load_token_config()`` — environment-driven JWT settings.
* ``TokenManager`` — high-level token issuance and validation.
* ``TokenPair``, ``AccessTokenPayload``, ``ShopTokenPayload``,
  ``RefreshTokenPayload`` — typed result objects.
* ``TokenError``, ``TokenExpired``, ``TokenInvalid``, ``TokenClaimMissing``
  — exception hierarchy for token validation failures.

This package does NOT contain:

* Login/logout routes (API layer, future sprint).
* Middleware (``auth_guard``, ``tenant_context`` — future sprint).
* Password hashing (future ``auth_service``).
* RBAC enforcement (``rbac_guard`` middleware — future sprint).
"""

from app.auth.token_config import TokenConfig, load_token_config  # noqa: F401
from app.auth.token_manager import (  # noqa: F401
    AccessTokenPayload,
    RefreshTokenPayload,
    ShopTokenPayload,
    TokenManager,
    TokenPair,
)
from app.auth.jwt_utils import (  # noqa: F401
    TokenClaimMissing,
    TokenError,
    TokenExpired,
    TokenInvalid,
)
