"""API response envelope helpers (API Architecture §2).

Provides the standard success/error response shapes so every endpoint
returns a consistent envelope without duplicating formatting logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from flask import jsonify, Response


def success_response(
    data: Any,
    *,
    status: int = 200,
) -> tuple[Response, int]:
    """Build a success envelope per API Architecture §2.1.

    Returns a (response, status_code) tuple for Flask to serialize.
    """
    body = {
        "success": True,
        "data": data,
        "meta": {
            "request_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    return jsonify(body), status


def error_response(
    code: str,
    message: str,
    *,
    status: int = 400,
    details: Optional[Dict[str, Any]] = None,
) -> tuple[Response, int]:
    """Build an error envelope per API Architecture §2.2.

    Args:
        code: Machine-readable error code (API Architecture §11).
        message: Human-readable, safe-to-display message.
        status: HTTP status code.
        details: Optional structured context (never a stack trace).
    """
    error_body: Dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details:
        error_body["details"] = details

    body = {
        "success": False,
        "error": error_body,
        "meta": {
            "request_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    return jsonify(body), status


def validation_error_response(
    fields: List[Dict[str, str]],
) -> tuple[Response, int]:
    """Build a validation error envelope per API Architecture §2.3.

    Args:
        fields: List of field-level errors, each with ``field``, ``code``,
            and ``message`` keys.
    """
    return error_response(
        "VALIDATION_ERROR",
        "One or more fields are invalid.",
        status=422,
        details={"fields": fields},
    )
