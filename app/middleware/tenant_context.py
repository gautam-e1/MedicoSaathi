"""Tenant context decorator (Backend Architecture §5.1, API Architecture §4.1 step 2).

Validates the shop-scoped token from the ``X-Shop-Token`` header, cross-checks
it against the authenticated user (set by ``@auth_required``), and populates
``flask.g`` with the tenant context for downstream service construction.

This decorator calls **only** ``TokenManager`` — no repositories, no models,
no ``db.session`` access.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import g, request

from app.auth import TokenManager, TokenExpired, TokenInvalid, TokenClaimMissing
from app.api.v1.responses import error_response
from app.repositories.tenant_context import TenantContext


def shop_context_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that enforces a valid shop-scoped token and establishes tenant context.

    **Must** be applied after ``@auth_required`` — it reads ``g.current_user_id``
    to cross-check token ownership.

    On success, sets on ``flask.g``:
        - ``g.shop_id`` (UUID) — the active shop
        - ``g.role_id`` (UUID) — the user's role in that shop
        - ``g.tenant_context`` (TenantContext) — ready for service/repository construction

    Usage::

        @bp.route("/items", methods=["GET"])
        @auth_required
        @shop_context_required
        def list_items():
            # g.shop_id, g.role_id, g.tenant_context available
            ...
    """

    @wraps(fn)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        shop_token = request.headers.get("X-Shop-Token", "").strip()

        if not shop_token:
            return error_response(
                "SHOP_CONTEXT_REQUIRED",
                "Shop context is required. Provide a valid X-Shop-Token header.",
                status=403,
            )

        tm = TokenManager()
        try:
            payload = tm.validate_shop_token(shop_token)
        except TokenExpired:
            return error_response(
                "TOKEN_EXPIRED",
                "Shop token has expired.",
                status=401,
            )
        except (TokenInvalid, TokenClaimMissing):
            return error_response(
                "TOKEN_INVALID",
                "Invalid shop token.",
                status=401,
            )

        if payload.user_id != g.current_user_id:
            return error_response(
                "TOKEN_INVALID",
                "Shop token does not match the authenticated user.",
                status=401,
            )

        g.shop_id = payload.shop_id
        g.role_id = payload.role_id
        g.tenant_context = TenantContext(
            shop_id=payload.shop_id,
            user_id=payload.user_id,
        )

        return fn(*args, **kwargs)

    return decorated
