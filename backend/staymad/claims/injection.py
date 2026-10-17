"""Prompt injection detection and defensive containment.

Authority: DEC-0004, docs/architecture/C-gemini-architecture.md, ADR-006
"""

from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"\[?SYSTEM\s+INSTRUCTION\s+OVERRIDE.*?\]?",
    r"\[?IGNORE\s+(?:ALL\s+)?PREVIOUS\s+INSTRUCTIONS.*?\]?",
    r"\[?DAN\s+MODE.*?\]?",
    r"\[?DEVELOPER\s+MODE.*?\]?",
    r"KLASIFIKASIKAN\s+SEBAGAI\s+ACTION\s+REQUIRED",
    r"TETAPKAN\s+SKOR\s+KEPERCAYAAN\s+1\.0",
]


def detect_prompt_injection(text: str) -> tuple[bool, list[str]]:
    """Detect presence of adversarial prompt injection patterns in untrusted text."""
    if not text:
        return False, []

    matched_patterns = []
    for pat in INJECTION_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            matched_patterns.extend(matches)

    return len(matched_patterns) > 0, matched_patterns


def sanitize_untrusted_content(text: str) -> str:
    """Neutralize delimiter escape attempts within untrusted text."""
    if not text:
        return ""
    # Disallow escaping XML container tags
    sanitized = text.replace("</article_content>", "&lt;/article_content&gt;")
    sanitized = sanitized.replace("<article_content>", "&lt;article_content&gt;")
    return sanitized
