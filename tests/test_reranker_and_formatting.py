from __future__ import annotations

import asyncio

import httpx

from app.core.config import Settings
from app.providers.base import RetrievalMatch
from app.providers.live import JinaReranker
from app.services.formatting import format_customer_answer, progressive_chunks


def _matches() -> list[RetrievalMatch]:
    return [
        RetrievalMatch("first", 0.91, "Website delivery details", {}),
        RetrievalMatch("second", 0.86, "Visual identity pricing", {}),
        RetrievalMatch("third", 0.72, "Introductory call details", {}),
    ]


def test_plain_multiline_items_become_markdown_bullets():
    answer = (
        "It includes:\n\n"
        "Up to five marketing pages\n"
        "Content planning and wireframes\n"
        "Responsive development\n"
        "Basic on-page SEO"
    )

    assert format_customer_answer(answer) == (
        "It includes:\n\n"
        "- Up to five marketing pages\n"
        "- Content planning and wireframes\n"
        "- Responsive development\n"
        "- Basic on-page SEO"
    )


def test_existing_markdown_and_prose_are_preserved():
    markdown = "It includes:\n\n- Strategy\n- Identity\n- Guidelines"
    prose = "Visual identity starts at $4,500."

    assert format_customer_answer(markdown) == markdown
    assert format_customer_answer(prose) == prose
    assert "".join(progressive_chunks(markdown)) == markdown


def test_jina_reranker_uses_returned_order_and_scores():
    async def run():
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers["Authorization"] == "Bearer test-jina-key"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"index": 1, "relevance_score": 0.98},
                        {"index": 0, "relevance_score": 0.61},
                    ]
                },
            )

        settings = Settings(
            environment="test",
            jina_api_key="test-jina-key",
            provider_max_retries=0,
        )
        reranker = JinaReranker(settings)
        reranker._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.jina.ai/v1",
            headers={"Authorization": "Bearer test-jina-key"},
        )
        try:
            ranked = await reranker.rerank("identity price", _matches(), 2)
        finally:
            await reranker._client.aclose()

        assert [match.vector_id for match in ranked] == ["second", "first"]
        assert ranked[0].metadata["reranker_score"] == 0.98
        assert ranked[0].metadata["vector_score"] == 0.86
        assert ranked[0].metadata["reranker_provider"] == "jina"

    asyncio.run(run())


def test_jina_failure_falls_back_to_vector_order():
    async def run():
        settings = Settings(
            environment="test",
            jina_api_key="test-jina-key",
            provider_max_retries=0,
        )
        reranker = JinaReranker(settings)
        reranker._client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(503, json={"detail": "unavailable"})
            ),
            base_url="https://api.jina.ai/v1",
        )
        try:
            ranked = await reranker.rerank("identity price", _matches(), 2)
        finally:
            await reranker._client.aclose()

        assert [match.vector_id for match in ranked] == ["first", "second"]

    asyncio.run(run())
