from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers.factory import ProviderBundle, build_providers

ROOT = Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = (
    "postgresql+asyncpg://chirpy_test:chirpy_test@localhost:55432/chirpy_test"
)
SYNC_DATABASE_URL = "postgresql://chirpy_test:chirpy_test@localhost:55432/chirpy_test"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        provider_mode="deterministic",
        database_url=TEST_DATABASE_URL,
        admin_api_key="test-admin-key",
        conversation_token_pepper="test-pepper",
        business_config_path=ROOT / "config" / "business.v1.json",
        requests_per_minute=10000,
        embedding_dimension=64,
        vector_collection="test-fixtures",
        retrieval_relevance_threshold=0.2,
        history_token_budget=128,
        summary_trigger_tokens=256,
    )


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    with psycopg.connect(SYNC_DATABASE_URL, autocommit=True) as connection:
        connection.execute(
            "TRUNCATE tool_executions, handoff_requests, knowledge_chunks, knowledge_documents, "
            "messages, chat_requests, conversations, visitor_sessions RESTART IDENTITY CASCADE"
        )
    yield


@pytest.fixture
def providers(settings: Settings) -> ProviderBundle:
    return build_providers(settings)


@pytest.fixture
def client(settings: Settings, providers: ProviderBundle) -> Iterator[TestClient]:
    with TestClient(create_app(settings, providers)) as test_client:
        yield test_client


def create_conversation(client: TestClient) -> tuple[str, str]:
    response = client.post(
        "/api/v1/conversations",
        headers={"X-Conversation-Token-Mode": "bearer"},
    )
    assert response.status_code == 201
    body = response.json()
    return body["conversation_id"], body["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
