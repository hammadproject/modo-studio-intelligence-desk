from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db.models import Conversation, HandoffRequest


class HandoffService:
    async def create(
        self,
        session: AsyncSession,
        conversation_id: uuid.UUID,
        reason: str,
        contact_details: dict[str, str] | None = None,
    ) -> HandoffRequest:
        conversation = (
            await session.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if conversation is None:
            raise AppError(404, "conversation_not_found", "Conversation was not found")
        handoff = HandoffRequest(
            conversation_id=conversation_id,
            reason=reason,
            status="recorded",
            contact_details=contact_details,
        )
        conversation.support_status = "waiting_for_human"
        conversation.assigned_admin = None
        conversation.human_requested_at = datetime.now(UTC)
        conversation.resolved_at = None
        session.add(handoff)
        await session.flush()
        return handoff
