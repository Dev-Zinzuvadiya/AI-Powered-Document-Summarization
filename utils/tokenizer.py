"""Token counting and bounded text chunking."""

from __future__ import annotations

import re
from collections.abc import Iterator


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """Count tokens with tiktoken when installed, otherwise estimate safely."""
    try:
        import tiktoken

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))
    except ImportError:
        return max(1, len(text) // 4)


def chunk_text(text: str, max_chars: int = 12000) -> Iterator[str]:
    """Split long input at paragraph/sentence boundaries."""
    cleaned = text.strip()

    if not cleaned:
        return

    if len(cleaned) <= max_chars:
        yield cleaned
        return

    segments = re.split(r"(?<=[.!?])\s+|\n{2,}", cleaned)
    current = ""

    for segment in segments:
        if not segment.strip():
            continue

        while len(segment) > max_chars:
            if current:
                yield current
                current = ""
            yield segment[:max_chars]
            segment = segment[max_chars:]

        candidate = f"{current} {segment}".strip()
        if len(candidate) > max_chars and current:
            yield current
            current = segment
        else:
            current = candidate

    if current:
        yield current
