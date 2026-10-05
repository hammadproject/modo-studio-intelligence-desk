from __future__ import annotations

import re


_MARKDOWN_LINE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|#{1,6}\s+|>|```)")


def _format_plain_line_block(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) < 3 or any(_MARKDOWN_LINE.match(line) for line in lines):
        return block.strip()
    if any(len(line) > 220 for line in lines):
        return block.strip()

    if lines[0].endswith(":") and len(lines) >= 4:
        return f"{lines[0]}\n\n" + "\n".join(f"- {line}" for line in lines[1:])
    return "\n".join(f"- {line}" for line in lines)


def format_customer_answer(answer: str) -> str:
    """Normalize customer-facing Markdown without rewriting its meaning."""
    normalized = answer.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n\s*\n", normalized)
    return "\n\n".join(_format_plain_line_block(block) for block in blocks).strip()


def progressive_chunks(text: str, target_chars: int = 28) -> list[str]:
    """Split finalized Markdown into small, lossless chunks for SSE display."""
    parts = re.findall(r"\S+\s*|\s+", text)
    chunks: list[str] = []
    current = ""
    for part in parts:
        current += part
        if len(current) >= target_chars or "\n" in current:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return chunks
