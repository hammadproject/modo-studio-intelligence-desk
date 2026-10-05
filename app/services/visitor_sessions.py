from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    hash_conversation_token,
    issue_visitor_session_token,
)
from app.db.models import VisitorSession


VISITOR_COOKIE = "modo_visitor_session"


class VisitorSessionService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _hash(self, token: str) -> str:
        return hash_conversation_token(
            f"visitor:{token}", self.settings.conversation_token_pepper
        )

    async def resolve(
        self, session: AsyncSession, request: Request
    ) -> VisitorSession | None:
        token = request.cookies.get(VISITOR_COOKIE)
        if not token:
            return None
        now = datetime.now(UTC)
        visitor = (
            await session.execute(
                select(VisitorSession).where(
                    VisitorSession.token_hash == self._hash(token),
                    VisitorSession.revoked_at.is_(None),
                    VisitorSession.expires_at > now,
                )
            )
        ).scalar_one_or_none()
        return visitor

    async def get_or_create(
        self, session: AsyncSession, request: Request, response: Response
    ) -> VisitorSession:
        visitor = await self.resolve(session, request)
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self.settings.visitor_session_days)
        if visitor is None:
            token = issue_visitor_session_token()
            visitor = VisitorSession(
                token_hash=self._hash(token),
                last_seen_at=now,
                expires_at=expires_at,
            )
            session.add(visitor)
            await session.flush()
            response.set_cookie(
                VISITOR_COOKIE,
                token,
                max_age=self.settings.visitor_session_days * 86400,
                httponly=True,
                secure=self.settings.environment == "production",
                samesite=self.settings.visitor_cookie_samesite,
                path="/",
            )
        else:
            visitor.last_seen_at = now
            visitor.expires_at = expires_at
        return visitor

    async def touch(self, visitor: VisitorSession) -> None:
        now = datetime.now(UTC)
        visitor.last_seen_at = now
        visitor.expires_at = now + timedelta(days=self.settings.visitor_session_days)
