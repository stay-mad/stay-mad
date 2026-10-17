"""Text normalization, hashing, and quote matching utilities.

Authority: docs/sources.md §3, docs/architecture/C-gemini-architecture.md §53-C
"""

from __future__ import annotations

import hashlib
import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalize unicode, strip control characters, and collapse excess whitespace."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    # Remove control characters except standard whitespace
    normalized = "".join(
        ch
        for ch in normalized
        if ch == "\n" or ch == "\t" or not unicodedata.category(ch).startswith("C")
    )
    # Collapse multiple whitespace characters into single space (preserving single newlines if relevant)
    cleaned = re.sub(r"[ \t]+", " ", normalized)
    cleaned = re.sub(r"\n\s*\n+", "\n\n", cleaned)
    return cleaned.strip()


def compute_content_hash(title: str, content: str) -> str:
    """Compute deterministic SHA-256 content hash for deduplication.

    Authority: docs/architecture/B-data-model.md §2.2
    """
    clean_title = clean_text(title).lower()
    clean_body = clean_text(content).lower()
    payload = f"{clean_title}::{clean_body}".encode()
    return hashlib.sha256(payload).hexdigest()


def create_excerpt(text: str, max_length: int = 500) -> str:
    """Extract a concise excerpt <= max_length (default 500 chars per §53-C)."""
    cleaned = clean_text(text)
    if len(cleaned) <= max_length:
        return cleaned

    # Try to break at word boundary
    truncated = cleaned[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > int(max_length * 0.7):
        truncated = truncated[:last_space]
    return truncated.rstrip() + "..."


def verbatim_substring_match(
    needle: str, haystack: str, min_fuzzy_ratio: float = 0.85
) -> tuple[bool, float]:
    """Check if needle exists verbatim or near-verbatim in haystack.

    Returns (matches, score) where score is 1.0 for exact substring match,
    or >= min_fuzzy_ratio for normalized match.
    """
    if not needle or not haystack:
        return False, 0.0

    clean_needle = clean_text(needle)
    clean_haystack = clean_text(haystack)

    # Exact verbatim check
    if clean_needle in clean_haystack:
        return True, 1.0

    # Case-insensitive check
    if clean_needle.lower() in clean_haystack.lower():
        return True, 0.98

    # Normalized punctuation check
    punct_pattern = r"[^\w\s]"
    norm_needle = re.sub(punct_pattern, "", clean_needle).lower()
    norm_haystack = re.sub(punct_pattern, "", clean_haystack).lower()
    if norm_needle and norm_needle in norm_haystack:
        return True, 0.95

    # Sequence matcher / token overlap ratio
    needle_words = set(norm_needle.split())
    if not needle_words:
        return False, 0.0

    # Check if a sliding window of haystack words covers the needle words
    haystack_words = norm_haystack.split()
    w_len = len(needle_words)
    best_overlap = 0.0

    for i in range(max(1, len(haystack_words) - w_len + 1)):
        window_set = set(haystack_words[i : i + w_len + 5])
        overlap = len(needle_words.intersection(window_set)) / len(needle_words)
        if overlap > best_overlap:
            best_overlap = overlap
            if best_overlap >= 1.0:
                break

    if best_overlap >= min_fuzzy_ratio:
        return True, best_overlap

    return False, best_overlap
