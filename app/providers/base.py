from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import AsyncIterator
from typing import Any, Literal, Protocol


@dataclass(slots=True)
class ChatTurn:
    role: str
    content: str


@dataclass(slots=True)
class RouteDecision:
    route: Literal["knowledge", "clarification", "handoff", "action", "off_topic"]
    action_name: str | None = None
    reason: str = ""


@dataclass(slots=True)
class VectorRecord:
    id: str
    values: list[float]
    metadata: dict[str, Any]


@dataclass(slots=True)
class RetrievalMatch:
    vector_id: str
    score: float
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    mode: str

    async def route(
        self, message: str, history: list[ChatTurn], state: dict[str, Any]
    ) -> RouteDecision: ...
    async def standalone_query(self, message: str, history: list[ChatTurn]) -> str: ...
    async def answer(
        self,
        message: str,
        history: list[ChatTurn],
        context: list[RetrievalMatch],
        system_instructions: str,
    ) -> str: ...
    def stream_answer(
        self,
        message: str,
        history: list[ChatTurn],
        context: list[RetrievalMatch],
        system_instructions: str,
    ) -> AsyncIterator[str]: ...


class EmbeddingProvider(Protocol):
    mode: str
    dimension: int

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...


class VectorProvider(Protocol):
    mode: str
    score_semantics: str

    async def upsert(self, records: list[VectorRecord], namespace: str) -> None: ...
    async def query(
        self,
        values: list[float],
        top_k: int,
        namespace: str,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[RetrievalMatch]: ...
    async def delete(self, ids: list[str], namespace: str) -> None: ...
    async def count(self, namespace: str) -> int: ...


class RerankerProvider(Protocol):
    mode: str

    async def rerank(
        self,
        query: str,
        matches: list[RetrievalMatch],
        top_n: int,
    ) -> list[RetrievalMatch]: ...
