from datetime import datetime, timezone

from uuid_utils import uuid7

from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

from app.extensions.extensions import db


# =============================================================================
# Domain B — Identity & Access (tenant schema)
# DB Architecture §1, Domain B
# =============================================================================


class TenantUser(db.Model):
    """A real person who may belong to more than one shop."""

    __tablename__ = "users"
    __table_args__ = {"schema": "tenant"}

    user_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    email = db.Column(db.Text, unique=True, nullable=True)
    phone = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=True)
    full_name = db.Column(db.Text, nullable=True)
    mfa_enabled = db.Column(
        db.Boolean, default=False, nullable=False
    )
    status = db.Column(db.Text, default="Active", nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_login_at = db.Column(
        db.DateTime(timezone=True), nullable=True
    )

    shop_memberships = db.relationship(
        "ShopUser",
        back_populates="user",
        foreign_keys="ShopUser.user_id",
        lazy="select",
    )
    sessions = db.relationship(
        "AuthSession", back_populates="user", lazy="select"
    )


class Role(db.Model):

    __tablename__ = "roles"
    __table_args__ = {"schema": "tenant"}

    role_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    role_code = db.Column(db.Text, unique=True, nullable=False)
    display_name = db.Column(db.Text, nullable=True)
    is_system_role = db.Column(
        db.Boolean, default=False, nullable=False
    )

    role_permissions = db.relationship(
        "RolePermission", back_populates="role", lazy="select"
    )
    shop_users = db.relationship(
        "ShopUser", back_populates="role", lazy="select"
    )


class Permission(db.Model):

    __tablename__ = "permissions"
    __table_args__ = (
        db.UniqueConstraint(
            "module", "action", name="uq_permission_module_action"
        ),
        {"schema": "tenant"},
    )

    permission_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    module = db.Column(db.Text, nullable=False)
    action = db.Column(db.Text, nullable=False)

    role_permissions = db.relationship(
        "RolePermission", back_populates="permission", lazy="select"
    )


class RolePermission(db.Model):
    """Junction: role_id + permission_id composite PK."""

    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "tenant"}

    role_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("tenant.roles.role_id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("tenant.permissions.permission_id", ondelete="CASCADE"),
        primary_key=True,
    )

    role = db.relationship("Role", back_populates="role_permissions")
    permission = db.relationship(
        "Permission", back_populates="role_permissions"
    )


class ShopUser(db.Model):
    """Membership junction — grants a user access to a specific shop."""

    __tablename__ = "shop_users"
    __table_args__ = (
        db.UniqueConstraint(
            "shop_id", "user_id", name="uq_shop_user"
        ),
        {"schema": "tenant"},
    )

    shop_user_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    # FK to platform.shops deferred until platform models exist
    shop_id = db.Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("tenant.users.user_id"),
        nullable=False,
        index=True,
    )
    role_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("tenant.roles.role_id"),
        nullable=False,
        index=True,
    )
    status = db.Column(db.Text, default="Active", nullable=False)
    invited_by = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("tenant.users.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    joined_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship(
        "TenantUser",
        foreign_keys=[user_id],
        back_populates="shop_memberships",
    )
    role = db.relationship("Role", back_populates="shop_users")
    inviter = db.relationship(
        "TenantUser", foreign_keys=[invited_by]
    )


class AuthSession(db.Model):

    __tablename__ = "auth_sessions"
    __table_args__ = {"schema": "tenant"}

    session_id = db.Column(
        UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("tenant.users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # FK to platform.shops deferred until platform models exist
    shop_id = db.Column(UUID(as_uuid=True), nullable=True, index=True)
    device_info = db.Column(JSONB, nullable=True)
    ip_address = db.Column(INET, nullable=True)
    issued_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(
        db.DateTime(timezone=True), nullable=False
    )
    revoked_at = db.Column(
        db.DateTime(timezone=True), nullable=True
    )

    user = db.relationship(
        "TenantUser", back_populates="sessions"
    )
