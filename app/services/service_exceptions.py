"""Service-layer exception hierarchy (Backend Architecture §3, Engineering Constitution §4).

Business-rule exceptions raised by the service layer. These extend the shared
``DomainError`` base from ``app.utils.exceptions`` with failures that are
specific to business-rule enforcement — plan limits, credit limits, invalid
state transitions, and service-level validation.

Per Engineering Constitution §4, every exception is PascalCase and names the
failure, not the layer (``PlanLimitExceeded``, not ``BillingServiceError``).

Repository-level exceptions (``NotFound``, ``Conflict``, ``TenantMismatch``,
etc.) remain in ``app.utils.exceptions`` and are re-exported here so that
service modules can import their full exception vocabulary from a single place.
"""

from __future__ import annotations

from typing import Optional

from app.utils.exceptions import (  # noqa: F401 – re-exported for service convenience
    Conflict,
    DomainError,
    Forbidden,
    IntegrityViolation,
    NotFound,
    TenantContextError,
    TenantMismatch,
)


class ServiceError(DomainError):
    """Base for every service-layer business-rule exception.

    Sits between ``DomainError`` and the concrete failures below so that API
    error handlers can distinguish "a business rule was violated" from "a
    repository-level constraint was hit" when choosing HTTP status codes.
    """


class PlanLimitExceeded(ServiceError):
    """A metered action would exceed the shop's subscription plan quota.

    Per Backend Architecture §3 and Engineering Constitution §8.3, every
    metered write must check plan limits *before* committing. This exception
    is the hard gate that prevents silent over-quota transactions.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        resource: Optional[str] = None,
        limit: Optional[int] = None,
        current: Optional[int] = None,
    ) -> None:
        super().__init__(message or "Plan limit exceeded.")
        self.resource = resource
        self.limit = limit
        self.current = current


class CreditLimitExceeded(ServiceError):
    """A transaction would exceed a supplier's credit limit.

    Raised by the supplier/procurement service layer when a purchase order or
    payment would push outstanding credit beyond the negotiated ceiling.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        supplier_id: Optional[int] = None,
        limit: Optional[float] = None,
        outstanding: Optional[float] = None,
    ) -> None:
        super().__init__(message or "Credit limit exceeded.")
        self.supplier_id = supplier_id
        self.limit = limit
        self.outstanding = outstanding


class InvalidStateTransition(ServiceError):
    """A lifecycle entity was asked to move to a state that is not reachable
    from its current state.

    Used by services that manage state machines — delivery lifecycle, invoice
    hold/recall/void, procurement GRN workflow, etc.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        entity: Optional[str] = None,
        current_state: Optional[str] = None,
        requested_state: Optional[str] = None,
    ) -> None:
        super().__init__(message or "Invalid state transition.")
        self.entity = entity
        self.current_state = current_state
        self.requested_state = requested_state


class ValidationError(ServiceError):
    """A service-level business-rule validation failed.

    Distinct from schema/request validation (which happens at the API layer):
    this covers rules that require domain context — e.g. a batch expiry date
    in the past, a GRN quantity exceeding the PO quantity, etc.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        field: Optional[str] = None,
        details: Optional[dict] = None,
    ) -> None:
        super().__init__(message or "Validation failed.")
        self.field = field
        self.details = details or {}
