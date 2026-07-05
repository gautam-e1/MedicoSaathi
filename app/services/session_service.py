"""Identity domain — session lifecycle orchestration (Backend Architecture §3).

Calls: ``SessionRepository`` (primary), ``UserRepository`` (membership
lookup for shop-context switching — same domain, Backend Architecture §4).

Business rules owned by this service:

* Session creation with expiry.
* Session validation (not revoked, not expired).
* Single-session and bulk revocation (password-reset flow).
* Shop-context switching with membership verification
  (Backend Architecture §5.1).

This service does **not** own:

* Credential verification (future ``auth_service``).
* JWT issuance or verification (future ``auth_service``).
* Token refresh mechanics (future ``auth_service``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.repositories.identity.session_repository import SessionRepository
from app.repositories.identity.user_repository import UserRepository
from app.services.base_service import BaseService, RepositoryContext
from app.services.service_exceptions import (
    InvalidStateTransition,
    NotFound,
    ValidationError,
)


class SessionService(BaseService):
    """Session lifecycle business orchestration."""

    def __init__(self, context: RepositoryContext) -> None:
        super().__init__(context)
        self._session_repo = SessionRepository(context)
        self._user_repo = UserRepository(context)

    # -- session creation ---------------------------------------------------

    def create_session(
        self,
        user_id: UUID,
        *,
        device_info: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Any:
        """Create a new auth session for a user.

        The caller (future ``auth_service``) is responsible for
        credential verification before calling this method.
        """
        data: Dict[str, Any] = {"user_id": user_id}
        if device_info is not None:
            data["device_info"] = device_info
        if ip_address is not None:
            data["ip_address"] = ip_address
        if expires_at is not None:
            data["expires_at"] = expires_at

        with self.transaction():
            session = self._session_repo.create(data)
        return session

    # -- session lookup / validation ----------------------------------------

    def get_session(self, session_id: UUID) -> Optional[Any]:
        """Look up a session by ID."""
        return self._session_repo.get_by_id(session_id)

    def get_session_or_raise(self, session_id: UUID) -> Any:
        """Look up a session by ID; raise ``NotFound`` if absent."""
        session = self._session_repo.get_by_id(session_id)
        if session is None:
            raise NotFound(f"Session {session_id} not found.")
        return session

    def validate_session(self, session_id: UUID) -> Any:
        """Validate that a session is active (not revoked, not expired).

        Returns the session if valid; raises ``InvalidStateTransition``
        if the session has been revoked or has expired.
        """
        session = self.get_session_or_raise(session_id)

        if session.revoked_at is not None:
            raise InvalidStateTransition(
                "Session has been revoked.",
                current_state="revoked",
                attempted_state="active",
            )
        if (
            session.expires_at is not None
            and session.expires_at <= datetime.now(timezone.utc)
        ):
            raise InvalidStateTransition(
                "Session has expired.",
                current_state="expired",
                attempted_state="active",
            )
        return session

    def get_active_sessions(self, user_id: UUID) -> List[Any]:
        """Return all active (non-revoked, non-expired) sessions for a user."""
        return self._session_repo.get_active_sessions(user_id)

    # -- session revocation -------------------------------------------------

    def revoke_session(self, session_id: UUID) -> Any:
        """Revoke a single session."""
        with self.transaction():
            session = self._session_repo.revoke(session_id)
        return session

    def revoke_all_sessions(self, user_id: UUID) -> int:
        """Revoke all active sessions for a user (e.g. password reset).

        Returns the count of sessions revoked.
        """
        with self.transaction():
            count = self._session_repo.revoke_all_for_user(user_id)
        return count

    # -- shop-context switching ---------------------------------------------

    def switch_shop(self, session_id: UUID, shop_id: UUID) -> Any:
        """Set the active shop context on a session.

        Verifies that the session is valid and that the user has an
        active membership in the target shop before switching
        (Backend Architecture §5.1).
        """
        session = self.validate_session(session_id)

        memberships = self._user_repo.get_memberships_for_user(
            session.user_id
        )
        active_shop_ids = {
            m.shop_id
            for m in memberships
            if getattr(m, "status", "Active") == "Active"
        }

        if shop_id not in active_shop_ids:
            raise ValidationError(
                "User does not have an active membership in the "
                "requested shop.",
                field="shop_id",
            )

        with self.transaction():
            session = self._session_repo.set_shop_context(
                session_id, shop_id
            )
        return session
