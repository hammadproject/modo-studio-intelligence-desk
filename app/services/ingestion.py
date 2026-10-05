from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import content_hash
from app.db.models import KnowledgeChunk, KnowledgeDocument
from app.providers.base import VectorRecord
from app.providers.factory import ProviderBundle


CHUNK_NAMESPACE = uuid.UUID("c5c106d6-d14b-4d1d-a72e-1418278d90aa")
CHUNKING_VERSION = 2


@dataclass(slots=True)
class IngestionResult:
    document: KnowledgeDocument
    chunk_count: int


@dataclass(frozen=True, slots=True)
class PreparedChunk:
    content: str
    section_path: str | None = None
    contains_table: bool = False


def _paragraph_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line.rstrip())
        elif current:
            blocks.append("\n".join(current).strip())
            current = []
    if current:
        blocks.append("\n".join(current).strip())
    return blocks


def _is_markdown_table(block: str) -> bool:
    lines = block.splitlines()
    return (
        len(lines) >= 2
        and "|" in lines[0]
        and bool(re.match(r"^\s*\|?\s*:?-{3,}", lines[1]))
    )


def _split_words(text: str, budget: int, overlap: int) -> list[str]:
    if len(text) <= budget:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + budget)
        if end < len(text):
            boundary = max(
                text.rfind(". ", start, end),
                text.rfind("; ", start, end),
                text.rfind(" ", start, end),
            )
            if boundary > start + budget // 2:
                end = boundary + (1 if text[boundary] in ".;" else 0)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(start + 1, end - min(overlap, budget // 3))
    return chunks


def _split_table(table: str, budget: int) -> list[str]:
    if len(table) <= budget:
        return [table]
    lines = table.splitlines()
    header = lines[:2]
    rows = lines[2:]
    prefix = "\n".join(header)
    tables: list[str] = []
    current = header.copy()
    for row in rows:
        candidate = "\n".join([*current, row])
        if len(candidate) <= budget or len(current) == 2:
            current.append(row)
            continue
        tables.append("\n".join(current))
        current = [*header, row]
    if len(current) > 2:
        tables.append("\n".join(current))
    return tables or [prefix]


def _markdown_sections(text: str) -> list[tuple[list[str], list[str]]]:
    sections: list[tuple[list[str], list[str]]] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []

    def flush() -> None:
        blocks = _paragraph_blocks(current_lines)
        if blocks:
            sections.append((heading_stack.copy(), blocks))
        current_lines.clear()

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if not match:
            current_lines.append(line)
            continue
        flush()
        level = len(match.group(1))
        heading = match.group(2).strip()
        del heading_stack[level - 1 :]
        while len(heading_stack) < level - 1:
            heading_stack.append("Untitled section")
        heading_stack.append(heading)
    flush()
    return sections


def split_document(
    text: str, size: int, overlap: int, *, markdown: bool = False
) -> list[PreparedChunk]:
    clean = text.replace("\r\n", "\n").strip()
    if not clean:
        return []
    sections = (
        _markdown_sections(clean)
        if markdown
        else [([], _paragraph_blocks(clean.splitlines()))]
    )
    chunks: list[PreparedChunk] = []
    for headings, blocks in sections:
        section_path = " > ".join(headings) or None
        prefix = f"Section: {section_path}\n\n" if section_path else ""
        body_budget = max(40, size - len(prefix))
        expanded: list[tuple[str, bool]] = []
        for block in blocks:
            is_table = markdown and _is_markdown_table(block)
            pieces = (
                _split_table(block, body_budget)
                if is_table
                else _split_words(block, body_budget, overlap)
            )
            expanded.extend((piece, is_table) for piece in pieces)

        current: list[tuple[str, bool]] = []
        for block, contains_table in expanded:
            candidate = "\n\n".join(
                item[0] for item in [*current, (block, contains_table)]
            )
            if not current or len(candidate) <= body_budget:
                current.append((block, contains_table))
                continue
            body = "\n\n".join(item[0] for item in current)
            chunks.append(
                PreparedChunk(
                    content=f"{prefix}{body}",
                    section_path=section_path,
                    contains_table=any(item[1] for item in current),
                )
            )
            carried: list[tuple[str, bool]] = []
            carried_size = 0
            for previous in reversed(current):
                additional = len(previous[0]) + (2 if carried else 0)
                if carried_size + additional > overlap:
                    break
                carried.insert(0, previous)
                carried_size += additional
            current = [*carried, (block, contains_table)]
            while (
                len("\n\n".join(item[0] for item in current)) > body_budget
                and len(current) > 1
            ):
                current.pop(0)
        if current:
            body = "\n\n".join(item[0] for item in current)
            chunks.append(
                PreparedChunk(
                    content=f"{prefix}{body}",
                    section_path=section_path,
                    contains_table=any(item[1] for item in current),
                )
            )
    return chunks


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Compatibility helper for callers that need plain-text chunk strings."""
    return [
        chunk.content for chunk in split_document(text, size, overlap, markdown=False)
    ]


class IngestionService:
    def __init__(self, settings: Settings, providers: ProviderBundle):
        self.settings = settings
        self.providers = providers

    async def ingest(
        self,
        session: AsyncSession,
        *,
        title: str,
        source: str,
        text: str,
        source_url: str | None,
        collection: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        namespace = collection or self.settings.vector_collection
        digest = content_hash(text)
        document = (
            await session.execute(
                select(KnowledgeDocument)
                .where(
                    KnowledgeDocument.collection == namespace,
                    KnowledgeDocument.source == source,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if (
            document
            and document.content_hash == digest
            and document.indexing_status == "indexed"
            and document.metadata_json.get("chunking_version") == CHUNKING_VERSION
        ):
            count = len(
                (
                    await session.execute(
                        select(KnowledgeChunk).where(
                            KnowledgeChunk.document_id == document.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            return IngestionResult(document, count)

        supplied_metadata = metadata or {}
        filename = str(supplied_metadata.get("filename", "")).lower()
        content_type = str(supplied_metadata.get("content_type", "")).lower()
        markdown = filename.endswith((".md", ".markdown")) or "markdown" in content_type
        pieces = split_document(
            text,
            self.settings.chunk_size_chars,
            self.settings.chunk_overlap_chars,
            markdown=markdown,
        )
        if not pieces:
            raise AppError(
                422, "empty_document", "Document contains no extractable text"
            )

        old_ids: list[str] = []
        if document:
            old_ids = list(
                (
                    await session.execute(
                        select(KnowledgeChunk.vector_id).where(
                            KnowledgeChunk.document_id == document.id
                        )
                    )
                ).scalars()
            )
            document.version += 1
            document.content_hash = digest
            document.title = title
            document.source_url = source_url
            document.indexing_status = "indexing"
            document.error_message = None
            document.metadata_json = {
                **supplied_metadata,
                "chunking_version": CHUNKING_VERSION,
                "stale_vector_ids": old_ids,
            }
            await session.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id)
            )
        else:
            document = KnowledgeDocument(
                collection=namespace,
                title=title,
                source=source,
                source_url=source_url,
                content_hash=digest,
                version=1,
                indexing_status="indexing",
                metadata_json={
                    **supplied_metadata,
                    "chunking_version": CHUNKING_VERSION,
                    "stale_vector_ids": [],
                },
            )
            session.add(document)
            await session.flush()

        chunks: list[KnowledgeChunk] = []
        for index, piece in enumerate(pieces):
            chunk_id = uuid.uuid5(
                CHUNK_NAMESPACE,
                f"{namespace}:{source}:v{CHUNKING_VERSION}:{digest}:{index}",
            )
            chunk = KnowledgeChunk(
                id=chunk_id,
                document_id=document.id,
                chunk_index=index,
                content=piece.content,
                content_hash=content_hash(piece.content),
                vector_id=str(chunk_id),
                indexing_status="pending",
                metadata_json={
                    "section_path": piece.section_path,
                    "contains_table": piece.contains_table,
                    "chunking_version": CHUNKING_VERSION,
                },
            )
            chunks.append(chunk)
            session.add(chunk)
        await session.commit()

        try:
            vectors = await self.providers.embeddings.embed_documents(
                [chunk.content for chunk in chunks]
            )
            if any(
                len(vector) != self.settings.embedding_dimension for vector in vectors
            ):
                raise ValueError("Embedding provider returned an unexpected dimension")
            records = [
                VectorRecord(
                    id=chunk.vector_id,
                    values=vector,
                    metadata={
                        "content": chunk.content,
                        "chunk_id": str(chunk.id),
                        "document_id": str(document.id),
                        "title": document.title,
                        "source": document.source,
                        "source_url": document.source_url or "",
                        "collection": namespace,
                        "version": document.version,
                        "section_path": chunk.metadata_json.get("section_path")
                        or document.title,
                        "contains_table": chunk.metadata_json.get(
                            "contains_table", False
                        ),
                        "chunking_version": CHUNKING_VERSION,
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            await self.providers.vectors.upsert(records, namespace)
            stale = [
                item
                for item in old_ids
                if item not in {chunk.vector_id for chunk in chunks}
            ]
            await self.providers.vectors.delete(stale, namespace)
            for chunk in chunks:
                chunk.indexing_status = "indexed"
            document.indexing_status = "indexed"
            document.metadata_json = {
                **supplied_metadata,
                "chunking_version": CHUNKING_VERSION,
                "stale_vector_ids": [],
            }
            await session.commit()
            return IngestionResult(document, len(chunks))
        except Exception as exc:
            document.indexing_status = "partial"
            document.error_message = str(exc)[:2000]
            await session.commit()
            raise AppError(
                502, "indexing_failed", "Document indexing was only partially completed"
            ) from exc

    async def retry(
        self, session: AsyncSession, document: KnowledgeDocument
    ) -> IngestionResult:
        chunks = list(
            (
                await session.execute(
                    select(KnowledgeChunk)
                    .where(KnowledgeChunk.document_id == document.id)
                    .order_by(KnowledgeChunk.chunk_index)
                )
            ).scalars()
        )
        if not chunks:
            raise AppError(
                409, "nothing_to_retry", "No pending chunks exist for this document"
            )
        vectors = await self.providers.embeddings.embed_documents(
            [chunk.content for chunk in chunks]
        )
        records = [
            VectorRecord(
                chunk.vector_id,
                vector,
                {
                    "content": chunk.content,
                    "chunk_id": str(chunk.id),
                    "document_id": str(document.id),
                    "title": document.title,
                    "source": document.source,
                    "source_url": document.source_url or "",
                    "collection": document.collection,
                    "version": document.version,
                    "section_path": chunk.metadata_json.get("section_path")
                    or document.title,
                    "contains_table": chunk.metadata_json.get("contains_table", False),
                    "chunking_version": chunk.metadata_json.get(
                        "chunking_version", CHUNKING_VERSION
                    ),
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        try:
            await self.providers.vectors.upsert(records, document.collection)
            stale = document.metadata_json.get("stale_vector_ids", [])
            await self.providers.vectors.delete(stale, document.collection)
            for chunk in chunks:
                chunk.indexing_status = "indexed"
            document.indexing_status = "indexed"
            document.error_message = None
            document.metadata_json = {**document.metadata_json, "stale_vector_ids": []}
            await session.commit()
            return IngestionResult(document, len(chunks))
        except Exception as exc:
            document.indexing_status = "partial"
            document.error_message = str(exc)[:2000]
            await session.commit()
            raise AppError(
                502, "indexing_failed", "Document indexing retry failed"
            ) from exc

    async def delete(self, session: AsyncSession, document: KnowledgeDocument) -> None:
        ids = list(
            (
                await session.execute(
                    select(KnowledgeChunk.vector_id).where(
                        KnowledgeChunk.document_id == document.id
                    )
                )
            ).scalars()
        )
        await self.providers.vectors.delete(ids, document.collection)
        await session.delete(document)
        await session.commit()
