from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.errors import ProviderUnavailableError
from app.main import create_app
from app.providers.deterministic import DeterministicLLM
from app.providers.factory import ProviderBundle, build_providers
from app.services.chat import is_recognizable_business_question
from tests.conftest import auth, create_conversation


def test_business_followup_is_not_treated_as_ambiguous():
    assert is_recognizable_business_question(
        "Does it include e-commerce and complex animations? If not, what happens if I need them?"
    )
    assert not is_recognizable_business_question("Could you explain that?")


def ingest_fixture(client: TestClient):
    return client.post(
        "/api/v1/admin/knowledge/documents",
        headers={"X-Admin-Key": "test-admin-key"},
        files={
            "file": (
                "neutral_faq.md",
                b"The synthetic support window opens at noon.",
                "text/markdown",
            )
        },
        data={
            "title": "Synthetic FAQ",
            "source": "fixture://neutral-faq",
            "collection": "test-fixtures",
        },
    )


def test_empty_and_low_relevance_fallbacks(client: TestClient):
    conversation_id, token = create_conversation(client)
    url = f"/api/v1/conversations/{conversation_id}/messages"
    empty = client.post(
        url,
        headers=auth(token),
        json={"request_id": "empty-kb", "message": "What are your policies?"},
    )
    assert empty.status_code == 200
    assert empty.json()["sources"] == []
    assert "confirmed answer" in empty.json()["answer"]
    assert "knowledge base" not in empty.json()["answer"].lower()
    assert "approved information" not in empty.json()["answer"].lower()

    assert ingest_fixture(client).status_code == 200
    low = client.post(
        url,
        headers=auth(token),
        json={"request_id": "low", "message": "quantum banana galaxies"},
    )
    assert low.status_code == 200
    assert low.json()["sources"] == []


def test_predefined_social_intents_bypass_retrieval(client: TestClient, providers):
    conversation_id, token = create_conversation(client)
    url = f"/api/v1/conversations/{conversation_id}/messages"

    greeting = client.post(
        url,
        headers=auth(token),
        json={"request_id": "greeting", "message": "Hello!"},
    )
    capabilities = client.post(
        url,
        headers=auth(token),
        json={"request_id": "capabilities", "message": "What can you do?"},
    )

    assert greeting.status_code == 200
    assert greeting.json()["route"] == "general"
    assert "help" in greeting.json()["answer"].lower()
    assert capabilities.status_code == 200
    assert capabilities.json()["route"] == "general"
    assert "services" in capabilities.json()["answer"].lower()
    assert providers.vectors.query_count == 0


def test_single_retrieval_and_sources_are_retrieved(client: TestClient, providers):
    assert ingest_fixture(client).status_code == 200
    conversation_id, token = create_conversation(client)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        headers=auth(token),
        json={
            "request_id": "grounded",
            "message": "When does the synthetic support window open?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert providers.vectors.query_count == 1
    assert body["sources"][0]["source"] == "fixture://neutral-faq"
    assert body["provider_mode"] == "deterministic"
    records = list(providers.vectors._records["test-fixtures"].values())
    assert records
    assert all(record.metadata["section_path"] for record in records)
    assert all(record.metadata["chunking_version"] == 2 for record in records)


def test_streaming_chat_emits_status_delta_and_completed_response(client: TestClient):
    assert ingest_fixture(client).status_code == 200
    conversation_id, token = create_conversation(client)

    with client.stream(
        "POST",
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        headers=auth(token),
        json={
            "request_id": "streamed-grounded",
            "message": "When does the synthetic support window open?",
        },
    ) as response:
        payload = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: status" in payload
    assert "event: delta" in payload
    assert "event: complete" in payload
    assert "The synthetic support window opens at noon." in payload


def test_followup_uses_same_conversation_memory_without_leakage(
    client: TestClient, providers
):
    assert ingest_fixture(client).status_code == 200
    first_id, first_token = create_conversation(client)
    second_id, second_token = create_conversation(client)
    first_url = f"/api/v1/conversations/{first_id}/messages"
    client.post(
        first_url,
        headers=auth(first_token),
        json={"request_id": "topic", "message": "Tell me about the support window"},
    )
    followup = client.post(
        first_url,
        headers=auth(first_token),
        json={"request_id": "follow", "message": "And when does it open?"},
    )
    assert followup.status_code == 200
    second_history = client.get(
        f"/api/v1/conversations/{second_id}/messages", headers=auth(second_token)
    ).json()["items"]
    assert second_history == []


def test_handoff_is_persistent_and_truthful(client: TestClient):
    conversation_id, token = create_conversation(client)
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/handoffs",
        headers=auth(token),
        json={
            "reason": "I want a person",
            "contact_details": {"email": "consented@example.test"},
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "recorded"
    waiting = client.get(
        "/api/v1/admin/conversations?support_status=waiting_for_human",
        headers={"X-Admin-Key": "test-admin-key"},
    )
    assert waiting.status_code == 200
    assert waiting.json()["items"][0]["id"] == conversation_id
    assert waiting.json()["items"][0]["support_status"] == "waiting_for_human"


def test_admin_can_take_over_reply_and_return_conversation_to_ren(client: TestClient):
    conversation_id, token = create_conversation(client)
    visitor_url = f"/api/v1/conversations/{conversation_id}"
    client.post(
        f"{visitor_url}/messages",
        headers=auth(token),
        json={"request_id": "first", "message": "I need help with a website"},
    )
    client.post(
        f"{visitor_url}/handoffs",
        headers=auth(token),
        json={
            "reason": "Please let me speak with a person",
            "contact_details": {"name": "Sarah"},
        },
    )

    login = client.post("/api/v1/admin/session", json={"api_key": "test-admin-key"})
    assert login.status_code == 200
    assert login.json()["authenticated"] is True

    takeover = client.post(f"/api/v1/admin/conversations/{conversation_id}/takeover")
    assert takeover.status_code == 200
    assert takeover.json()["support_status"] == "human_active"

    reply = client.post(
        f"/api/v1/admin/conversations/{conversation_id}/messages",
        json={"message": "Hi Sarah — I’m here and happy to help."},
    )
    assert reply.status_code == 200
    assert reply.json()["role"] == "operator"

    queued = client.post(
        f"{visitor_url}/messages",
        headers=auth(token),
        json={"request_id": "human-active", "message": "Thank you"},
    )
    assert queued.status_code == 200
    assert queued.json()["route"] == "human"
    assert queued.json()["assistant_message_id"] is None
    assert queued.json()["answer"] == ""

    history = client.get(f"{visitor_url}/messages", headers=auth(token)).json()["items"]
    assert "system" in [item["role"] for item in history]
    assert "operator" in [item["role"] for item in history]

    released = client.post(f"/api/v1/admin/conversations/{conversation_id}/release")
    assert released.status_code == 200
    resumed = client.post(
        f"{visitor_url}/messages",
        headers=auth(token),
        json={"request_id": "ren-resumed", "message": "What can you do?"},
    )
    assert resumed.status_code == 200
    assert resumed.json()["assistant_message_id"] is not None


class FailingLLM(DeterministicLLM):
    async def route(self, message, history, state):
        raise ProviderUnavailableError("synthetic outage")


def test_provider_failure_never_returns_fabricated_success(settings):
    base = build_providers(settings)
    providers = ProviderBundle(
        FailingLLM(), base.embeddings, base.vectors, base.reranker
    )
    with TestClient(create_app(settings, providers)) as client:
        conversation_id, token = create_conversation(client)
        response = client.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=auth(token),
            json={"request_id": "failure", "message": "Answer this"},
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "provider_unavailable"
