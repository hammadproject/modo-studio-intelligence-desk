from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import Conversation, Message
from app.providers.base import ChatTurn


def estimated_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


class MemoryService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def load(
        self, session: AsyncSession, conversation: Conversation, before_sequence: int
    ) -> list[ChatTurn]:
        result = await session.execute(
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.sequence > conversation.summary_through_sequence,
                Message.sequence < before_sequence,
                Message.role.in_(["user", "assistant"]),
            )
            .order_by(Message.sequence)
        )
        messages = list(result.scalars())
        total = sum(estimated_tokens(item.content) for item in messages)
        if total > self.settings.summary_trigger_tokens:
            kept: list[Message] = []
            kept_tokens = 0
            for item in reversed(messages):
                cost = estimated_tokens(item.content)
                if kept and kept_tokens + cost > self.settings.history_token_budget:
                    break
                kept.append(item)
                kept_tokens += cost
            boundary = kept[-1].sequence - 1 if kept else messages[-1].sequence
            summarized = [item for item in messages if item.sequence <= boundary]
            if summarized:
                additions = "\n".join(
                    f"{item.role}: {item.content}" for item in summarized
                )
                conversation.summary = "\n".join(
                    filter(None, [conversation.summary, additions])
                )[-12000:]
                conversation.summary_through_sequence = boundary
                messages = list(reversed(kept))
                await session.flush()

        turns: list[ChatTurn] = []
        if conversation.summary:
            turns.append(
                ChatTurn(
                    "system",
                    "Earlier speaker-attributed conversation (not business-policy evidence):\n"
                    f"{conversation.summary}",
                )
            )
        budget = self.settings.history_token_budget
        selected: list[Message] = []
        for item in reversed(messages):
            cost = estimated_tokens(item.content)
            if selected and budget - cost < 0:
                break
            selected.append(item)
            budget -= cost
        turns.extend(ChatTurn(item.role, item.content) for item in reversed(selected))
        return turns
