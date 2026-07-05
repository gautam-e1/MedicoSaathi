"""RBAC permission guard decorator (Backend Architecture §6.2, API Architecture §4.1 step 3).

Checks that the current user's role (resolved from the shop-scoped token by
``@shop_context_required``) possesses the declared ``(module, action)``
permission. Rejects with ``403 PERMISSION_DENIED`` otherwise.

This decorator calls **only** ``RolePermissionService`` — no repositories,
no models, no ``db.session`` access.

Per Engineering Constitution §6: RBAC is data-driven — no role-name string
comparisons, always ``(module, action)`` lookups against ``role_permissions``.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import g

from app.api.v1.responses import error_response
from app.repositories.tenant_context import PlatformContext
from app.services.role_permission_service import RolePermissionService


def permission_required(module: str, action: str) -> Callable[..., Any]:
    """Decorator factory that enforces a specific ``(module, action)`` permission.

    **Must** be applied after ``@shop_context_required`` — it reads ``g.role_id``.

    Args:
        module: Permission module (e.g. ``"billing"``, ``"inventory"``).
        action: Permission action (e.g. ``"view"``, ``"create"``, ``"edit"``, ``"delete"``).

    Usage::

        @bp.route("/invoices", methods=["POST"])
        @auth_required
        @shop_context_required
        @permission_required("billing", "create")
        def create_invoice():
            ...
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            role_id = getattr(g, "role_id", None)
            if role_id is None:
                return error_response(
                    "SHOP_CONTEXT_REQUIRED",
                    "Shop context must be established before permission check.",
                    status=403,
                )

            context = PlatformContext(admin_id=0)
            rp_svc = RolePermissionService(context)

            has_perm = rp_svc.check_permission(role_id, module, action)

            if not has_perm:
                return error_response(
                    "PERMISSION_DENIED",
                    f"You do not have permission to perform this action.",
                    status=403,
                    details={"required_permission": {"module": module, "action": action}},
                )

            return fn(*args, **kwargs)

        return decorated

    return decorator
