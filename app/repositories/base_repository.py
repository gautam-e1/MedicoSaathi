"""Repository-layer foundation (Backend Architecture §4).

``BaseRepository`` is the single enforcement point for the architecture's most
load-bearing rule: every tenant-scoped query is filtered by ``shop_id`` *in the
application layer*, alongside (never instead of) Postgres RLS (DB Architecture
§9, Engineering Constitution §1.2 / §20.2).

This module is foundation only. It deliberately contains:
  * NO domain repository (no users/medicines/invoices/etc.) — those arrive in
    their own sprints per the Master Development Plan;
  * NO business logic (Engineering Constitution §13.3 — business rules live in
    ``services/`` only);
  * NO schema, migration, or API coupling.

It provides exactly the contract Backend Architecture §4 specifies for
``base_repository.py``:
  1. Constructed with a ``TenantContext`` (or ``PlatformContext``); refuses to
     run a tenant-scoped query without a bound tenant, except methods marked
     ``@platform_bypass``.
  2. A helper that applies ``WHERE shop_id = :shop_id`` as the first predicate of
     every tenant-scoped query.
  3. ``.on_primary()`` / ``.on_replica()`` read routing, defaulting to primary.
  4. Translation of DB-level constraint violations into the
     ``app.utils.exceptions`` domain hierarchy, so services never branch on raw
     DB error codes.
"""

from __future__ import annotations

import functools
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional, TypeVar, Union

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from app.extensions.extensions import db
from app.repositories.tenant_context import PlatformContext, TenantContext
from app.utils.exceptions import (
    Conflict,
    IntegrityViolation,
    TenantContextError,
)

# Postgres SQLSTATE codes used to classify an IntegrityError precisely when the
# driver exposes them (psycopg2 sets ``.pgcode``). Falls back to message
# inspection only when a code is unavailable.
_PG_UNIQUE_VIOLATION = "23505"
_PG_FOREIGN_KEY_VIOLATION = "23503"

# Read-routing bind keys. ``None`` means the default (primary) connection. The
# physical replica bind (``SQLALCHEMY_BINDS["replica"]``) is provisioned in a
# later sprint per Backend Architecture §10.2; until then ``on_replica()``
# resolves safely to primary, so routing intent can be expressed today without
# changing runtime behaviour.
_REPLICA_BIND_KEY = "replica"

F = TypeVar("F", bound=Callable[..., Any])

# A repository is constructed with one of these two realms, never a raw value.
RepositoryContext = Union[TenantContext, PlatformContext]


def platform_bypass(method: F) -> F:
    """Mark a repository method as exempt from the tenant-context guard.

    Used only by the platform realm (Backend Architecture §4's ``@platform_bypass``,
    §5.2). A method decorated with this may run under a ``PlatformContext``; an
    undecorated method requires a ``TenantContext`` and will raise
    ``TenantContextError`` otherwise. The marker is an attribute on the wrapper,
    so the guard can check it without inspecting source.
    """

    @functools.wraps(method)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return method(*args, **kwargs)

    wrapper.__platform_bypass__ = True  # type: ignore[attr-defined]
    return wrapper


class BaseRepository:
    """Common foundation every concrete repository inherits from.

    Subclasses set the class attribute ``model`` to the ORM model they own.
    ``BaseRepository`` itself binds no model and exposes no domain query — it is
    purely the enforcement and routing scaffolding described in Backend
    Architecture §4.
    """

    #: The ORM model a concrete subclass owns. ``None`` on the base itself.
    model: Optional[type] = None

    def __init__(self, context: RepositoryContext) -> None:
        if context is None:  # explicit: a repository is never unbound
            raise TenantContextError(
                "A repository requires a bound TenantContext or PlatformContext."
            )
        self._context: RepositoryContext = context
        # Read routing defaults to primary (Backend Architecture §4); a service
        # opts a specific read into the replica via ``on_replica()``.
        self._read_bind: Optional[str] = None

    # -- Context -----------------------------------------------------------

    @property
    def context(self) -> RepositoryContext:
        """The realm context this repository was constructed with."""
        return self._context

    @property
    def is_platform(self) -> bool:
        """True when bound to the platform realm (no tenant scoping)."""
        return isinstance(self._context, PlatformContext)

    def _require_tenant(self) -> TenantContext:
        """Return the bound ``TenantContext`` or raise.

        This is the guard behind Engineering Constitution §20.2: a tenant-scoped
        operation cannot proceed without a validated ``shop_id`` to scope it to.
        """
        if not isinstance(self._context, TenantContext):
            raise TenantContextError(
                "This operation requires a bound TenantContext; "
                "the repository is bound to the platform realm instead."
            )
        return self._context

    # -- Tenant scoping ----------------------------------------------------

    def _tenant_filter(
        self, query: Query, model: Optional[type] = None
    ) -> Query:
        """Apply ``WHERE shop_id = :shop_id`` as the first predicate.

        This is the application-layer half of the defense-in-depth pairing with
        Postgres RLS (DB Architecture §9) — never a replacement for it. Every
        tenant-scoped query in every concrete repository flows through here so
        the ``shop_id`` filter can never be silently forgotten at a call site.
        """
        tenant = self._require_tenant()
        target = model or self.model
        if target is None:
            raise TenantContextError(
                "Cannot apply a tenant filter without a model; set the "
                "repository's `model` attribute or pass one explicitly."
            )
        return query.filter(target.shop_id == tenant.shop_id)

    # -- Read routing (primary / replica) ----------------------------------

    def on_primary(self) -> "BaseRepository":
        """Route subsequent reads to the primary. Chainable; returns self.

        Primary is the default; this exists for an explicit, readable opt-back
        after a prior ``on_replica()`` on the same instance.
        """
        self._read_bind = None
        return self

    def on_replica(self) -> "BaseRepository":
        """Route subsequent reads to the read replica. Chainable; returns self.

        Per Engineering Constitution §5.8 the primary/replica choice is an
        explicit, documented per-method decision. The physical replica bind is
        provisioned in a later sprint (Backend Architecture §10.2); until then
        this resolves to primary so no read ever fails for lack of a replica.
        """
        self._read_bind = _REPLICA_BIND_KEY
        return self

    @property
    def read_bind(self) -> Optional[str]:
        """The currently selected read bind key (``None`` == primary)."""
        return self._read_bind

    def _read_session(self) -> Any:
        """Return the SQLAlchemy session for the current read routing.

        Falls back to the primary session when no replica bind is configured,
        which is the case until the replica is provisioned (Backend Architecture
        §10.2). Resolving here, in one place, keeps every concrete repository's
        read methods free of routing branches.
        """
        if self._read_bind == _REPLICA_BIND_KEY:
            configured = db.engines.get(_REPLICA_BIND_KEY) if hasattr(db, "engines") else None
            if configured is not None:
                return db.session(bind=configured)
        return db.session

    # -- Constraint-violation translation ----------------------------------

    @contextmanager
    def _translate_integrity_errors(self) -> Iterator[None]:
        """Translate a DB ``IntegrityError`` into the domain hierarchy.

        Per Backend Architecture §4 and Engineering Constitution §13.5: a unique
        violation becomes ``Conflict``; any other integrity violation becomes
        ``IntegrityViolation``. Services catch these domain types and never the
        raw DB error. The original exception is chained (``raise ... from``) so
        the underlying cause is preserved for 2 a.m. debugging.
        """
        try:
            yield
        except IntegrityError as exc:
            pgcode = getattr(getattr(exc, "orig", None), "pgcode", None)
            if pgcode == _PG_UNIQUE_VIOLATION:
                raise Conflict("A record violating a uniqueness constraint already exists.") from exc
            if pgcode == _PG_FOREIGN_KEY_VIOLATION:
                raise IntegrityViolation("A referenced record is missing or in use.") from exc
            # Unknown SQLSTATE (or a non-Postgres driver): fall back to message
            # inspection so the failure is still surfaced as a domain error,
            # never a raw DB exception leaking upward.
            message = str(getattr(exc, "orig", exc)).lower()
            if "unique" in message:
                raise Conflict("A record violating a uniqueness constraint already exists.") from exc
            raise IntegrityViolation("A database integrity constraint was violated.") from exc
