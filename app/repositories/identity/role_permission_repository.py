"""Identity domain — role and permission data access (Backend Architecture §4).

Owns: ``tenant.roles``, ``tenant.permissions``, ``tenant.role_permissions``.

Roles and permissions are system-wide reference data with no ``shop_id``.
All methods are ``@platform_bypass`` — no tenant scoping applies.
RBAC lookups should be heavily cached at the service layer
(Backend Architecture §8).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.extensions.extensions import db
from app.models.identity import Permission, Role, RolePermission
from app.repositories.base_repository import BaseRepository, platform_bypass
from app.utils.exceptions import NotFound


class RolePermissionRepository(BaseRepository):
    """Data access for ``tenant.roles``, ``tenant.permissions``,
    ``tenant.role_permissions``.

    RBAC lookups — heavily cached at the service layer
    (Backend Architecture §4, §8).
    Read routing: primary on all methods (small reference tables).
    """

    model = None  # system-wide reference data, no tenant scoping

    # -- roles --------------------------------------------------------------

    @platform_bypass
    def get_role_by_id(self, role_id: UUID) -> Optional[Role]:
        """Index: roles_pkey (PK). Primary."""
        return db.session.get(Role, role_id)

    @platform_bypass
    def get_role_by_code(self, role_code: str) -> Optional[Role]:
        """Index: roles_role_code_key (UNIQUE). Primary."""
        return (
            db.session.query(Role)
            .filter(Role.role_code == role_code)
            .first()
        )

    @platform_bypass
    def list_roles(self) -> List[Role]:
        """Index: seq scan (small reference table). Primary."""
        return db.session.query(Role).all()

    @platform_bypass
    def create_role(self, data: Dict[str, Any]) -> Role:
        """Primary (write)."""
        role = Role(**data)
        with self._translate_integrity_errors():
            db.session.add(role)
            db.session.flush()
        return role

    @platform_bypass
    def update_role(
        self, role_id: UUID, data: Dict[str, Any]
    ) -> Role:
        """Index: roles_pkey (PK). Primary (write)."""
        role = db.session.get(Role, role_id)
        if role is None:
            raise NotFound(f"Role {role_id} not found.")
        for key, value in data.items():
            setattr(role, key, value)
        with self._translate_integrity_errors():
            db.session.flush()
        return role

    # -- permissions --------------------------------------------------------

    @platform_bypass
    def get_permission_by_id(
        self, permission_id: UUID
    ) -> Optional[Permission]:
        """Index: permissions_pkey (PK). Primary."""
        return db.session.get(Permission, permission_id)

    @platform_bypass
    def list_permissions(self) -> List[Permission]:
        """Index: seq scan (small reference table). Primary."""
        return db.session.query(Permission).all()

    @platform_bypass
    def get_permissions_by_module(
        self, module: str
    ) -> List[Permission]:
        """Index: uq_permission_module_action (leading column). Primary."""
        return (
            db.session.query(Permission)
            .filter(Permission.module == module)
            .all()
        )

    @platform_bypass
    def create_permission(
        self, data: Dict[str, Any]
    ) -> Permission:
        """Primary (write)."""
        permission = Permission(**data)
        with self._translate_integrity_errors():
            db.session.add(permission)
            db.session.flush()
        return permission

    # -- role_permissions (junction) ----------------------------------------

    @platform_bypass
    def get_permissions_for_role(
        self, role_id: UUID
    ) -> List[Permission]:
        """All permissions assigned to a role.

        Index: role_permissions PK (leading = role_id), then
        permissions_pkey via join. Primary.
        """
        return (
            db.session.query(Permission)
            .join(
                RolePermission,
                RolePermission.permission_id == Permission.permission_id,
            )
            .filter(RolePermission.role_id == role_id)
            .all()
        )

    @platform_bypass
    def get_roles_for_permission(
        self, permission_id: UUID
    ) -> List[Role]:
        """All roles that hold a given permission.

        Index: role_permissions PK second column (permission_id);
        may benefit from a standalone index on permission_id for
        large datasets. Primary.
        """
        return (
            db.session.query(Role)
            .join(
                RolePermission,
                RolePermission.role_id == Role.role_id,
            )
            .filter(RolePermission.permission_id == permission_id)
            .all()
        )

    @platform_bypass
    def assign_permission(
        self, role_id: UUID, permission_id: UUID
    ) -> RolePermission:
        """Primary (write)."""
        mapping = RolePermission(
            role_id=role_id, permission_id=permission_id
        )
        with self._translate_integrity_errors():
            db.session.add(mapping)
            db.session.flush()
        return mapping

    @platform_bypass
    def revoke_permission(
        self, role_id: UUID, permission_id: UUID
    ) -> bool:
        """Remove a permission from a role.

        Index: role_permissions PK (role_id, permission_id). Primary (write).
        Returns True if the mapping existed and was deleted.
        """
        mapping = db.session.get(
            RolePermission, (role_id, permission_id)
        )
        if mapping is None:
            return False
        db.session.delete(mapping)
        db.session.flush()
        return True
