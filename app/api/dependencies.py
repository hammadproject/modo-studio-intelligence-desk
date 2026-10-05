from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import verify_admin_session, verify_secret
from app.db.models import Conversation, VisitorSession

bearer = HTTPBearer(auto_error=False)


async def get_session(request: Request):
    async with request.app.state.database.sessions() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def authorized_conversation(
    conversation_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Conversation:
    if credentials is not None:
        if credentials.scheme.lower() != "bearer":
            raise AppError(
                401, "conversation_token_required", "A valid credential is required"
            )
        return await request.app.state.conversations.authenticate(
            session, conversation_id, credentials.credentials
        )
    visitor = await request.app.state.visitor_sessions.resolve(session, request)
    if visitor is None:
        raise AppError(
            401,
            "visitor_session_required",
            "A valid visitor session is required",
        )
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in request.app.state.settings.cors_origins:
            raise AppError(403, "origin_not_allowed", "Request origin is not allowed")
    return await request.app.state.conversations.authenticate_visitor(
        session, conversation_id, visitor
    )


ConversationDep = Annotated[Conversation, Depends(authorized_conversation)]


async def require_visitor_session(
    request: Request, session: SessionDep
) -> VisitorSession:
    visitor = await request.app.state.visitor_sessions.resolve(session, request)
    if visitor is None:
        raise AppError(
            401, "visitor_session_required", "A valid visitor session is required"
        )
    return visitor


VisitorSessionDep = Annotated[VisitorSession, Depends(require_visitor_session)]


async def require_admin(
    request: Request, x_admin_key: Annotated[str | None, Header()] = None
) -> None:
    settings = request.app.state.settings
    key_is_valid = bool(x_admin_key) and verify_secret(
        x_admin_key or "", settings.admin_api_key
    )
    cookie = request.cookies.get("modo_admin_session", "")
    session_is_valid = verify_admin_session(
        cookie,
        settings.admin_api_key,
        settings.admin_session_hours * 3600,
    )
    if not key_is_valid and not session_is_valid:
        raise AppError(
            403, "admin_access_denied", "A valid administrative credential is required"
        )


AdminDep = Annotated[None, Depends(require_admin)]
