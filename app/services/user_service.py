"""Identity domain — user and shop-membership orchestration (Backend Architecture §3).

Calls: ``UserRepository`` only (Backend Architecture §3 — a service is the only
caller of its corresponding repositories).

Business rules owned by this service:

* User creation / update orchestration.
* Multi-shop membership orchestration (add / update / revoke members).
* Staff-count query (consumed by ``subscription_service`` for plan-limit
  checks — Backend Architecture §3 service-layer rule on plan limits).

This service does **not** own:

* Password hashing or credential verification (future ``auth_service``).
* Plan-limit enforcement (future ``subscription_service``).
* RBAC permission checks (middleware layer, Backend Architecture §6).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.repositories.identity.user_repository import UserRepository
from app.services.base_service import BaseService, RepositoryContext
from app.services.service_exceptions import NotFound, ValidationError


class UserService(BaseService):
    """User and shop-membership business orchestration."""

    def __init__(self, context: RepositoryContext) -> None:
        super().__init__(context)
        self._user_repo = UserRepository(context)

    # -- user lookup --------------------------------------------------------

    def get_user(self, user_id: UUID) -> Optional[Any]:
        """Look up a user by ID."""
        return self._user_repo.get_by_id(user_id)

    def get_user_or_raise(self, user_id: UUID) -> Any:
        """Look up a user by ID; raise ``NotFound`` if absent."""
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFound(f"User {user_id} not found.")
        return user

    def get_user_by_phone(self, phone: str) -> Optional[Any]:
        """Look up a user by phone number."""
        return self._user_repo.get_by_phone(phone)

    def get_user_by_email(self, email: str) -> Optional[Any]:
        """Look up a user by email address."""
        return self._user_repo.get_by_email(email)

    # -- user creation / update ---------------------------------------------

    def create_user(self, data: Dict[str, Any]) -> Any:
        """Create a new user.

        Validates that a phone number is provided (the architecture's
        only NOT NULL non-defaulted field on ``users``).
        """
        if not data.get("phone"):
            raise ValidationError(
                "Phone number is required.", field="phone"
            )
        with self.transaction():
            user = self._user_repo.create_user(data)
        return user

    def update_user(
        self, user_id: UUID, data: Dict[str, Any]
    ) -> Any:
        """Update fields on an existing user."""
        with self.transaction():
            user = self._user_repo.update_user(user_id, data)
        return user

    # -- multi-shop membership ----------------------------------------------

    def get_user_shops(self, user_id: UUID) -> List[Any]:
        """Return all shop memberships for a user (multi-shop resolution).

        Used by the auth layer to determine whether auto-select or
        shop-picker is needed after login (Backend Architecture §5.1).
        """
        return self._user_repo.get_memberships_for_user(user_id)

    def list_shop_members(self) -> List[Any]:
        """Return all members of the bound shop (tenant-scoped)."""
        return self._user_repo.list_shop_users()

    def count_shop_members(self) -> int:
        """Count members in the bound shop.

        Consumed by ``subscription_service`` for staff-account plan-limit
        checks (Backend Architecture §3 service-layer rule).
        """
        return self._user_repo.count_shop_users()

    def get_shop_membership(self, user_id: UUID) -> Optional[Any]:
        """Return a specific user's membership in the bound shop."""
        return self._user_repo.get_shop_user(user_id)

    def add_shop_member(
        self,
        user_id: UUID,
        role_id: UUID,
        *,
        invited_by: Optional[UUID] = None,
    ) -> Any:
        """Add a user to the bound shop with a given role.

        The caller (future ``settings_service`` or ``auth_service``) is
        responsible for checking staff-account plan limits via
        ``subscription_service`` before calling this method.
        """
        existing = self._user_repo.get_shop_user(user_id)
        if existing is not None:
            raise ValidationError(
                "User is already a member of this shop.",
                field="user_id",
            )

        data: Dict[str, Any] = {
            "user_id": user_id,
            "role_id": role_id,
            "status": "Active",
        }
        if invited_by is not None:
            data["invited_by"] = invited_by

        with self.transaction():
            membership = self._user_repo.create_shop_user(data)
        return membership

    def update_shop_membership(
        self, shop_user_id: UUID, data: Dict[str, Any]
    ) -> Any:
        """Update a membership (role change, status change, etc.)."""
        with self.transaction():
            membership = self._user_repo.update_shop_user(
                shop_user_id, data
            )
        return membership

    def revoke_shop_membership(self, shop_user_id: UUID) -> Any:
        """Revoke a user's membership in the bound shop."""
        with self.transaction():
            membership = self._user_repo.update_shop_user(
                shop_user_id, {"status": "Revoked"}
            )
        return membership
