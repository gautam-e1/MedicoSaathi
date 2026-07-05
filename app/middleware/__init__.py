"""Cross-cutting request middleware (Backend Architecture §6, API Architecture §4.1).

Exports the three RBAC decorators that protect tenant-scoped endpoints:

    @auth_required          — JWT + session validation (auth_guard)
    @shop_context_required  — shop token + tenant context (tenant_context)
    @permission_required    — (module, action) RBAC check (rbac_guard)

Intended decorator stacking order (outermost → innermost):

    @auth_required
    @shop_context_required
    @permission_required("module", "action")
    def handler(): ...
"""

from app.middleware.auth_guard import auth_required  # noqa: F401
from app.middleware.tenant_context import shop_context_required  # noqa: F401
from app.middleware.rbac_guard import permission_required  # noqa: F401
