from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ConversationCreated(BaseModel):
    conversation_id: uuid.UUID
    access_token: str | None = None
    created_at: datetime


class VisitorConversationSummary(BaseModel):
    conversation_id: uuid.UUID
    preview: str
    support_status: str
    created_at: datetime
    updated_at: datetime


class VisitorConversationPage(BaseModel):
    items: list[VisitorConversationSummary]


class PresenceOutput(BaseModel):
    conversation_id: uuid.UUID
    last_seen_at: datetime


class VisitorConversationClaimInput(BaseModel):
    conversation_id: uuid.UUID
    access_token: str = Field(min_length=1, max_length=500)


class ChatInput(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1)


class SourceCitation(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    source: str
    source_url: str | None = None
    relevance_score: float


class ChatOutput(BaseModel):
    conversation_id: uuid.UUID
    request_id: str
    assistant_message_id: uuid.UUID | None = None
    answer: str
    route: Literal[
        "knowledge",
        "general",
        "clarification",
        "handoff",
        "action",
        "off_topic",
        "human",
    ]
    sources: list[SourceCitation] = Field(default_factory=list)
    handoff_status: str | None = None
    provider_mode: Literal["live", "deterministic"]


class MessageOutput(BaseModel):
    id: uuid.UUID
    sequence: int
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any]


class MessagePage(BaseModel):
    items: list[MessageOutput]
    next_after_sequence: int | None


class HandoffInput(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
    contact_details: dict[str, str] | None = None


class HandoffOutput(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    status: Literal["recorded"]
    reason: str
    created_at: datetime


class KnowledgeDocumentOutput(BaseModel):
    id: uuid.UUID
    collection: str
    title: str
    source: str
    source_url: str | None
    content_hash: str
    version: int
    indexing_status: str
    chunk_count: int
    error_message: str | None


class ReadinessOutput(BaseModel):
    status: Literal["ready", "degraded", "not_ready"]
    database: str
    providers: str
    knowledge_base: Literal["available", "empty", "unavailable"]
    provider_mode: str


class AdminLoginInput(BaseModel):
    api_key: str = Field(min_length=1, max_length=1000)


class AdminSessionOutput(BaseModel):
    authenticated: bool
    display_name: str


class AdminReplyInput(BaseModel):
    message: str = Field(min_length=1, max_length=1500)


class AdminConversationSummary(BaseModel):
    id: uuid.UUID
    visitor_name: str
    topic: str
    preview: str
    support_status: str
    assigned_admin: str | None
    unread_count: int
    message_count: int
    created_at: datetime
    updated_at: datetime
    human_requested_at: datetime | None
    visitor_last_seen_at: datetime | None
    visitor_online: bool


class AdminConversationDetail(BaseModel):
    conversation: AdminConversationSummary
    messages: list[MessageOutput]
    contact_details: dict[str, str] | None = None
    handoff_reason: str | None = None


class AdminConversationPage(BaseModel):
    items: list[AdminConversationSummary]
    counts: dict[str, int]
    next_cursor: datetime | None = None


class AdminConversationActionOutput(BaseModel):
    conversation_id: uuid.UUID
    support_status: str
    assigned_admin: str | None
    message: MessageOutput | None = None
