from __future__ import annotations

import argparse
from pathlib import Path

import httpx

from app.core.config import Settings


DOCUMENTS = (
    (
        "agency_overview.md",
        "Modo Studio Agency Overview",
        "internal://modo-studio/agency-overview",
    ),
    (
        "services_and_pricing.md",
        "Modo Studio Services and Pricing",
        "internal://modo-studio/services-and-pricing",
    ),
    (
        "faqs_and_project_policies.md",
        "Modo Studio FAQs and Project Policies",
        "internal://modo-studio/faqs-and-project-policies",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest approved Modo Studio knowledge"
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument(
        "--documents-dir", type=Path, default=Path("knowledge/source")
    )
    args = parser.parse_args()

    settings = Settings()
    headers = {"X-Admin-Key": settings.admin_api_key}
    with httpx.Client(base_url=args.base_url, headers=headers, timeout=600) as client:
        response = client.get("/api/v1/admin/knowledge/documents")
        response.raise_for_status()
        existing = {item["source"]: item for item in response.json()}

        for filename, title, source in DOCUMENTS:
            current = existing.get(source)
            if current and current["indexing_status"] == "partial":
                response = client.post(
                    f"/api/v1/admin/knowledge/documents/{current['id']}/retry"
                )
                response.raise_for_status()
                result = response.json()
                print(
                    f"retried {source}: {result['indexing_status']} "
                    f"({result['chunk_count']} chunks)"
                )
                continue

            path = args.documents_dir / filename
            with path.open("rb") as document:
                response = client.post(
                    "/api/v1/admin/knowledge/documents",
                    files={"file": (filename, document, "text/markdown")},
                    data={
                        "title": title,
                        "source": source,
                        "source_url": "",
                        "collection": settings.vector_collection,
                    },
                )
            response.raise_for_status()
            result = response.json()
            print(
                f"ingested {source}: {result['indexing_status']} "
                f"({result['chunk_count']} chunks, version {result['version']})"
            )


if __name__ == "__main__":
    main()
