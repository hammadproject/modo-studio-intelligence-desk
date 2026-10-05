from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.providers.base import (
    EmbeddingProvider,
    LLMProvider,
    RerankerProvider,
    VectorProvider,
)
from app.providers.deterministic import (
    DeterministicEmbeddings,
    DeterministicLLM,
    DeterministicReranker,
    DeterministicVectorStore,
)
from app.providers.live import (
    CloudflareEmbeddings,
    GroqLLM,
    HuggingFaceEmbeddings,
    JinaReranker,
    LocalCrossEncoderReranker,
    PineconeVectorStore,
)


@dataclass(slots=True)
class ProviderBundle:
    llm: LLMProvider
    embeddings: EmbeddingProvider
    vectors: VectorProvider
    reranker: RerankerProvider


def build_providers(settings: Settings) -> ProviderBundle:
    if settings.provider_mode == "deterministic":
        return ProviderBundle(
            DeterministicLLM(),
            DeterministicEmbeddings(settings.embedding_dimension),
            DeterministicVectorStore(),
            DeterministicReranker(),
        )
    if (
        settings.llm_provider != "groq"
        or settings.embedding_provider not in {"cloudflare", "huggingface"}
        or settings.vector_provider != "pinecone"
        or settings.reranker_provider not in {"local", "jina"}
    ):
        raise ValueError("Unsupported live provider selection")
    reranker = (
        JinaReranker(settings)
        if settings.reranker_provider == "jina"
        else LocalCrossEncoderReranker(settings)
    )
    embeddings = (
        CloudflareEmbeddings(settings)
        if settings.embedding_provider == "cloudflare"
        else HuggingFaceEmbeddings(settings)
    )
    return ProviderBundle(
        GroqLLM(settings),
        embeddings,
        PineconeVectorStore(settings),
        reranker,
    )
