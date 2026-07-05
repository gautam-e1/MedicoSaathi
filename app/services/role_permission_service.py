"""Identity domain — role and permission orchestration (Backend Architecture §3).

Calls: ``RolePermissionRepository`` only.

Business rules owned by this service:

* Role creation / update with ``role_code`` uniqueness.
* Permission creation with ``(module, action)`` uniqueness.
* Role-permission assignment / revocation.
* Permission resolution — full ``(module, action)`` set for a role.
* Guard: system roles cannot be mutated.

This service does **not** own:

* RBAC enforcement (middleware layer, Backend Architecture §6).
* Cache management for permission lookups (Backend Architecture §8 —
  to be added when caching infrastructure is in place).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from app.repositories.identity.role_permission_repository import (
    RolePermissionRepository,
)
from app.services.base_service import BaseService, RepositoryContext
from app.services.service_exceptions import (
    Forbidden,
    NotFound,
    ValidationError,
)


class RolePermissionService(BaseService):
    """Role and permission business orchestration."""

    def __init__(self, context: RepositoryContext) -> None:
        super().__init__(context)
        self._rp_repo = RolePermissionRepository(context)

    # -- role lookup --------------------------------------------------------

    def get_role(self, role_id: UUID) -> Optional[Any]:
        """Look up a role by ID."""
        return self._rp_repo.get_role_by_id(role_id)

    def get_role_or_raise(self, role_id: UUID) -> Any:
        """Look up a role by ID; raise ``NotFound`` if absent."""
        role = self._rp_repo.get_role_by_id(role_id)
        if role is None:
            raise NotFound(f"Role {role_id} not found.")
        return role

    def get_role_by_code(self, role_code: str) -> Optional[Any]:
        """Look up a role by its unique code."""
        return self._rp_repo.get_role_by_code(role_code)

    def list_roles(self) -> List[Any]:
        """Return all roles."""
        return self._rp_repo.list_roles()

    # -- role creation / update ---------------------------------------------

    def create_role(self, data: Dict[str, Any]) -> Any:
        """Create a new role.

        Validates that ``role_code`` and ``display_name`` are provided.
        """
        if not data.get("role_code"):
            raise ValidationError(
                "Role code is required.", field="role_code"
            )
        if not data.get("display_name"):
            raise ValidationError(
                "Display name is required.", field="display_name"
            )
        with self.transaction():
            role = self._rp_repo.create_role(data)
        return role

    def update_role(
        self, role_id: UUID, data: Dict[str, Any]
    ) -> Any:
        """Update a role.

        System roles (``is_system_role = True``) cannot be mutated.
        """
        role = self.get_role_or_raise(role_id)
        if getattr(role, "is_system_role", False):
            raise Forbidden("System roles cannot be modified.")
        with self.transaction():
            role = self._rp_repo.update_role(role_id, data)
        return role

    # -- permission lookup --------------------------------------------------

    def get_permission(self, permission_id: UUID) -> Optional[Any]:
        """Look up a permission by ID."""
        return self._rp_repo.get_permission_by_id(permission_id)

    def get_permission_or_raise(self, permission_id: UUID) -> Any:
        """Look up a permission by ID; raise ``NotFound`` if absent."""
        perm = self._rp_repo.get_permission_by_id(permission_id)
        if perm is None:
            raise NotFound(f"Permission {permission_id} not found.")
        return perm

    def list_permissions(self) -> List[Any]:
        """Return all permissions."""
        return self._rp_repo.list_permissions()

    def list_permissions_by_module(self, module: str) -> List[Any]:
        """Return all permissions for a given module."""
        return self._rp_repo.get_permissions_by_module(module)

    # -- permission creation ------------------------------------------------

    def create_permission(self, data: Dict[str, Any]) -> Any:
        """Create a new permission.

        Validates that ``module`` and ``action`` are provided.
        """
        if not data.get("module"):
            raise ValidationError(
                "Module is required.", field="module"
            )
        if not data.get("action"):
            raise ValidationError(
                "Action is required.", field="action"
            )
        with self.transaction():
            perm = self._rp_repo.create_permission(data)
        return perm

    # -- role-permission assignment -----------------------------------------

    def get_permissions_for_role(self, role_id: UUID) -> List[Any]:
        """Return all permissions assigned to a role."""
        self.get_role_or_raise(role_id)
        return self._rp_repo.get_permissions_for_role(role_id)

    def resolve_permissions(
        self, role_id: UUID
    ) -> List[Dict[str, str]]:
        """Resolve the full ``(module, action)`` set for a role.

        Returns a list of dicts, each with ``module`` and ``action`` keys.
        Useful for the future RBAC middleware to build the permission set
        from the user's active role (Backend Architecture §6).
        """
        permissions = self.get_permissions_for_role(role_id)
        return [
            {"module": p.module, "action": p.action}
            for p in permissions
        ]

    def check_permission(
        self, role_id: UUID, module: str, action: str
    ) -> bool:
        """Check whether a role has a specific ``(module, action)`` pair.

        Pure lookup — does NOT enforce; enforcement is the middleware's
        responsibility (Backend Architecture §6).
        """
        permissions = self.resolve_permissions(role_id)
        return any(
            p["module"] == module and p["action"] == action
            for p in permissions
        )

    def assign_permission(
        self, role_id: UUID, permission_id: UUID
    ) -> Any:
        """Assign a permission to a role.

        System roles cannot have their permissions changed.
        """
        role = self.get_role_or_raise(role_id)
        if getattr(role, "is_system_role", False):
            raise Forbidden(
                "Cannot modify permissions of a system role."
            )
        self.get_permission_or_raise(permission_id)
        with self.transaction():
            mapping = self._rp_repo.assign_permission(
                role_id, permission_id
            )
        return mapping

    def revoke_permission(
        self, role_id: UUID, permission_id: UUID
    ) -> bool:
        """Remove a permission from a role.

        System roles cannot have their permissions changed.
        Returns True if the mapping existed and was removed.
        """
        role = self.get_role_or_raise(role_id)
        if getattr(role, "is_system_role", False):
            raise Forbidden(
                "Cannot modify permissions of a system role."
            )
        with self.transaction():
            removed = self._rp_repo.revoke_permission(
                role_id, permission_id
            )
        return removed
