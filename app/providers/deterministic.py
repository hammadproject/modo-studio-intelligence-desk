from __future__ import annotations

import math
import re
from collections import defaultdict

from app.providers.base import ChatTurn, RetrievalMatch, RouteDecision, VectorRecord


class DeterministicLLM:
    mode = "deterministic"

    async def route(
        self, message: str, history: list[ChatTurn], state: dict
    ) -> RouteDecision:
        lowered = message.lower()
        if any(
            term in lowered
            for term in ("human", "person", "representative", "handoff", "expert")
        ):
            return RouteDecision("handoff", reason="explicit_handoff_request")
        if len(message.strip()) < 3:
            return RouteDecision("clarification", reason="message_too_short")
        return RouteDecision("knowledge", reason="knowledge_question")

    async def standalone_query(self, message: str, history: list[ChatTurn]) -> str:
        ambiguous = bool(
            re.match(
                r"^(and|what about|how about|that|it|they|those)\b",
                message.strip(),
                re.I,
            )
        )
        if not ambiguous or not history:
            return message
        prior_user = next(
            (turn.content for turn in reversed(history) if turn.role == "user"), ""
        )
        return f"{prior_user} Follow-up: {message}" if prior_user else message

    async def answer(
        self,
        message: str,
        history: list[ChatTurn],
        context: list[RetrievalMatch],
        system_instructions: str,
    ) -> str:
        if not context:
            raise ValueError("DeterministicLLM requires retrieved context")
        return context[0].content.strip()

    async def stream_answer(
        self,
        message: str,
        history: list[ChatTurn],
        context: list[RetrievalMatch],
        system_instructions: str,
    ):
        yield await self.answer(message, history, context, system_instructions)


class DeterministicEmbeddings:
    mode = "deterministic"

    def __init__(self, dimension: int):
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        values = [0.0] * self.dimension
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            index = (
                int.from_bytes(token.encode("utf-8"), "little", signed=False)
                % self.dimension
            )
            values[index] += 1.0
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class DeterministicVectorStore:
    mode = "deterministic"
    score_semantics = (
        "Cosine similarity in [-1, 1]; a relevance signal, not answer confidence."
    )

    def __init__(self):
        self._records: dict[str, dict[str, VectorRecord]] = defaultdict(dict)
        self.query_count = 0

    async def upsert(self, records: list[VectorRecord], namespace: str) -> None:
        for record in records:
            self._records[namespace][record.id] = record

    async def query(
        self, values, top_k, namespace, metadata_filter=None
    ) -> list[RetrievalMatch]:
        self.query_count += 1
        matches = []
        for record in self._records[namespace].values():
            if metadata_filter and any(
                record.metadata.get(k) != v for k, v in metadata_filter.items()
            ):
                continue
            score = sum(
                left * right for left, right in zip(values, record.values, strict=True)
            )
            matches.append(
                RetrievalMatch(
                    record.id, score, record.metadata["content"], dict(record.metadata)
                )
            )
        return sorted(matches, key=lambda item: item.score, reverse=True)[:top_k]

    async def delete(self, ids: list[str], namespace: str) -> None:
        for vector_id in ids:
            self._records[namespace].pop(vector_id, None)

    async def count(self, namespace: str) -> int:
        return len(self._records[namespace])


class DeterministicReranker:
    mode = "deterministic"

    async def rerank(
        self,
        query: str,
        matches: list[RetrievalMatch],
        top_n: int,
    ) -> list[RetrievalMatch]:
        return matches[:top_n]
