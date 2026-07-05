"""Identity domain — authentication orchestration (Backend Architecture §3, API Architecture §3).

``AuthService`` is the single service named in Backend Architecture §3's table
for the identity domain.  It composes the three identity sub-services
(``UserService``, ``SessionService``, ``RolePermissionService``) with the
``TokenManager`` to implement the full authentication lifecycle:

* Login (API Architecture §3.1)
* Shop-context selection (API Architecture §3.2)
* Token refresh with rotation (API Architecture §3.3)
* Logout / logout-all (API Architecture §3.4)

This service does **not**:

* Access repositories directly — all DB work is delegated to sub-services
  (Engineering Constitution §8.2).
* Return HTTP responses or reference Flask request objects (layer separation).
* Enforce RBAC — that is the middleware's responsibility (Backend Architecture §6).
* Manage password-reset token delivery — that is ``notification_service``'s job.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from werkzeug.security import check_password_hash

from app.auth import TokenManager, TokenPair
from app.auth.jwt_utils import TokenExpired, TokenInvalid
from app.services.base_service import BaseService, RepositoryContext
from app.services.service_exceptions import (
    Forbidden,
    InvalidStateTransition,
    NotFound,
    ValidationError,
)
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.services.role_permission_service import RolePermissionService


# -- Result types ----------------------------------------------------------


@dataclass(frozen=True)
class LoginResult:
    """Returned by ``AuthService.login()`` on success.

    Contains the token pair and the user's shop memberships so the client
    can immediately render a shop-picker or auto-select (API Architecture §3.1).
    """

    access_token: str
    refresh_token: str
    user_id: UUID
    session_id: UUID
    memberships: List[Dict[str, Any]]
    shop_token: Optional[str] = None


@dataclass(frozen=True)
class RefreshResult:
    """Returned by ``AuthService.refresh()`` on success.

    Per API Architecture §3.3: if the session had a shop context,
    the refreshed tokens include a re-validated shop-scoped token.
    """

    access_token: str
    refresh_token: str
    shop_token: Optional[str] = None


@dataclass(frozen=True)
class ShopSelectResult:
    """Returned by ``AuthService.select_shop()`` on success.

    Contains the shop-scoped access token that every tenant endpoint
    requires (API Architecture §3.2).
    """

    shop_token: str
    shop_id: UUID
    role_id: UUID


# -- Service ---------------------------------------------------------------


class AuthService(BaseService):
    """Authentication lifecycle orchestration (Backend Architecture §3).

    Constructed with a ``RepositoryContext`` (typically ``PlatformContext``
    since auth operations happen before a tenant context is established).
    """

    def __init__(
        self,
        context: RepositoryContext,
        *,
        token_manager: Optional[TokenManager] = None,
    ) -> None:
        super().__init__(context)
        self._user_svc = UserService(context)
        self._session_svc = SessionService(context)
        self._rp_svc = RolePermissionService(context)
        self._token_mgr = token_manager or TokenManager()

    # -- Login (API Architecture §3.1) -------------------------------------

    def login(
        self,
        identifier: str,
        password: str,
        *,
        device_info: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> LoginResult:
        """Authenticate a user by phone/email + password, issue tokens.

        Flow:
            1. Resolve user by phone or email.
            2. Verify password against stored hash.
            3. Create an ``auth_sessions`` row via SessionService.
            4. Issue access + refresh token pair via TokenManager.
            5. Fetch shop memberships for the shop-picker UI.
            6. If exactly one active membership, auto-select shop context
               and include a shop-scoped token (Backend Architecture §5.1).

        Args:
            identifier: Phone number or email address.
            password: Plaintext password to verify.
            device_info: Optional device metadata (JSONB).
            ip_address: Optional client IP (INET).

        Returns:
            ``LoginResult`` with tokens, user ID, session ID, and memberships.

        Raises:
            ValidationError: identifier or password is empty.
            Forbidden: credentials are invalid (generic message to prevent
                account enumeration — API Architecture §3.5).
        """
        if not identifier or not password:
            raise ValidationError(
                "Identifier and password are required.",
                field="identifier",
            )

        user = self._resolve_user(identifier)
        if user is None:
            raise Forbidden("Invalid credentials.")

        if not user.password_hash:
            raise Forbidden("Invalid credentials.")

        if not check_password_hash(user.password_hash, password):
            raise Forbidden("Invalid credentials.")

        if user.status != "Active":
            raise Forbidden("Account is disabled.")

        session_expires = datetime.now(timezone.utc) + timedelta(
            seconds=self._token_mgr.config.refresh_token_ttl_seconds
        )
        session = self._session_svc.create_session(
            user.user_id,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=session_expires,
        )

        pair = self._token_mgr.issue_tokens(
            user.user_id, session.session_id
        )

        memberships = self._build_membership_list(user.user_id)

        shop_token = self._try_auto_select_shop(
            user.user_id, session.session_id, memberships
        )

        return LoginResult(
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            user_id=user.user_id,
            session_id=session.session_id,
            memberships=memberships,
            shop_token=shop_token,
        )

    # -- Shop selection (API Architecture §3.2) ----------------------------

    def select_shop(
        self,
        user_id: UUID,
        session_id: UUID,
        shop_id: UUID,
    ) -> ShopSelectResult:
        """Select the active shop context and mint a shop-scoped token.

        Per API Architecture §3.2: validates that an active ``shop_users``
        row exists for ``(user_id, shop_id)``, sets the shop context on the
        session, and returns a token carrying ``shop_id`` + ``role_id``.

        Args:
            user_id: The authenticated user.
            session_id: The current session (from the base access token).
            shop_id: The target shop to activate.

        Returns:
            ``ShopSelectResult`` with the shop-scoped token and role_id.

        Raises:
            ValidationError: user has no active membership in the target shop.
            InvalidStateTransition: session is revoked or expired.
        """
        self._session_svc.switch_shop(session_id, shop_id)

        role_id = self._resolve_role_for_shop(user_id, shop_id)

        shop_token = self._token_mgr.issue_shop_token(
            user_id, session_id, shop_id, role_id
        )

        return ShopSelectResult(
            shop_token=shop_token,
            shop_id=shop_id,
            role_id=role_id,
        )

    # -- Token refresh (API Architecture §3.3) -----------------------------

    def refresh(self, refresh_token: str) -> RefreshResult:
        """Exchange a refresh token for new tokens.

        Flow:
            1. Validate the refresh token cryptographically (TokenManager).
            2. Validate the session is still active (SessionService).
            3. Issue a new access + refresh token pair (rotation).
            4. If the session has a shop context, re-validate membership and
               re-issue a shop-scoped token with the current role
               (API Architecture §3.3 — role changes take effect on refresh).

        Args:
            refresh_token: The current refresh token string.

        Returns:
            ``RefreshResult`` with new tokens (+ shop_token if applicable).

        Raises:
            Forbidden: token is expired, invalid, or session is revoked.
        """
        try:
            payload = self._token_mgr.validate_refresh_token(refresh_token)
        except (TokenExpired, TokenInvalid) as exc:
            raise Forbidden("Invalid or expired refresh token.") from exc

        try:
            session = self._session_svc.validate_session(payload.session_id)
        except (NotFound, InvalidStateTransition) as exc:
            raise Forbidden("Session is no longer active.") from exc

        new_pair = self._token_mgr.issue_tokens(
            payload.user_id, payload.session_id
        )

        shop_token = None
        if session.shop_id is not None:
            shop_token = self._try_reissue_shop_token(
                payload.user_id, payload.session_id, session.shop_id
            )

        return RefreshResult(
            access_token=new_pair.access_token,
            refresh_token=new_pair.refresh_token,
            shop_token=shop_token,
        )

    # -- Logout (API Architecture §3.4) -----------------------------------

    def logout(self, session_id: UUID) -> None:
        """Revoke the current session.

        Per API Architecture §3.4: revokes only the specified session.
        The access token remains cryptographically valid until its short
        TTL expires — this is acceptable because the access token lifetime
        is ~15 min (Backend Architecture §5.1).
        """
        self._session_svc.revoke_session(session_id)

    def logout_all(self, user_id: UUID) -> int:
        """Revoke all sessions for a user ("log out everywhere").

        Per API Architecture §3.4: used for security recovery when
        unauthorized access is suspected. Also called after password reset
        (API Architecture §3.5).

        Returns:
            Count of sessions revoked.
        """
        return self._session_svc.revoke_all_sessions(user_id)

    # -- Internal helpers --------------------------------------------------

    def _resolve_user(self, identifier: str) -> Optional[Any]:
        """Look up a user by phone or email.

        Phone is tried first (the architecture's primary identifier per
        DB Architecture Domain B — phone is NOT NULL, email is nullable).
        """
        user = self._user_svc.get_user_by_phone(identifier)
        if user is None:
            user = self._user_svc.get_user_by_email(identifier)
        return user

    def _build_membership_list(
        self, user_id: UUID
    ) -> List[Dict[str, Any]]:
        """Build a serializable list of shop memberships for the login response.

        Returns only active memberships with their shop_id and role_id so
        the client can render the shop-picker (API Architecture §3.1).
        """
        raw_memberships = self._user_svc.get_user_shops(user_id)
        return [
            {
                "shop_user_id": str(m.shop_user_id),
                "shop_id": str(m.shop_id),
                "role_id": str(m.role_id),
                "status": m.status,
            }
            for m in raw_memberships
            if m.status == "Active"
        ]

    def _try_auto_select_shop(
        self,
        user_id: UUID,
        session_id: UUID,
        memberships: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Auto-select shop if exactly one active membership exists.

        Per Backend Architecture §5.1: "if the user has exactly one
        shop_users membership, the active shop is auto-selected."
        Returns the shop-scoped token or None.
        """
        if len(memberships) != 1:
            return None

        membership = memberships[0]
        shop_id = UUID(membership["shop_id"])
        role_id = UUID(membership["role_id"])

        try:
            self._session_svc.switch_shop(session_id, shop_id)
        except (ValidationError, InvalidStateTransition):
            return None

        return self._token_mgr.issue_shop_token(
            user_id, session_id, shop_id, role_id
        )

    def _resolve_role_for_shop(
        self, user_id: UUID, shop_id: UUID
    ) -> UUID:
        """Resolve the user's role_id in a specific shop.

        Scans memberships (already fetched by SessionService.switch_shop
        validation) to find the role for the target shop.
        """
        memberships = self._user_svc.get_user_shops(user_id)
        for m in memberships:
            if m.shop_id == shop_id and m.status == "Active":
                return m.role_id

        raise ValidationError(
            "User does not have an active membership in the requested shop.",
            field="shop_id",
        )

    def _try_reissue_shop_token(
        self,
        user_id: UUID,
        session_id: UUID,
        shop_id: UUID,
    ) -> Optional[str]:
        """Re-issue a shop-scoped token during refresh, re-validating membership.

        Per API Architecture §3.3: "re-validated against current shop_users
        state (so a mid-session role downgrade or membership revocation takes
        effect on next refresh, not just next login)."

        Returns the shop token, or None if membership is no longer valid.
        """
        try:
            role_id = self._resolve_role_for_shop(user_id, shop_id)
        except ValidationError:
            return None

        return self._token_mgr.issue_shop_token(
            user_id, session_id, shop_id, role_id
        )
