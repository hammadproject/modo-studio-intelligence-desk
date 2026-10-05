from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import (
    hash_conversation_token,
    issue_conversation_token,
    verify_secret,
)
from app.db.models import Conversation, Message, VisitorSession


class ConversationService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def create(
        self,
        session: AsyncSession,
        visitor: VisitorSession | None,
        issue_bearer: bool = False,
    ) -> tuple[Conversation, str | None]:
        token = issue_conversation_token() if issue_bearer else None
        conversation = Conversation(
            access_token_hash=(
                hash_conversation_token(token, self.settings.conversation_token_pepper)
                if token
                else None
            ),
            visitor_session_id=visitor.id if visitor else None,
            visitor_last_seen_at=datetime.now(UTC) if visitor else None,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)
        return conversation, token

    async def authenticate(
        self, session: AsyncSession, conversation_id: uuid.UUID, token: str
    ) -> Conversation:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.status != "active":
            raise AppError(404, "conversation_not_found", "Conversation was not found")
        candidate = hash_conversation_token(
            token, self.settings.conversation_token_pepper
        )
        if not conversation.access_token_hash or not verify_secret(
            candidate, conversation.access_token_hash
        ):
            raise AppError(
                403,
                "invalid_conversation_token",
                "Conversation access token is invalid",
            )
        return conversation

    async def authenticate_visitor(
        self,
        session: AsyncSession,
        conversation_id: uuid.UUID,
        visitor: VisitorSession,
    ) -> Conversation:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.status != "active":
            raise AppError(404, "conversation_not_found", "Conversation was not found")
        if conversation.visitor_session_id != visitor.id:
            raise AppError(
                403,
                "visitor_session_mismatch",
                "This conversation does not belong to the current visitor session",
            )
        return conversation

    async def list_for_visitor(
        self, session: AsyncSession, visitor: VisitorSession, limit: int = 100
    ) -> list[Conversation]:
        return list(
            (
                await session.execute(
                    select(Conversation)
                    .where(
                        Conversation.visitor_session_id == visitor.id,
                        Conversation.status == "active",
                    )
                    .order_by(Conversation.updated_at.desc())
                    .limit(limit)
                )
            ).scalars()
        )

    async def touch_presence(
        self, session: AsyncSession, conversation: Conversation
    ) -> datetime:
        now = datetime.now(UTC)
        conversation.visitor_last_seen_at = now
        if conversation.support_status == "archived":
            conversation.support_status = "ai_active"
            conversation.resolved_at = None
        await session.commit()
        return now

    async def history(
        self, session: AsyncSession, conversation_id: uuid.UUID, after: int, limit: int
    ):
        result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.sequence > after)
            .order_by(Message.sequence)
            .limit(limit + 1)
        )
        items = list(result.scalars())
        has_more = len(items) > limit
        return items[:limit], items[limit - 1].sequence if has_more else None

    async def delete(self, session: AsyncSession, conversation_id: uuid.UUID) -> None:
        await session.execute(
            delete(Conversation).where(Conversation.id == conversation_id)
        )
        await session.commit()
