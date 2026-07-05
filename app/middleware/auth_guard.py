"""Authentication guard decorator (Backend Architecture §5, API Architecture §4.1).

Validates the ``Authorization: Bearer <token>`` header, confirms the
underlying session is still active, and populates ``flask.g`` with the
authenticated user/session context for downstream decorators and handlers.

This decorator calls **only** ``TokenManager`` and ``SessionService`` —
no repositories, no models, no ``db.session`` access.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import g, request

from app.auth import TokenManager, TokenExpired, TokenInvalid, TokenClaimMissing
from app.api.v1.responses import error_response
from app.repositories.tenant_context import PlatformContext
from app.services.session_service import SessionService
from app.services.service_exceptions import InvalidStateTransition, NotFound


def auth_required(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that enforces a valid access token and active session.

    On success, sets on ``flask.g``:
        - ``g.current_user_id`` (UUID)
        - ``g.current_session_id`` (UUID)
        - ``g.current_session`` (session ORM object)

    Must be the **outermost** auth decorator on any route (applied first,
    i.e. listed closest to the ``@route`` line above the handler).
    """

    @wraps(fn)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return error_response(
                "TOKEN_INVALID",
                "Authorization header with Bearer token is required.",
                status=401,
            )

        token = header[7:]

        tm = TokenManager()
        try:
            payload = tm.validate_access_token(token)
        except TokenExpired:
            return error_response(
                "TOKEN_EXPIRED",
                "Access token has expired.",
                status=401,
            )
        except (TokenInvalid, TokenClaimMissing):
            return error_response(
                "TOKEN_INVALID",
                "Invalid access token.",
                status=401,
            )

        context = PlatformContext(admin_id=0)
        session_svc = SessionService(context)

        try:
            session = session_svc.validate_session(payload.session_id)
        except (InvalidStateTransition, NotFound):
            return error_response(
                "SESSION_REVOKED",
                "Session is no longer active.",
                status=401,
            )

        g.current_user_id = payload.user_id
        g.current_session_id = payload.session_id
        g.current_session = session

        return fn(*args, **kwargs)

    return decorated
