from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.db.base import Database
from app.providers import ProviderBundle, build_providers
from app.services.chat import ChatService
from app.services.admin_inbox import AdminInboxService
from app.services.conversations import ConversationService
from app.services.handoffs import HandoffService
from app.services.ingestion import IngestionService
from app.services.visitor_sessions import VisitorSessionService
from app.services.tools import ToolRegistry, ToolService

logger = logging.getLogger("modo_studio_intelligence_desk")


def create_app(
    settings: Settings | None = None, providers: ProviderBundle | None = None
) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.assistant_config = settings.load_assistant_config()
        app.state.database = Database(settings)
        app.state.providers = providers or build_providers(settings)
        app.state.conversations = ConversationService(settings)
        app.state.visitor_sessions = VisitorSessionService(settings)
        app.state.admin_inbox = AdminInboxService(settings)
        app.state.handoffs = HandoffService()
        app.state.tools = ToolRegistry()
        app.state.tool_service = ToolService(app.state.tools)
        app.state.chat = ChatService(
            settings,
            settings.load_business_config(),
            app.state.assistant_config,
            app.state.providers,
            app.state.tools,
        )
        app.state.ingestion = IngestionService(settings, app.state.providers)
        app.state.rate_windows = defaultdict(deque)
        yield
        await app.state.database.dispose()

    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Admin-Key",
            "X-Conversation-Token-Mode",
            "X-Request-ID",
        ],
    )

    @app.middleware("http")
    async def operational_middleware(request: Request, call_next):
        correlation_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        start = time.perf_counter()
        if request.url.path != "/health/live":
            is_admin_operation = (
                request.url.path.startswith("/api/v1/admin/")
                and request.url.path != "/api/v1/admin/session"
            )
            scope = "admin" if is_admin_operation else "public"
            limit = (
                settings.admin_requests_per_minute
                if is_admin_operation
                else settings.requests_per_minute
            )
            client_host = request.client.host if request.client else "unknown"
            key = f"{scope}:{client_host}"
            now = time.monotonic()
            window = request.app.state.rate_windows[key]
            while window and window[0] < now - 60:
                window.popleft()
            if len(window) >= limit:
                response_headers = {
                    "X-Request-ID": correlation_id,
                    "Retry-After": "60",
                }
                origin = request.headers.get("origin")
                if origin in settings.cors_origins:
                    response_headers.update(
                        {
                            "Access-Control-Allow-Origin": origin,
                            "Access-Control-Allow-Credentials": "true",
                            "Vary": "Origin",
                        }
                    )
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Request limit exceeded",
                            "request_id": correlation_id,
                        }
                    },
                    headers=response_headers,
                )
            window.append(now)
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id
        logger.info(
            "request_complete method=%s path=%s status=%s latency_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - start) * 1000,
            correlation_id,
        )
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        request_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "request_id": request_id,
                }
            },
        )

    app.include_router(router)
    return app


app = create_app()
