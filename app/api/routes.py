from __future__ import annotations

import asyncio
import io
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    File,
    Form,
    Header,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from pypdf import PdfReader
from sqlalchemy import func, select, text

from app.api.dependencies import (
    AdminDep,
    ConversationDep,
    SessionDep,
    VisitorSessionDep,
)
from app.core.errors import AppError
from app.core.security import issue_admin_session, verify_secret
from app.db.models import KnowledgeChunk, KnowledgeDocument, Message
from app.schemas.api import (
    AdminConversationActionOutput,
    AdminConversationDetail,
    AdminConversationPage,
    AdminLoginInput,
    AdminReplyInput,
    AdminSessionOutput,
    ChatInput,
    ChatOutput,
    ConversationCreated,
    HandoffInput,
    HandoffOutput,
    KnowledgeDocumentOutput,
    MessageOutput,
    MessagePage,
    PresenceOutput,
    ReadinessOutput,
    VisitorConversationPage,
    VisitorConversationClaimInput,
    VisitorConversationSummary,
)

router = APIRouter()


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/health/ready", response_model=ReadinessOutput)
async def ready(request: Request, session: SessionDep) -> ReadinessOutput:
    database_status = "ready"
    knowledge = "empty"
    try:
        await session.execute(text("SELECT 1"))
        count = await session.scalar(
            select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.indexing_status == "indexed"
            )
        )
        knowledge = "available" if count else "empty"
    except Exception:
        database_status = "unavailable"
        knowledge = "unavailable"
    settings = request.app.state.settings
    providers = "configured"
    if settings.provider_mode == "live" and (
        not settings.groq_api_key or not settings.pinecone_api_key
    ):
        providers = "misconfigured"
    overall = (
        "ready"
        if database_status == "ready" and providers == "configured"
        else "not_ready"
    )
    if overall == "ready" and knowledge == "empty":
        overall = "degraded"
    return ReadinessOutput(
        status=overall,
        database=database_status,
        providers=providers,
        knowledge_base=knowledge,
        provider_mode=settings.provider_mode,
    )


@router.post(
    "/api/v1/conversations",
    response_model=ConversationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: Request,
    response: Response,
    session: SessionDep,
    x_conversation_token_mode: Annotated[str | None, Header()] = None,
) -> ConversationCreated:
    issue_bearer = x_conversation_token_mode == "bearer"
    visitor = (
        None
        if issue_bearer
        else await request.app.state.visitor_sessions.get_or_create(
            session, request, response
        )
    )
    conversation, token = await request.app.state.conversations.create(
        session,
        visitor,
        issue_bearer=issue_bearer,
    )
    return ConversationCreated(
        conversation_id=conversation.id,
        access_token=token,
        created_at=conversation.created_at,
    )


@router.get("/api/v1/visitor/conversations", response_model=VisitorConversationPage)
async def visitor_conversations(
    request: Request,
    session: SessionDep,
    visitor: VisitorSessionDep,
) -> VisitorConversationPage:
    items = await request.app.state.conversations.list_for_visitor(session, visitor)
    ids = [item.id for item in items]
    message_rows = (
        (
            await session.execute(
                select(Message.conversation_id, Message.content)
                .where(Message.conversation_id.in_(ids))
                .order_by(Message.conversation_id, Message.sequence)
            )
        ).all()
        if ids
        else []
    )
    previews = {conversation_id: content for conversation_id, content in message_rows}
    return VisitorConversationPage(
        items=[
            VisitorConversationSummary(
                conversation_id=item.id,
                preview=(previews.get(item.id) or "No messages yet")[:160],
                support_status=item.support_status,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in items
        ]
    )


@router.post(
    "/api/v1/conversations/{conversation_id}/presence",
    response_model=PresenceOutput,
)
async def conversation_presence(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    conversation: ConversationDep,
) -> PresenceOutput:
    last_seen = await request.app.state.conversations.touch_presence(
        session, conversation
    )
    visitor = await request.app.state.visitor_sessions.resolve(session, request)
    if visitor is not None:
        await request.app.state.visitor_sessions.touch(visitor)
        await session.commit()
    return PresenceOutput(conversation_id=conversation_id, last_seen_at=last_seen)


@router.post(
    "/api/v1/conversations/{conversation_id}/messages", response_model=ChatOutput
)
async def send_message(
    conversation_id: uuid.UUID,
    body: ChatInput,
    request: Request,
    session: SessionDep,
    conversation: ConversationDep,
) -> ChatOutput:
    return await request.app.state.chat.submit(
        session, conversation.id, body.request_id, body.message
    )


@router.post("/api/v1/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: uuid.UUID,
    body: ChatInput,
    request: Request,
    session: SessionDep,
    conversation: ConversationDep,
) -> StreamingResponse:
    async def events():
        try:
            async for event in request.app.state.chat.stream(
                session, conversation.id, body.request_id, body.message
            ):
                event_type = str(event["type"])
                payload = {key: value for key, value in event.items() if key != "type"}
                yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        except AppError as exc:
            payload = {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            }
            yield f"event: error\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/api/v1/conversations/{conversation_id}/messages", response_model=MessagePage
)
async def message_history(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    conversation: ConversationDep,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MessagePage:
    items, cursor = await request.app.state.conversations.history(
        session, conversation.id, after_sequence, limit
    )
    return MessagePage(
        items=[
            MessageOutput(
                id=item.id,
                sequence=item.sequence,
                role=item.role,
                content=item.content,
                created_at=item.created_at,
                metadata=item.metadata_json,
            )
            for item in items
        ],
        next_after_sequence=cursor,
    )


@router.post(
    "/api/v1/visitor/conversations/claim",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def claim_legacy_conversation(
    body: VisitorConversationClaimInput,
    request: Request,
    response: Response,
    session: SessionDep,
) -> Response:
    origin = request.headers.get("origin")
    if origin and origin not in request.app.state.settings.cors_origins:
        raise AppError(403, "origin_not_allowed", "Request origin is not allowed")
    visitor = await request.app.state.visitor_sessions.get_or_create(
        session, request, response
    )
    conversation = await request.app.state.conversations.authenticate(
        session, body.conversation_id, body.access_token
    )
    if conversation.visitor_session_id not in {None, visitor.id}:
        raise AppError(
            409,
            "conversation_already_claimed",
            "This conversation belongs to another visitor session",
        )
    conversation.visitor_session_id = visitor.id
    conversation.visitor_last_seen_at = datetime.now(UTC)
    await session.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.delete(
    "/api/v1/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    conversation: ConversationDep,
) -> Response:
    await request.app.state.conversations.delete(session, conversation.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/api/v1/conversations/{conversation_id}/handoffs",
    response_model=HandoffOutput,
    status_code=status.HTTP_201_CREATED,
)
async def create_handoff(
    conversation_id: uuid.UUID,
    body: HandoffInput,
    request: Request,
    session: SessionDep,
    conversation: ConversationDep,
) -> HandoffOutput:
    handoff = await request.app.state.handoffs.create(
        session, conversation.id, body.reason, body.contact_details
    )
    await session.commit()
    await session.refresh(handoff)
    return HandoffOutput.model_validate(handoff, from_attributes=True)


def _pdf_text(payload: bytes) -> str:
    reader = PdfReader(io.BytesIO(payload))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


@router.post("/api/v1/admin/session", response_model=AdminSessionOutput)
async def create_admin_session(
    body: AdminLoginInput, request: Request, response: Response
) -> AdminSessionOutput:
    settings = request.app.state.settings
    if not verify_secret(body.api_key, settings.admin_api_key):
        raise AppError(403, "admin_access_denied", "The admin key is incorrect")
    response.set_cookie(
        "modo_admin_session",
        issue_admin_session(settings.admin_api_key),
        max_age=settings.admin_session_hours * 3600,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path="/api/v1/admin",
    )
    return AdminSessionOutput(
        authenticated=True, display_name=settings.admin_display_name
    )


@router.get("/api/v1/admin/session", response_model=AdminSessionOutput)
async def read_admin_session(request: Request, _: AdminDep) -> AdminSessionOutput:
    return AdminSessionOutput(
        authenticated=True,
        display_name=request.app.state.settings.admin_display_name,
    )


@router.delete("/api/v1/admin/session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_session(response: Response) -> Response:
    response.delete_cookie("modo_admin_session", path="/api/v1/admin")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/api/v1/admin/conversations", response_model=AdminConversationPage)
async def list_admin_conversations(
    request: Request,
    session: SessionDep,
    _: AdminDep,
    support_status: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    scope: Annotated[str, Query(pattern="^(inbox|history)$")] = "inbox",
    time_window: Annotated[str, Query(pattern="^(6h|12h|1d|3d|7d|30d|all)$")] = "1d",
    cursor: Annotated[datetime | None, Query()] = None,
) -> AdminConversationPage:
    return await request.app.state.admin_inbox.list(
        session, support_status, search, limit, scope, time_window, cursor
    )


@router.get(
    "/api/v1/admin/conversations/{conversation_id}",
    response_model=AdminConversationDetail,
)
async def admin_conversation_detail(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _: AdminDep,
) -> AdminConversationDetail:
    return await request.app.state.admin_inbox.detail(session, conversation_id)


@router.post(
    "/api/v1/admin/conversations/{conversation_id}/takeover",
    response_model=AdminConversationActionOutput,
)
async def takeover_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _: AdminDep,
) -> AdminConversationActionOutput:
    return await request.app.state.admin_inbox.takeover(session, conversation_id)


@router.post(
    "/api/v1/admin/conversations/{conversation_id}/release",
    response_model=AdminConversationActionOutput,
)
async def release_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _: AdminDep,
) -> AdminConversationActionOutput:
    return await request.app.state.admin_inbox.release(session, conversation_id)


@router.post(
    "/api/v1/admin/conversations/{conversation_id}/resolve",
    response_model=AdminConversationActionOutput,
)
async def resolve_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    _: AdminDep,
) -> AdminConversationActionOutput:
    return await request.app.state.admin_inbox.resolve(session, conversation_id)


@router.post(
    "/api/v1/admin/conversations/{conversation_id}/messages",
    response_model=MessageOutput,
)
async def send_admin_reply(
    conversation_id: uuid.UUID,
    body: AdminReplyInput,
    request: Request,
    session: SessionDep,
    _: AdminDep,
) -> MessageOutput:
    return await request.app.state.admin_inbox.reply(
        session, conversation_id, body.message
    )


@router.post(
    "/api/v1/admin/knowledge/documents", response_model=KnowledgeDocumentOutput
)
async def ingest_document(
    request: Request,
    session: SessionDep,
    _: AdminDep,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
    source: Annotated[str | None, Form()] = None,
    source_url: Annotated[str | None, Form()] = None,
    collection: Annotated[str | None, Form()] = None,
) -> KnowledgeDocumentOutput:
    settings = request.app.state.settings
    payload = await file.read(settings.max_upload_bytes + 1)
    if len(payload) > settings.max_upload_bytes:
        raise AppError(
            413,
            "upload_too_large",
            "Uploaded document exceeds the configured size limit",
        )
    filename = file.filename or "document.txt"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".md", ".pdf"}:
        raise AppError(
            415,
            "unsupported_document",
            "Only UTF-8 text, Markdown, and text-based PDFs are supported",
        )
    try:
        document_text = (
            await asyncio.to_thread(_pdf_text, payload)
            if suffix == ".pdf"
            else payload.decode("utf-8")
        )
    except (UnicodeDecodeError, ValueError) as exc:
        raise AppError(
            422,
            "unreadable_document",
            "The document could not be read as supported text",
        ) from exc
    if not document_text.strip():
        raise AppError(
            422,
            "empty_document",
            "The PDF has no extractable text"
            if suffix == ".pdf"
            else "Document is empty",
        )
    result = await request.app.state.ingestion.ingest(
        session,
        title=title or Path(filename).stem,
        source=source or filename,
        text=document_text,
        source_url=source_url,
        collection=collection,
        metadata={"filename": filename, "content_type": file.content_type},
    )
    return KnowledgeDocumentOutput(
        id=result.document.id,
        collection=result.document.collection,
        title=result.document.title,
        source=result.document.source,
        source_url=result.document.source_url,
        content_hash=result.document.content_hash,
        version=result.document.version,
        indexing_status=result.document.indexing_status,
        chunk_count=result.chunk_count,
        error_message=result.document.error_message,
    )


@router.get(
    "/api/v1/admin/knowledge/documents", response_model=list[KnowledgeDocumentOutput]
)
async def list_documents(
    session: SessionDep, _: AdminDep
) -> list[KnowledgeDocumentOutput]:
    result = await session.execute(
        select(KnowledgeDocument, func.count(KnowledgeChunk.id))
        .outerjoin(KnowledgeChunk)
        .group_by(KnowledgeDocument.id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    return [
        KnowledgeDocumentOutput(
            id=document.id,
            collection=document.collection,
            title=document.title,
            source=document.source,
            source_url=document.source_url,
            content_hash=document.content_hash,
            version=document.version,
            indexing_status=document.indexing_status,
            chunk_count=count,
            error_message=document.error_message,
        )
        for document, count in result.all()
    ]


@router.post(
    "/api/v1/admin/knowledge/documents/{document_id}/retry",
    response_model=KnowledgeDocumentOutput,
)
async def retry_document(
    document_id: uuid.UUID, request: Request, session: SessionDep, _: AdminDep
):
    document = await session.get(KnowledgeDocument, document_id)
    if document is None:
        raise AppError(404, "document_not_found", "Knowledge document was not found")
    result = await request.app.state.ingestion.retry(session, document)
    return KnowledgeDocumentOutput(
        id=document.id,
        collection=document.collection,
        title=document.title,
        source=document.source,
        source_url=document.source_url,
        content_hash=document.content_hash,
        version=document.version,
        indexing_status=document.indexing_status,
        chunk_count=result.chunk_count,
        error_message=document.error_message,
    )


@router.delete(
    "/api/v1/admin/knowledge/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: uuid.UUID, request: Request, session: SessionDep, _: AdminDep
) -> Response:
    document = await session.get(KnowledgeDocument, document_id)
    if document is None:
        raise AppError(404, "document_not_found", "Knowledge document was not found")
    await request.app.state.ingestion.delete(session, document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
