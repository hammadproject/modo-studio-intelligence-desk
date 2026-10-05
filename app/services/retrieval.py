from __future__ import annotations

from app.core.config import Settings
from app.providers.base import RetrievalMatch
from app.providers.factory import ProviderBundle


class RetrievalService:
    def __init__(self, settings: Settings, providers: ProviderBundle):
        self.settings = settings
        self.providers = providers

    async def retrieve(
        self, query: str, collection: str | None = None
    ) -> list[RetrievalMatch]:
        values = await self.providers.embeddings.embed_query(query)
        namespace = collection or self.settings.vector_collection
        return await self.providers.vectors.query(
            values,
            self.settings.retrieval_candidate_k,
            namespace,
            metadata_filter={"collection": namespace},
        )

    async def rerank(
        self, query: str, matches: list[RetrievalMatch]
    ) -> list[RetrievalMatch]:
        return await self.providers.reranker.rerank(
            query,
            matches,
            self.settings.retrieval_top_k,
        )
