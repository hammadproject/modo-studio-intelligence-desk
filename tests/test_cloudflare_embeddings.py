from __future__ import annotations

import asyncio
import math

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import ProviderUnavailableError
from app.providers.live import CloudflareEmbeddings


def test_cloudflare_embeddings_use_cls_pooling_and_normalize() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/@cf/baai/bge-base-en-v1.5")
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.read() == (b'{"text":["first","second"],"pooling":"cls"}')
        return httpx.Response(
            200,
            json={
                "success": True,
                "result": {
                    "shape": [2, 3],
                    "data": [[3.0, 4.0, 0.0], [0.0, 0.0, 2.0]],
                },
            },
        )

    settings = Settings(
        _env_file=None,
        embedding_dimension=3,
        cloudflare_account_id="test-account",
        cloudflare_api_token="test-token",
        provider_max_retries=0,
    )
    provider = CloudflareEmbeddings(settings)
    provider._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.cloudflare.com/client/v4/accounts/test-account/ai/run",
        headers={"Authorization": "Bearer test-token"},
    )

    async def run() -> list[list[float]]:
        try:
            return await provider.embed_documents(["first", "second"])
        finally:
            await provider._client.aclose()

    vectors = asyncio.run(run())

    assert vectors == [[0.6, 0.8, 0.0], [0.0, 0.0, 1.0]]
    assert all(math.isclose(sum(v * v for v in vector), 1.0) for vector in vectors)


def test_cloudflare_embeddings_reject_wrong_dimension() -> None:
    settings = Settings(
        _env_file=None,
        embedding_dimension=3,
        cloudflare_account_id="test-account",
        cloudflare_api_token="test-token",
        provider_max_retries=0,
    )
    provider = CloudflareEmbeddings(settings)
    provider._client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"result": {"shape": [1, 2], "data": [[1.0, 2.0]]}},
            )
        ),
        base_url="https://api.cloudflare.com/client/v4/accounts/test-account/ai/run",
        headers={"Authorization": "Bearer test-token"},
    )

    async def run() -> None:
        try:
            await provider.embed_query("question")
        finally:
            await provider._client.aclose()

    with pytest.raises(
        ProviderUnavailableError, match="Embedding provider request failed"
    ):
        asyncio.run(run())
