from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.deterministic import DeterministicVectorStore
from app.providers.factory import ProviderBundle, build_providers


ADMIN = {"X-Admin-Key": "test-admin-key"}


def upload(client: TestClient, content: bytes, source: str = "fixture://doc"):
    return client.post(
        "/api/v1/admin/knowledge/documents",
        headers=ADMIN,
        files={"file": ("fixture.md", content, "text/markdown")},
        data={"title": "Fixture", "source": source},
    )


def test_admin_protection_and_file_validation(client: TestClient):
    assert client.get("/api/v1/admin/knowledge/documents").status_code == 403
    assert (
        client.get(
            "/api/v1/admin/knowledge/documents", headers={"X-Admin-Key": "wrong"}
        ).status_code
        == 403
    )
    unsupported = client.post(
        "/api/v1/admin/knowledge/documents",
        headers=ADMIN,
        files={"file": ("image.png", b"not an image", "image/png")},
    )
    assert unsupported.status_code == 415


def test_repeated_changed_and_deleted_documents_remove_stale_vectors(
    client: TestClient, providers
):
    first = upload(client, b"alpha support fact " * 100)
    assert first.status_code == 200
    first_body = first.json()
    first_count = first_body["chunk_count"]
    vector_count = len(providers.vectors._records["test-fixtures"])

    repeated = upload(client, b"alpha support fact " * 100)
    assert repeated.status_code == 200
    assert repeated.json()["id"] == first_body["id"]
    assert repeated.json()["version"] == 1
    assert len(providers.vectors._records["test-fixtures"]) == vector_count

    changed = upload(client, b"beta replacement fact")
    assert changed.status_code == 200
    assert changed.json()["version"] == 2
    assert changed.json()["chunk_count"] == 1
    assert len(providers.vectors._records["test-fixtures"]) == 1
    assert first_count >= 1

    deleted = client.delete(
        f"/api/v1/admin/knowledge/documents/{changed.json()['id']}", headers=ADMIN
    )
    assert deleted.status_code == 204
    assert len(providers.vectors._records["test-fixtures"]) == 0


class FailOnceVectorStore(DeterministicVectorStore):
    def __init__(self):
        super().__init__()
        self.should_fail = True

    async def upsert(self, records, namespace):
        if self.should_fail:
            self.should_fail = False
            raise RuntimeError("synthetic partial failure")
        await super().upsert(records, namespace)


def test_partial_indexing_can_be_retried(settings):
    base = build_providers(settings)
    vectors = FailOnceVectorStore()
    providers = ProviderBundle(base.llm, base.embeddings, vectors, base.reranker)
    with TestClient(create_app(settings, providers)) as client:
        failed = upload(client, b"retryable synthetic knowledge")
        assert failed.status_code == 502
        documents = client.get(
            "/api/v1/admin/knowledge/documents", headers=ADMIN
        ).json()
        assert documents[0]["indexing_status"] == "partial"
        retried = client.post(
            f"/api/v1/admin/knowledge/documents/{documents[0]['id']}/retry",
            headers=ADMIN,
        )
        assert retried.status_code == 200
        assert retried.json()["indexing_status"] == "indexed"
        assert len(vectors._records["test-fixtures"]) == 1


def test_readiness_distinguishes_empty_knowledge_base(client: TestClient):
    empty = client.get("/health/ready")
    assert empty.status_code == 200
    assert empty.json()["status"] == "degraded"
    assert empty.json()["knowledge_base"] == "empty"
    assert upload(client, b"readiness fact").status_code == 200
    ready = client.get("/health/ready").json()
    assert ready["status"] == "ready"
    assert ready["knowledge_base"] == "available"
