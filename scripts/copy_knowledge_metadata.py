from __future__ import annotations

import argparse
import os

from sqlalchemy import create_engine, delete, func, insert, select

from app.core.config import Settings
from app.db.models import KnowledgeChunk, KnowledgeDocument


def sync_url(database_url: str) -> str:
    return Settings(database_url=database_url).sync_database_url


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Copy Modo Studio knowledge metadata between PostgreSQL databases "
            "without copying visitor conversations"
        )
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace knowledge rows already present in the target database",
    )
    args = parser.parse_args()

    source_database_url = os.getenv("SOURCE_DATABASE_URL") or Settings().database_url
    target_database_url = os.getenv("TARGET_DATABASE_URL")
    if not target_database_url:
        parser.error("TARGET_DATABASE_URL must be set")

    source_url = sync_url(source_database_url)
    target_url = sync_url(target_database_url)
    if source_url == target_url:
        parser.error("source and target databases must be different")

    source_engine = create_engine(source_url, pool_pre_ping=True)
    target_engine = create_engine(target_url, pool_pre_ping=True)
    try:
        with source_engine.connect() as source:
            documents = [
                dict(row)
                for row in source.execute(
                    select(KnowledgeDocument.__table__)
                ).mappings()
            ]
            chunks = [
                dict(row)
                for row in source.execute(select(KnowledgeChunk.__table__)).mappings()
            ]

        if not documents or not chunks:
            parser.error("the source database has no indexed knowledge metadata")

        with target_engine.begin() as target:
            existing_documents = target.scalar(
                select(func.count()).select_from(KnowledgeDocument)
            )
            existing_chunks = target.scalar(
                select(func.count()).select_from(KnowledgeChunk)
            )
            if (existing_documents or existing_chunks) and not args.replace:
                parser.error(
                    "the target already contains knowledge metadata; "
                    "rerun with --replace only if replacement is intentional"
                )
            if args.replace:
                target.execute(delete(KnowledgeChunk))
                target.execute(delete(KnowledgeDocument))
            target.execute(insert(KnowledgeDocument), documents)
            target.execute(insert(KnowledgeChunk), chunks)

        print(
            f"Copied {len(documents)} knowledge documents and {len(chunks)} "
            "chunks. Conversations and visitor data were not copied."
        )
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()
