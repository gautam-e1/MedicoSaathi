"""Tenant / platform execution context (Backend Architecture §4, §5, §6).

A repository is constructed with one of these context objects and refuses to run
any tenant-scoped query without one. This is the in-process carrier of the
validated ``shop_id`` that the auth/middleware layer (Backend Architecture §5.3,
§6) produces per request — the repository layer is the single enforcement point
that turns that value into a ``WHERE shop_id = ...`` predicate.

These are immutable value objects only. They hold no behaviour, no business
logic, and perform no I/O. They do not themselves connect to or configure the
database; the connection-pool / ``SET LOCAL`` wiring described in Backend
Architecture §5.3 / §10.2 is a later sprint's concern and is intentionally not
implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TenantContext:
    """The bound tenant for a unit of work.

    Attributes:
        shop_id: The validated tenant discriminator. Every tenant-scoped query
            issued through a repository constructed with this context is filtered
            by this value as its first predicate (Backend Architecture §4).
        user_id: The acting user within the shop, when known. Optional because a
            context may be established before a user is resolved; it is metadata
            for logging/audit correlation, never itself a query filter.
    """

    shop_id: int
    user_id: int | None = None


@dataclass(frozen=True)
class PlatformContext:
    """The bound context for the platform-admin realm (Backend Architecture §5.2).

    A repository constructed with this context is *not* tenant-scoped: it backs
    the explicitly cross-tenant platform-admin path (Backend Architecture §4's
    ``@platform_bypass`` methods, DB Architecture §9's ``BYPASSRLS`` role). It is
    a distinct type — never a ``TenantContext`` with a flag — so that the two
    realms cannot be confused at a call site (Engineering Constitution §20.5).
    """

    admin_id: int
