from __future__ import annotations

import asyncio
import re
import unicodedata
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import AssistantConfig, BusinessConfig, Settings
from app.core.errors import AppError, ProviderUnavailableError
from app.core.security import content_hash
from app.db.models import (
    ChatRequest,
    Conversation,
    KnowledgeChunk,
    KnowledgeDocument,
    Message,
)
from app.providers.factory import ProviderBundle
from app.schemas.api import ChatOutput, SourceCitation
from app.services.formatting import format_customer_answer, progressive_chunks
from app.services.handoffs import HandoffService
from app.services.memory import MemoryService
from app.services.retrieval import RetrievalService
from app.services.tools import ToolRegistry


def normalize_intent_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold().strip()
    value = re.sub(r"[^\w\s']", " ", value)
    return re.sub(r"\s+", " ", value).strip()


BUSINESS_QUESTION_PATTERN = re.compile(
    r"\b(?:service|package|include|included|inclusion|exclude|excluded|"
    r"e[ -]?commerce|animation|website|webflow|wordpress|branding|identity|"
    r"strategy|price|pricing|cost|timeline|take|revision|deliverable|scope|"
    r"seo|cms|hosting|domain|booking|appointment|project)\b",
    re.IGNORECASE,
)


def is_recognizable_business_question(message: str) -> bool:
    """Keep answerable business questions out of the generic clarification route."""
    return bool(BUSINESS_QUESTION_PATTERN.search(normalize_intent_text(message)))


def guard_customer_answer(
    answer: str, internal_terms: list[str], fallback: str
) -> tuple[str, bool]:
    normalized = answer.casefold()
    if any(term.casefold() in normalized for term in internal_terms):
        return fallback, True
    return answer, False


class ChatService:
    def __init__(
        self,
        settings: Settings,
        business: BusinessConfig,
        assistant: AssistantConfig,
        providers: ProviderBundle,
        tools: ToolRegistry,
    ):
        self.settings = settings
        self.business = business
        self.assistant = assistant
        self.providers = providers
        self.tools = tools
        self.memory = MemoryService(settings)
        self.retrieval = RetrievalService(settings, providers)
        self.handoffs = HandoffService()

    def match_predefined_intent(self, message: str) -> str | None:
        normalized = normalize_intent_text(message)
        matches = sorted(
            self.assistant.intent_matching.predefined_intents,
            key=lambda intent: intent.priority,
            reverse=True,
        )
        for intent in matches:
            if intent.retrieval_required or not intent.responses:
                continue
            if any(
                normalized == normalize_intent_text(example)
                for example in intent.examples
            ):
                return intent.responses[0]
        return None

    async def submit(
        self,
        session: AsyncSession,
        conversation_id: uuid.UUID,
        request_id: str,
        message: str,
    ) -> ChatOutput:
        completed: ChatOutput | None = None
        async for event in self.stream(session, conversation_id, request_id, message):
            if event["type"] == "complete":
                completed = ChatOutput.model_validate(event["response"])
        if completed is None:
            raise RuntimeError("Chat stream ended without a completed response")
        return completed

    async def stream(
        self,
        session: AsyncSession,
        conversation_id: uuid.UUID,
        request_id: str,
        message: str,
    ) -> AsyncIterator[dict[str, Any]]:
        normalized = message.strip()
        if not normalized:
            raise AppError(422, "empty_message", "Message cannot be blank")
        if len(normalized) > self.settings.max_message_chars:
            raise AppError(
                413, "message_too_large", "Message exceeds the configured size limit"
            )
        digest = content_hash(normalized)

        conversation = (
            await session.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        existing = (
            await session.execute(
                select(ChatRequest).where(
                    ChatRequest.conversation_id == conversation_id,
                    ChatRequest.request_id == request_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            if existing.input_hash != digest:
                raise AppError(
                    409,
                    "idempotency_conflict",
                    "Request ID was already used with different input",
                )
            if existing.status == "completed" and existing.response_json:
                completed = ChatOutput.model_validate(existing.response_json)
                yield {"type": "delta", "delta": completed.answer}
                yield {
                    "type": "complete",
                    "response": completed.model_dump(mode="json"),
                }
                return
            if existing.status == "processing":
                raise AppError(
                    409,
                    "turn_in_progress",
                    "A matching turn is still processing; retry later",
                )
            existing.status = "processing"
            existing.error_code = None
            request_record = existing
            user_message = (
                await session.execute(
                    select(Message).where(
                        Message.conversation_id == conversation_id,
                        Message.request_id == request_id,
                        Message.role == "user",
                    )
                )
            ).scalar_one()
        else:
            request_record = ChatRequest(
                conversation_id=conversation_id,
                request_id=request_id,
                input_hash=digest,
                status="processing",
            )
            session.add(request_record)
            user_message = Message(
                conversation_id=conversation_id,
                sequence=conversation.next_sequence,
                role="user",
                content=normalized,
                request_id=request_id,
                metadata_json={},
            )
            conversation.next_sequence += 1
            session.add(user_message)
        await session.flush()

        try:
            if conversation.support_status in {"waiting_for_human", "human_active"}:
                output = ChatOutput(
                    conversation_id=conversation_id,
                    request_id=request_id,
                    assistant_message_id=None,
                    answer="",
                    route="human",
                    sources=[],
                    handoff_status=conversation.support_status,
                    provider_mode=self.providers.llm.mode,
                )
                request_record.status = "completed"
                request_record.response_json = output.model_dump(mode="json")
                await session.commit()
                yield {
                    "type": "complete",
                    "response": output.model_dump(mode="json"),
                }
                return
            if conversation.support_status in {"resolved", "archived"}:
                conversation.support_status = "ai_active"
                conversation.resolved_at = None

            yield {"type": "status", "status": "thinking"}
            history = await self.memory.load(
                session, conversation, user_message.sequence
            )
            sources: list[SourceCitation] = []
            handoff_status = None
            progressively_stream_answer = False

            predefined_answer = self.match_predefined_intent(normalized)
            if predefined_answer is not None:
                route = "general"
                answer = predefined_answer
                decision = None
            else:
                decision = await self.providers.llm.route(
                    normalized, history, conversation.state
                )
                route = decision.route
                if route == "clarification" and is_recognizable_business_question(
                    normalized
                ):
                    route = "knowledge"

            if route == "general":
                pass
            elif route == "handoff":
                handoff = await self.handoffs.create(
                    session, conversation_id, normalized
                )
                handoff_status = handoff.status
                answer = (
                    "I’ve notified the Modo Studio team that you’d like to speak "
                    "with someone. You can keep this chat open and send any extra details here."
                )
            elif route == "clarification":
                answer = self.assistant.general_behavior.ambiguous_message.response
            elif route == "action":
                tool = self.tools.get(decision.action_name or "")
                if tool is None:
                    route = "clarification"
                    answer = "That action is not available. I can answer from approved information or record a handoff request."
                else:
                    conversation.state = {
                        **conversation.state,
                        "pending_action": {
                            "tool": tool.name,
                            "status": "awaiting_confirmation",
                        },
                    }
                    answer = f"The action '{tool.name}' requires confirmation before it can run."
            else:
                indexed_count = await session.scalar(
                    select(func.count(KnowledgeChunk.id))
                    .join(KnowledgeDocument)
                    .where(
                        KnowledgeDocument.collection == self.settings.vector_collection,
                        KnowledgeChunk.indexing_status == "indexed",
                    )
                )
                if not indexed_count:
                    answer = (
                        self.assistant.general_behavior.unknown_business_detail.response
                    )
                else:
                    query = await self.providers.llm.standalone_query(
                        normalized, history
                    )
                    matches = await self.retrieval.retrieve(query)
                    relevant = [
                        item
                        for item in matches
                        if item.score >= self.settings.retrieval_relevance_threshold
                    ]
                    relevant = await self.retrieval.rerank(query, relevant)
                    if not relevant:
                        answer = self.assistant.general_behavior.unknown_business_detail.response
                    else:
                        instructions = "\n".join(
                            [
                                *self.business.instructions,
                                self.assistant.customer_facing_instructions,
                            ]
                        )
                        answer = await self.providers.llm.answer(
                            normalized, history, relevant, instructions
                        )
                        answer = format_customer_answer(answer)
                        if not answer:
                            raise ProviderUnavailableError(
                                "LLM provider returned an empty answer"
                            )
                        progressively_stream_answer = True
                        sources = [
                            SourceCitation(
                                chunk_id=str(
                                    item.metadata.get("chunk_id", item.vector_id)
                                ),
                                document_id=str(item.metadata["document_id"]),
                                title=str(item.metadata["title"]),
                                source=str(item.metadata["source"]),
                                source_url=item.metadata.get("source_url"),
                                relevance_score=item.score,
                            )
                            for item in relevant
                        ]

            answer, replaced_internal_language = guard_customer_answer(
                answer,
                self.assistant.customer_facing_language.internal_terms_to_avoid,
                self.assistant.general_behavior.unknown_business_detail.response,
            )
            if replaced_internal_language:
                sources = []

            if progressively_stream_answer:
                for chunk in progressive_chunks(answer):
                    yield {"type": "delta", "delta": chunk}
                    await asyncio.sleep(0.012)
            else:
                yield {"type": "delta", "delta": answer}

            assistant = Message(
                conversation_id=conversation_id,
                sequence=conversation.next_sequence,
                role="assistant",
                content=answer,
                request_id=request_id,
                metadata_json={
                    "route": route,
                    "sources": [source.model_dump(mode="json") for source in sources],
                    "handoff_status": handoff_status,
                    "provider_mode": self.providers.llm.mode,
                },
            )
            conversation.next_sequence += 1
            session.add(assistant)
            await session.flush()
            output = ChatOutput(
                conversation_id=conversation_id,
                request_id=request_id,
                assistant_message_id=assistant.id,
                answer=answer,
                route=route,
                sources=sources,
                handoff_status=handoff_status,
                provider_mode=self.providers.llm.mode,
            )
            request_record.status = "completed"
            request_record.response_json = output.model_dump(mode="json")
            await session.commit()
            yield {
                "type": "complete",
                "response": output.model_dump(mode="json"),
            }
        except ProviderUnavailableError as exc:
            request_record.status = "failed"
            request_record.error_code = "provider_unavailable"
            await session.commit()
            raise AppError(
                503,
                "provider_unavailable",
                self.assistant.failure_messages.temporary_service_error,
            ) from exc
