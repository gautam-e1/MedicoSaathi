"""Authentication API endpoints (API Architecture §3).

Blueprint: ``auth_bp`` mounted at ``/auth`` on the ``api_v1`` parent,
producing paths like ``POST /api/v1/auth/login``.

Every handler delegates to ``AuthService`` — no repositories, models, or
``db.session`` access occurs in this module.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from flask import Blueprint, request

from app.auth import TokenManager
from app.repositories.tenant_context import PlatformContext
from app.services import (
    AuthService,
    ValidationError,
)
from app.services.service_exceptions import (
    Forbidden,
    InvalidStateTransition,
    NotFound,
)
from app.api.v1.responses import (
    error_response,
    success_response,
    validation_error_response,
)

auth_bp = Blueprint("api_v1_auth", __name__, url_prefix="/auth")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_bearer_token() -> Optional[str]:
    """Extract the Bearer token from the Authorization header."""
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return None


def _build_auth_service() -> AuthService:
    """Construct AuthService with PlatformContext (auth is pre-tenant)."""
    context = PlatformContext(admin_id=0)
    return AuthService(context)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate with phone/email + password (API Architecture §3.1)."""
    body = request.get_json(silent=True) or {}

    identifier = (body.get("identifier") or "").strip()
    password = body.get("password") or ""

    if not identifier or not password:
        return validation_error_response([
            *(
                [{"field": "identifier", "code": "REQUIRED", "message": "Identifier is required."}]
                if not identifier else []
            ),
            *(
                [{"field": "password", "code": "REQUIRED", "message": "Password is required."}]
                if not password else []
            ),
        ])

    svc = _build_auth_service()

    try:
        result = svc.login(
            identifier,
            password,
            device_info=body.get("device_info"),
            ip_address=request.remote_addr,
        )
    except Forbidden:
        return error_response(
            "INVALID_CREDENTIALS",
            "Invalid credentials.",
            status=401,
        )
    except ValidationError as exc:
        return validation_error_response([
            {"field": exc.field or "identifier", "code": "INVALID", "message": str(exc)},
        ])

    data = {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
        "user_id": str(result.user_id),
        "session_id": str(result.session_id),
        "memberships": result.memberships,
    }
    if result.shop_token:
        data["shop_token"] = result.shop_token

    return success_response(data, status=200)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """Exchange a refresh token for new tokens (API Architecture §3.3)."""
    body = request.get_json(silent=True) or {}

    refresh_token = (body.get("refresh_token") or "").strip()
    if not refresh_token:
        return validation_error_response([
            {"field": "refresh_token", "code": "REQUIRED", "message": "Refresh token is required."},
        ])

    svc = _build_auth_service()

    try:
        result = svc.refresh(refresh_token)
    except Forbidden:
        return error_response(
            "TOKEN_INVALID",
            "Invalid or expired refresh token.",
            status=401,
        )

    data = {
        "access_token": result.access_token,
        "refresh_token": result.refresh_token,
    }
    if result.shop_token:
        data["shop_token"] = result.shop_token

    return success_response(data, status=200)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/logout
# ---------------------------------------------------------------------------


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Revoke the current session (API Architecture §3.4)."""
    token = _get_bearer_token()
    if not token:
        return error_response(
            "TOKEN_INVALID",
            "Authorization header with Bearer token is required.",
            status=401,
        )

    tm = TokenManager()
    try:
        payload = tm.validate_access_token(token)
    except Exception:
        return error_response(
            "TOKEN_INVALID",
            "Invalid or expired access token.",
            status=401,
        )

    svc = _build_auth_service()

    try:
        svc.logout(payload.session_id)
    except (NotFound, InvalidStateTransition):
        pass

    return success_response({"message": "Logged out successfully."}, status=200)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/shops/select
# ---------------------------------------------------------------------------


@auth_bp.route("/shops/select", methods=["POST"])
def select_shop():
    """Select active shop context (API Architecture §3.2)."""
    token = _get_bearer_token()
    if not token:
        return error_response(
            "TOKEN_INVALID",
            "Authorization header with Bearer token is required.",
            status=401,
        )

    tm = TokenManager()
    try:
        payload = tm.validate_access_token(token)
    except Exception:
        return error_response(
            "TOKEN_INVALID",
            "Invalid or expired access token.",
            status=401,
        )

    body = request.get_json(silent=True) or {}
    shop_id_str = (body.get("shop_id") or "").strip()

    if not shop_id_str:
        return validation_error_response([
            {"field": "shop_id", "code": "REQUIRED", "message": "shop_id is required."},
        ])

    try:
        shop_id = UUID(shop_id_str)
    except (ValueError, AttributeError):
        return validation_error_response([
            {"field": "shop_id", "code": "INVALID", "message": "shop_id must be a valid UUID."},
        ])

    svc = _build_auth_service()

    try:
        result = svc.select_shop(payload.user_id, payload.session_id, shop_id)
    except ValidationError as exc:
        return error_response(
            "SHOP_CONTEXT_REQUIRED",
            str(exc),
            status=403,
        )
    except InvalidStateTransition:
        return error_response(
            "SESSION_REVOKED",
            "Session is no longer active.",
            status=401,
        )

    return success_response({
        "shop_token": result.shop_token,
        "shop_id": str(result.shop_id),
        "role_id": str(result.role_id),
    })


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@auth_bp.route("/me", methods=["GET"])
def me():
    """Return current user info from the access token (API Architecture §3)."""
    token = _get_bearer_token()
    if not token:
        return error_response(
            "TOKEN_INVALID",
            "Authorization header with Bearer token is required.",
            status=401,
        )

    tm = TokenManager()
    try:
        payload = tm.validate_access_token(token)
    except Exception:
        return error_response(
            "TOKEN_INVALID",
            "Invalid or expired access token.",
            status=401,
        )

    data = {
        "user_id": str(payload.user_id),
        "session_id": str(payload.session_id),
    }

    return success_response(data)
