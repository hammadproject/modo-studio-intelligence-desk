from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Text, cast, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import Conversation, HandoffRequest, Message
from app.schemas.api import (
    AdminConversationActionOutput,
    AdminConversationDetail,
    AdminConversationPage,
    AdminConversationSummary,
    MessageOutput,
)


def _message_output(message: Message) -> MessageOutput:
    return MessageOutput(
        id=message.id,
        sequence=message.sequence,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        metadata=message.metadata_json,
    )


class AdminInboxService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def _summary(
        self, session: AsyncSession, conversation: Conversation
    ) -> AdminConversationSummary:
        messages = list(
            (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.sequence)
                )
            ).scalars()
        )
        handoff = (
            await session.execute(
                select(HandoffRequest)
                .where(HandoffRequest.conversation_id == conversation.id)
                .order_by(HandoffRequest.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        contact = handoff.contact_details if handoff else None
        visitor_name = (
            (contact or {}).get("name")
            or (contact or {}).get("full_name")
            or f"Visitor {str(conversation.id)[:5].upper()}"
        )
        first_user = next((item for item in messages if item.role == "user"), None)
        last_message = messages[-1] if messages else None
        topic_source = (
            first_user.content if first_user else "New conversation"
        ).strip()
        topic = topic_source[:52] + ("…" if len(topic_source) > 52 else "")
        preview_source = (
            last_message.content if last_message else "No messages yet"
        ).strip()
        preview = preview_source[:78] + ("…" if len(preview_source) > 78 else "")
        unread_count = sum(
            1
            for item in messages
            if item.role == "user"
            and item.sequence > conversation.admin_read_through_sequence
        )
        online_cutoff = datetime.now(UTC) - timedelta(
            seconds=self.settings.visitor_presence_seconds
        )
        visitor_online = bool(
            conversation.visitor_last_seen_at
            and conversation.visitor_last_seen_at >= online_cutoff
        )
        return AdminConversationSummary(
            id=conversation.id,
            visitor_name=visitor_name,
            topic=topic,
            preview=preview,
            support_status=conversation.support_status,
            assigned_admin=conversation.assigned_admin,
            unread_count=unread_count,
            message_count=len(messages),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            human_requested_at=conversation.human_requested_at,
            visitor_last_seen_at=conversation.visitor_last_seen_at,
            visitor_online=visitor_online,
        )

    async def _archive_stale(self, session: AsyncSession) -> None:
        cutoff = datetime.now(UTC) - timedelta(
            hours=self.settings.conversation_archive_after_hours
        )
        result = await session.execute(
            update(Conversation)
            .where(
                Conversation.status == "active",
                Conversation.support_status == "ai_active",
                Conversation.updated_at < cutoff,
            )
            .values(support_status="archived", resolved_at=datetime.now(UTC))
        )
        if result.rowcount:
            await session.commit()

    async def list(
        self,
        session: AsyncSession,
        status: str | None = None,
        search: str | None = None,
        limit: int = 50,
        scope: str = "inbox",
        time_window: str = "1d",
        cursor: datetime | None = None,
    ) -> AdminConversationPage:
        await self._archive_stale(session)
        statement = select(Conversation).where(Conversation.status == "active")
        if scope == "history":
            statement = statement.where(
                Conversation.support_status.in_(["resolved", "archived"])
            )
        else:
            statement = statement.where(
                Conversation.support_status.not_in(["resolved", "archived"])
            )
        if status and status != "all":
            statement = statement.where(Conversation.support_status == status)
        window_hours = {
            "6h": 6,
            "12h": 12,
            "1d": 24,
            "3d": 72,
            "7d": 168,
            "30d": 720,
        }
        if time_window != "all":
            hours = window_hours.get(time_window)
            if hours is None:
                raise AppError(
                    422, "invalid_time_window", "Time window is not supported"
                )
            cutoff = datetime.now(UTC) - timedelta(hours=hours)
            # Human requests never disappear from the actionable inbox because of age.
            if scope == "inbox":
                statement = statement.where(
                    or_(
                        Conversation.updated_at >= cutoff,
                        Conversation.support_status == "waiting_for_human",
                    )
                )
            else:
                statement = statement.where(Conversation.updated_at >= cutoff)
        if cursor:
            statement = statement.where(Conversation.updated_at < cursor)
        if search:
            pattern = f"%{search.strip()}%"
            matching_ids = select(Message.conversation_id).where(
                Message.content.ilike(pattern)
            )
            matching_handoffs = select(HandoffRequest.conversation_id).where(
                or_(
                    HandoffRequest.reason.ilike(pattern),
                    cast(HandoffRequest.contact_details, Text).ilike(pattern),
                )
            )
            statement = statement.where(
                or_(
                    Conversation.assigned_admin.ilike(pattern),
                    Conversation.id.in_(matching_ids),
                    Conversation.id.in_(matching_handoffs),
                )
            )
        conversations = list(
            (
                await session.execute(
                    statement.order_by(Conversation.updated_at.desc()).limit(limit + 1)
                )
            ).scalars()
        )
        has_more = len(conversations) > limit
        conversations = conversations[:limit]
        count_rows = (
            await session.execute(
                select(Conversation.support_status, func.count(Conversation.id))
                .where(Conversation.status == "active")
                .group_by(Conversation.support_status)
            )
        ).all()
        counts = {key: value for key, value in count_rows}
        counts["all"] = sum(counts.values())
        counts["history"] = counts.get("resolved", 0) + counts.get("archived", 0)
        counts["inbox"] = counts["all"] - counts["history"]
        return AdminConversationPage(
            items=[await self._summary(session, item) for item in conversations],
            counts=counts,
            next_cursor=(conversations[-1].updated_at if has_more else None),
        )

    async def detail(
        self, session: AsyncSession, conversation_id: uuid.UUID, mark_read: bool = True
    ) -> AdminConversationDetail:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None or conversation.status != "active":
            raise AppError(404, "conversation_not_found", "Conversation was not found")
        messages = list(
            (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.sequence)
                )
            ).scalars()
        )
        if mark_read and messages:
            read_through = messages[-1].sequence
            await session.execute(
                update(Conversation)
                .where(Conversation.id == conversation.id)
                .values(
                    admin_read_through_sequence=read_through,
                    updated_at=conversation.updated_at,
                )
                .execution_options(synchronize_session=False)
            )
            await session.commit()
            await session.refresh(conversation)
        handoff = (
            await session.execute(
                select(HandoffRequest)
                .where(HandoffRequest.conversation_id == conversation_id)
                .order_by(HandoffRequest.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return AdminConversationDetail(
            conversation=await self._summary(session, conversation),
            messages=[_message_output(item) for item in messages],
            contact_details=handoff.contact_details if handoff else None,
            handoff_reason=handoff.reason if handoff else None,
        )

    async def _locked_conversation(
        self, session: AsyncSession, conversation_id: uuid.UUID
    ) -> Conversation:
        conversation = (
            await session.execute(
                select(Conversation)
                .where(
                    Conversation.id == conversation_id,
                    Conversation.status == "active",
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if conversation is None:
            raise AppError(404, "conversation_not_found", "Conversation was not found")
        return conversation

    async def _system_message(
        self, session: AsyncSession, conversation: Conversation, content: str
    ) -> Message:
        message = Message(
            conversation_id=conversation.id,
            sequence=conversation.next_sequence,
            role="system",
            content=content,
            metadata_json={"event": "support_status"},
        )
        conversation.next_sequence += 1
        session.add(message)
        await session.flush()
        return message

    async def takeover(
        self, session: AsyncSession, conversation_id: uuid.UUID
    ) -> AdminConversationActionOutput:
        conversation = await self._locked_conversation(session, conversation_id)
        if conversation.support_status in {"resolved", "archived"}:
            raise AppError(
                409,
                "inactive_conversation",
                "This conversation is inactive and can only be viewed",
            )
        if conversation.support_status == "human_active":
            if conversation.assigned_admin != self.settings.admin_display_name:
                raise AppError(
                    409,
                    "conversation_assigned",
                    "Another operator owns this conversation",
                )
            return AdminConversationActionOutput(
                conversation_id=conversation.id,
                support_status=conversation.support_status,
                assigned_admin=conversation.assigned_admin,
            )
        conversation.support_status = "human_active"
        conversation.assigned_admin = self.settings.admin_display_name
        conversation.takeover_at = datetime.now(UTC)
        conversation.resolved_at = None
        message = await self._system_message(
            session,
            conversation,
            f"{self.settings.admin_display_name} joined the conversation.",
        )
        await session.execute(
            HandoffRequest.__table__.update()
            .where(
                HandoffRequest.conversation_id == conversation.id,
                HandoffRequest.status == "recorded",
            )
            .values(status="accepted")
        )
        await session.commit()
        return AdminConversationActionOutput(
            conversation_id=conversation.id,
            support_status=conversation.support_status,
            assigned_admin=conversation.assigned_admin,
            message=_message_output(message),
        )

    async def release(
        self, session: AsyncSession, conversation_id: uuid.UUID
    ) -> AdminConversationActionOutput:
        conversation = await self._locked_conversation(session, conversation_id)
        conversation.support_status = "ai_active"
        conversation.assigned_admin = None
        message = await self._system_message(
            session, conversation, "Ren is handling the conversation again."
        )
        await session.commit()
        return AdminConversationActionOutput(
            conversation_id=conversation.id,
            support_status=conversation.support_status,
            assigned_admin=None,
            message=_message_output(message),
        )

    async def resolve(
        self, session: AsyncSession, conversation_id: uuid.UUID
    ) -> AdminConversationActionOutput:
        conversation = await self._locked_conversation(session, conversation_id)
        conversation.support_status = "resolved"
        conversation.assigned_admin = None
        conversation.resolved_at = datetime.now(UTC)
        message = await self._system_message(
            session, conversation, "This conversation was marked as resolved."
        )
        await session.execute(
            HandoffRequest.__table__.update()
            .where(HandoffRequest.conversation_id == conversation.id)
            .values(status="resolved")
        )
        await session.commit()
        return AdminConversationActionOutput(
            conversation_id=conversation.id,
            support_status=conversation.support_status,
            assigned_admin=None,
            message=_message_output(message),
        )

    async def reply(
        self, session: AsyncSession, conversation_id: uuid.UUID, content: str
    ) -> MessageOutput:
        conversation = await self._locked_conversation(session, conversation_id)
        if conversation.support_status != "human_active":
            raise AppError(
                409, "takeover_required", "Take over the conversation before replying"
            )
        message = Message(
            conversation_id=conversation.id,
            sequence=conversation.next_sequence,
            role="operator",
            content=content.strip(),
            metadata_json={"operator": self.settings.admin_display_name},
        )
        conversation.next_sequence += 1
        conversation.updated_at = datetime.now(UTC)
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return _message_output(message)
