from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import psycopg
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.factory import build_providers
from tests.conftest import SYNC_DATABASE_URL, auth, create_conversation


def test_session_isolation_and_token_enforcement(client: TestClient):
    first_id, first_token = create_conversation(client)
    second_id, second_token = create_conversation(client)

    assert client.get(f"/api/v1/conversations/{first_id}/messages").status_code == 401
    assert (
        client.get(
            f"/api/v1/conversations/{first_id}/messages", headers=auth(second_token)
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/v1/conversations/{first_id}/messages", headers=auth(first_token)
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/conversations/{second_id}/messages", headers=auth(second_token)
        ).json()["items"]
        == []
    )


def test_http_only_visitor_session_restores_multiple_conversations(client: TestClient):
    first = client.post("/api/v1/conversations")
    assert first.status_code == 201
    assert first.json()["access_token"] is None
    assert "HttpOnly" in first.headers["set-cookie"]
    first_id = first.json()["conversation_id"]

    sent = client.post(
        f"/api/v1/conversations/{first_id}/messages",
        json={"request_id": "cookie-session-1", "message": "Hello"},
    )
    assert sent.status_code == 200

    second = client.post("/api/v1/conversations")
    second_id = second.json()["conversation_id"]
    restored = client.get("/api/v1/visitor/conversations")
    assert restored.status_code == 200
    assert {item["conversation_id"] for item in restored.json()["items"]} == {
        first_id,
        second_id,
    }
    assert client.get(f"/api/v1/conversations/{first_id}/messages").status_code == 200

    client.cookies.clear()
    assert client.get("/api/v1/visitor/conversations").status_code == 401
    assert client.get(f"/api/v1/conversations/{first_id}/messages").status_code == 401


def test_legacy_browser_conversation_can_be_claimed(client: TestClient):
    conversation_id, token = create_conversation(client)
    claimed = client.post(
        "/api/v1/visitor/conversations/claim",
        json={"conversation_id": conversation_id, "access_token": token},
    )
    assert claimed.status_code == 204
    assert "HttpOnly" in claimed.headers["set-cookie"]
    restored = client.get("/api/v1/visitor/conversations")
    assert restored.status_code == 200
    assert restored.json()["items"][0]["conversation_id"] == conversation_id
    assert (
        client.get(f"/api/v1/conversations/{conversation_id}/messages").status_code
        == 200
    )


def test_presence_and_archived_threads_are_separated_from_inbox(client: TestClient):
    created = client.post("/api/v1/conversations")
    conversation_id = created.json()["conversation_id"]
    heartbeat = client.post(f"/api/v1/conversations/{conversation_id}/presence")
    assert heartbeat.status_code == 200

    admin_headers = {"X-Admin-Key": "test-admin-key"}
    inbox = client.get(
        "/api/v1/admin/conversations?time_window=6h", headers=admin_headers
    )
    summary = next(
        item for item in inbox.json()["items"] if item["id"] == conversation_id
    )
    assert summary["visitor_online"] is True

    with psycopg.connect(SYNC_DATABASE_URL, autocommit=True) as connection:
        connection.execute(
            "UPDATE conversations SET updated_at = now() - interval '2 days', "
            "visitor_last_seen_at = now() - interval '2 days' WHERE id = %s",
            (conversation_id,),
        )

    refreshed = client.get(
        "/api/v1/admin/conversations?time_window=all", headers=admin_headers
    )
    assert conversation_id not in {item["id"] for item in refreshed.json()["items"]}
    history = client.get(
        "/api/v1/admin/conversations?scope=history&time_window=all",
        headers=admin_headers,
    )
    archived = next(
        item for item in history.json()["items"] if item["id"] == conversation_id
    )
    assert archived["support_status"] == "archived"
    takeover = client.post(
        f"/api/v1/admin/conversations/{conversation_id}/takeover",
        headers=admin_headers,
    )
    assert takeover.status_code == 409
    assert takeover.json()["error"]["code"] == "inactive_conversation"


def test_history_persists_across_application_instances(settings):
    with TestClient(create_app(settings, build_providers(settings))) as first:
        conversation_id, token = create_conversation(first)
        response = first.post(
            f"/api/v1/conversations/{conversation_id}/messages",
            headers=auth(token),
            json={"request_id": "persist-1", "message": "What is configured?"},
        )
        assert response.status_code == 200

    with TestClient(create_app(settings, build_providers(settings))) as second:
        history = second.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers=auth(token)
        )
        assert history.status_code == 200
        assert [item["role"] for item in history.json()["items"]] == [
            "user",
            "assistant",
        ]


def test_idempotency_conflict_and_serialized_concurrent_turns(client: TestClient):
    conversation_id, token = create_conversation(client)
    url = f"/api/v1/conversations/{conversation_id}/messages"
    first = client.post(
        url, headers=auth(token), json={"request_id": "same", "message": "Question one"}
    )
    repeated = client.post(
        url, headers=auth(token), json={"request_id": "same", "message": "Question one"}
    )
    conflict = client.post(
        url, headers=auth(token), json={"request_id": "same", "message": "Different"}
    )
    assert first.status_code == repeated.status_code == 200
    assert first.json() == repeated.json()
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"

    def submit(number: int):
        return client.post(
            url,
            headers=auth(token),
            json={
                "request_id": f"concurrent-{number}",
                "message": f"Concurrent question {number}",
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(submit, [1, 2]))
    assert [response.status_code for response in responses] == [200, 200]
    history = client.get(url, headers=auth(token)).json()["items"]
    assert [item["sequence"] for item in history] == list(range(1, len(history) + 1))


def test_rolling_summary_preserves_original_messages(client: TestClient):
    conversation_id, token = create_conversation(client)
    url = f"/api/v1/conversations/{conversation_id}/messages"
    for number in range(4):
        response = client.post(
            url,
            headers=auth(token),
            json={
                "request_id": f"summary-{number}",
                "message": f"turn {number} " + ("x" * 350),
            },
        )
        assert response.status_code == 200
    with psycopg.connect(SYNC_DATABASE_URL) as connection:
        summary, boundary = connection.execute(
            "SELECT summary, summary_through_sequence FROM conversations WHERE id = %s",
            (conversation_id,),
        ).fetchone()
        message_count = connection.execute(
            "SELECT count(*) FROM messages WHERE conversation_id = %s",
            (conversation_id,),
        ).fetchone()[0]
    assert summary
    assert boundary > 0
    assert message_count == 8


def test_conversation_deletion_cascades(client: TestClient):
    conversation_id, token = create_conversation(client)
    response = client.delete(
        f"/api/v1/conversations/{conversation_id}", headers=auth(token)
    )
    assert response.status_code == 204
    assert (
        client.get(
            f"/api/v1/conversations/{conversation_id}/messages", headers=auth(token)
        ).status_code
        == 404
    )
