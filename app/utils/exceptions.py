"""Domain exception hierarchy (Backend Architecture §1, §4).

This is the single, shared set of exceptions every layer raises and the layer
above catches. Per Engineering Constitution §13.5, every failure path maps to a
member of this hierarchy rather than leaking a raw database/ORM error or a bare
``Exception``. The repository layer (Backend Architecture §4) is responsible for
translating DB-level constraint violations into these types so that services
never branch on raw DB error codes.

This module is foundation only: it defines the exception *types*. It contains no
business logic and is intentionally not wired to any API error-code mapping yet
(that mapping lives at the API layer and is added in a later sprint, per the
Master Development Plan).
"""

from __future__ import annotations

from typing import Optional


class DomainError(Exception):
    """Base class for every MedicoSaathi domain exception.

    Carries an optional human-readable ``message``. It deliberately does not
    carry an API ``error.code`` — that mapping is an API-layer concern
    (API Architecture §11) and is not decided here, to keep the repository
    foundation free of API coupling.
    """

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or self.__class__.__name__)
        self.message: str = message or self.__class__.__name__


class TenantContextError(DomainError):
    """Raised when a repository operation is attempted without a bound tenant
    context, or with a context that is not valid for the operation.

    This is the load-bearing guard behind Engineering Constitution §1.2 /
    §20.2: a tenant-scoped query must never run without an explicit ``shop_id``
    to scope it to.
    """


class TenantMismatch(DomainError):
    """Raised when an entity's ``shop_id`` does not match the bound tenant
    context — i.e. an attempt to read or write across a tenant boundary
    (Backend Architecture §4, Engineering Constitution §1.2)."""


class NotFound(DomainError):
    """Raised when a requested entity does not exist within the bound tenant
    context."""


class Conflict(DomainError):
    """Raised when a write violates a uniqueness/integrity constraint — the
    domain-level translation of a DB unique-violation (Backend Architecture §4)."""


class IntegrityViolation(DomainError):
    """Raised when a write violates a foreign-key or other integrity constraint —
    the domain-level translation of a DB integrity error (Backend Architecture §4)."""


class Forbidden(DomainError):
    """Raised when an operation is not permitted for the current actor.

    Defined here for completeness of the hierarchy; RBAC enforcement itself
    lives in middleware (Backend Architecture §6), not in the repository layer.
    """
