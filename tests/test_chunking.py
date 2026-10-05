from app.services.ingestion import split_document


def test_markdown_chunking_respects_headings_and_paragraphs():
    markdown = """# Root document

## Alpha policy

Alpha body explains the first policy in a self-contained paragraph.

Another alpha paragraph adds a condition without changing sections.

## Beta policy

Beta body explains a separate policy and must not share a chunk with alpha.
"""

    chunks = split_document(markdown, 220, 30, markdown=True)

    assert chunks
    assert all(chunk.content.startswith("Section: Root document >") for chunk in chunks)
    assert any(chunk.section_path == "Root document > Alpha policy" for chunk in chunks)
    assert any(chunk.section_path == "Root document > Beta policy" for chunk in chunks)
    assert all(
        not ("Alpha body" in chunk.content and "Beta body" in chunk.content)
        for chunk in chunks
    )


def test_markdown_table_is_preserved_with_heading_context():
    markdown = """# Service guide

## Pricing

| Service | Starting fee | Duration |
| --- | ---: | --- |
| Identity | $4,500 | 3–5 weeks |
| Website | $7,500 | 5–8 weeks |

Pricing is finalized in a written proposal.
"""

    chunks = split_document(markdown, 500, 40, markdown=True)
    table_chunks = [chunk for chunk in chunks if chunk.contains_table]

    assert len(table_chunks) == 1
    assert table_chunks[0].section_path == "Service guide > Pricing"
    assert "| Service | Starting fee | Duration |" in table_chunks[0].content
    assert "| Identity | $4,500 | 3–5 weeks |" in table_chunks[0].content
    assert "| Website | $7,500 | 5–8 weeks |" in table_chunks[0].content
