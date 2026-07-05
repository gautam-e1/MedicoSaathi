"""Identity domain — user and shop-membership data access (Backend Architecture §4).

Owns: ``tenant.users``, ``tenant.shop_users``.

``users`` has no ``shop_id`` — a user is a cross-tenant entity that can belong
to many shops via the ``shop_users`` junction.  Methods querying ``users``
directly are ``@platform_bypass``; methods querying ``shop_users`` enforce the
tenant context as the first predicate (DB Architecture §9).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.extensions.extensions import db
from app.models.identity import ShopUser, TenantUser
from app.repositories.base_repository import BaseRepository, platform_bypass
from app.utils.exceptions import NotFound


class UserRepository(BaseRepository):
    """Data access for ``tenant.users`` and ``tenant.shop_users``.

    Multi-shop membership resolution (Backend Architecture §4).
    Read routing: primary on all methods (auth/identity is write-critical).
    """

    model = None  # spans two tables with different scoping rules

    # -- users (cross-tenant, @platform_bypass) -----------------------------

    @platform_bypass
    def get_by_id(self, user_id: UUID) -> Optional[TenantUser]:
        """Index: users_pkey (PK). Primary."""
        return db.session.get(TenantUser, user_id)

    @platform_bypass
    def get_by_phone(self, phone: str) -> Optional[TenantUser]:
        """Index: users_phone_key (UNIQUE). Primary."""
        return (
            db.session.query(TenantUser)
            .filter(TenantUser.phone == phone)
            .first()
        )

    @platform_bypass
    def get_by_email(self, email: str) -> Optional[TenantUser]:
        """Index: users_email_key (UNIQUE). Primary."""
        return (
            db.session.query(TenantUser)
            .filter(TenantUser.email == email)
            .first()
        )

    @platform_bypass
    def create_user(self, data: Dict[str, Any]) -> TenantUser:
        """Primary (write)."""
        user = TenantUser(**data)
        with self._translate_integrity_errors():
            db.session.add(user)
            db.session.flush()
        return user

    @platform_bypass
    def update_user(
        self, user_id: UUID, data: Dict[str, Any]
    ) -> TenantUser:
        """Index: users_pkey (PK). Primary (write)."""
        user = db.session.get(TenantUser, user_id)
        if user is None:
            raise NotFound(f"User {user_id} not found.")
        for key, value in data.items():
            setattr(user, key, value)
        with self._translate_integrity_errors():
            db.session.flush()
        return user

    @platform_bypass
    def get_memberships_for_user(
        self, user_id: UUID
    ) -> List[ShopUser]:
        """All shop memberships for a user (multi-shop resolution).

        Index: ix_tenant_shop_users_user_id. Primary.
        """
        return (
            db.session.query(ShopUser)
            .filter(ShopUser.user_id == user_id)
            .all()
        )

    # -- shop_users (tenant-scoped) -----------------------------------------

    def list_shop_users(self) -> List[ShopUser]:
        """All users belonging to the bound shop.

        Index: ix_tenant_shop_users_shop_id. Primary.
        """
        query = db.session.query(ShopUser)
        query = self._tenant_filter(query, model=ShopUser)
        return query.all()

    def count_shop_users(self) -> int:
        """Count of users in the bound shop (plan-limit checks).

        Index: ix_tenant_shop_users_shop_id. Primary.
        """
        query = db.session.query(db.func.count(ShopUser.shop_user_id))
        query = self._tenant_filter(query, model=ShopUser)
        return query.scalar() or 0

    def get_shop_user(self, user_id: UUID) -> Optional[ShopUser]:
        """A specific user's membership in the bound shop.

        Index: uq_shop_user (shop_id, user_id). Primary.
        """
        query = db.session.query(ShopUser).filter(
            ShopUser.user_id == user_id
        )
        query = self._tenant_filter(query, model=ShopUser)
        return query.first()

    def get_shop_user_by_id(
        self, shop_user_id: UUID
    ) -> Optional[ShopUser]:
        """Fetch a shop-user membership by its own PK, within the bound shop.

        Index: shop_users_pkey + tenant filter. Primary.
        """
        query = db.session.query(ShopUser).filter(
            ShopUser.shop_user_id == shop_user_id
        )
        query = self._tenant_filter(query, model=ShopUser)
        return query.first()

    def create_shop_user(self, data: Dict[str, Any]) -> ShopUser:
        """Create a membership in the bound shop. Primary (write)."""
        tenant = self._require_tenant()
        membership = ShopUser(shop_id=tenant.shop_id, **data)
        with self._translate_integrity_errors():
            db.session.add(membership)
            db.session.flush()
        return membership

    def update_shop_user(
        self, shop_user_id: UUID, data: Dict[str, Any]
    ) -> ShopUser:
        """Update a membership in the bound shop.

        Index: shop_users_pkey + tenant filter. Primary (write).
        """
        query = db.session.query(ShopUser).filter(
            ShopUser.shop_user_id == shop_user_id
        )
        query = self._tenant_filter(query, model=ShopUser)
        membership = query.first()
        if membership is None:
            raise NotFound(f"ShopUser {shop_user_id} not found.")
        for key, value in data.items():
            setattr(membership, key, value)
        with self._translate_integrity_errors():
            db.session.flush()
        return membership
