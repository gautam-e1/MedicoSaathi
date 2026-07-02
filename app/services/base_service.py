"""Service-layer foundation (Backend Architecture §3, Engineering Constitution §8).

``BaseService`` is the common infrastructure every domain service inherits from.
It mirrors the repository layer's ``BaseRepository`` in purpose — shared
plumbing, zero business logic — but at the service tier:

  * Binds a ``TenantContext`` or ``PlatformContext`` so that every repository
    the service constructs inherits correct tenant scoping automatically.
  * Owns the transaction boundary: when a service method touches more than one
    repository, ``BaseService.transaction()`` wraps the work in a single
    commit/rollback unit (Engineering Constitution §8.1).

This module is foundation only. It deliberately contains:
  * NO domain service (no inventory/billing/customer/etc.) — those arrive in
    their own sprints per the Master Development Plan;
  * NO business logic (Engineering Constitution §13.3 — business rules live in
    concrete service subclasses only);
  * NO route, schema, model, or migration coupling.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Optional, Union

from app.extensions.extensions import db
from app.repositories.tenant_context import PlatformContext, TenantContext
from app.services.service_exceptions import TenantContextError

RepositoryContext = Union[TenantContext, PlatformContext]


class BaseService:
    """Common foundation every concrete service inherits from.

    A service is always constructed with a validated execution context.
    Subclasses build their own repositories in ``__init__`` by forwarding
    ``self.context`` — this keeps tenant scoping consistent and explicit
    across the entire request path.

    Example (future sprint)::

        class InventoryService(BaseService):
            def __init__(self, context: RepositoryContext) -> None:
                super().__init__(context)
                self._batch_repo = BatchRepository(context)

            def create_batch(self, data: dict) -> dict:
                with self.transaction():
                    batch = self._batch_repo.create(data)
                    self._batch_repo.create_ledger_entry(batch.id, ...)
                return batch_schema.dump(batch)
    """

    def __init__(self, context: RepositoryContext) -> None:
        if context is None:
            raise TenantContextError(
                "A service requires a bound TenantContext or PlatformContext."
            )
        self._context: RepositoryContext = context

    # -- Context access ----------------------------------------------------

    @property
    def context(self) -> RepositoryContext:
        """The execution context this service was constructed with."""
        return self._context

    @property
    def is_platform(self) -> bool:
        """True when operating in the platform-admin realm."""
        return isinstance(self._context, PlatformContext)

    def _require_tenant(self) -> TenantContext:
        """Return the bound ``TenantContext`` or raise.

        Convenience for service methods that must only run under a tenant
        scope — mirrors ``BaseRepository._require_tenant()``.
        """
        if not isinstance(self._context, TenantContext):
            raise TenantContextError(
                "This operation requires a bound TenantContext; "
                "the service is bound to the platform realm instead."
            )
        return self._context

    # -- Transaction boundary ----------------------------------------------

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Wrap a unit of work in a single commit/rollback boundary.

        Per Engineering Constitution §8.1, a service method that touches more
        than one repository owns the transaction. Partial-failure states are
        treated as bugs — if any step raises, the entire unit is rolled back.

        Usage::

            with self.transaction():
                self._repo_a.create(...)
                self._repo_b.update(...)
            # commit happens here on success; rollback on any exception.
        """
        try:
            yield db.session
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
