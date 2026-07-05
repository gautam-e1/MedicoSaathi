"""Identity domain — auth session data access (Backend Architecture §4).

Owns: ``tenant.auth_sessions``.

Sessions are user-scoped with an optional shop context.  ``shop_id`` is nullable
(NULL before the user selects a shop in the multi-shop flow — Backend
Architecture §5.1).  All methods are ``@platform_bypass`` because session
operations happen at the auth layer before a tenant context is established.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from app.extensions.extensions import db
from app.models.identity import AuthSession
from app.repositories.base_repository import BaseRepository, platform_bypass
from app.utils.exceptions import NotFound


class SessionRepository(BaseRepository):
    """Data access for ``tenant.auth_sessions``.

    Session issuance, revocation, and active-shop context management
    (Backend Architecture §4, §5.1).
    Read routing: primary on all methods (auth path — must be fresh).
    """

    model = AuthSession

    @platform_bypass
    def create(self, data: dict) -> AuthSession:
        """Primary (write)."""
        session = AuthSession(**data)
        with self._translate_integrity_errors():
            db.session.add(session)
            db.session.flush()
        return session

    @platform_bypass
    def get_by_id(
        self, session_id: UUID
    ) -> Optional[AuthSession]:
        """Index: auth_sessions_pkey (PK). Primary."""
        return db.session.get(AuthSession, session_id)

    @platform_bypass
    def get_active_sessions(
        self, user_id: UUID
    ) -> List[AuthSession]:
        """Non-revoked, non-expired sessions for a user.

        Index: ix_tenant_auth_sessions_user_id. Primary.
        """
        now = datetime.now(timezone.utc)
        return (
            db.session.query(AuthSession)
            .filter(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .all()
        )

    @platform_bypass
    def revoke(self, session_id: UUID) -> AuthSession:
        """Set ``revoked_at`` on a session.

        Index: auth_sessions_pkey (PK). Primary (write).
        """
        session = db.session.get(AuthSession, session_id)
        if session is None:
            raise NotFound(f"Session {session_id} not found.")
        session.revoked_at = datetime.now(timezone.utc)
        db.session.flush()
        return session

    @platform_bypass
    def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke every active session for a user (e.g. password reset).

        Index: ix_tenant_auth_sessions_user_id. Primary (write).
        Returns the count of sessions revoked.
        """
        now = datetime.now(timezone.utc)
        count = (
            db.session.query(AuthSession)
            .filter(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .update(
                {"revoked_at": now},
                synchronize_session="fetch",
            )
        )
        db.session.flush()
        return count

    @platform_bypass
    def set_shop_context(
        self, session_id: UUID, shop_id: UUID
    ) -> AuthSession:
        """Set the active-shop context on a session (multi-shop flow).

        Index: auth_sessions_pkey (PK). Primary (write).
        """
        session = db.session.get(AuthSession, session_id)
        if session is None:
            raise NotFound(f"Session {session_id} not found.")
        session.shop_id = shop_id
        db.session.flush()
        return session
