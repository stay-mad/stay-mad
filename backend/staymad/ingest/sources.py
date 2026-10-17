"""Source allowlist and policy management.

Authority: DEC-0003, docs/sources.md, config/sources.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field

from backend.staymad.db.models.enums import SourceTier, SourceType

DEFAULT_SOURCES_PATH = Path(__file__).resolve().parents[3] / "config" / "sources.yaml"


class UnauthorizedSourceError(ValueError):
    """Raised when an article domain is not within the authorized allowlist."""


class SourceConfig(BaseModel):
    """Configuration record for an authorized source."""

    id: str
    domain: str
    name: str
    type: str
    url: str
    tier: int
    source_family: str
    rate_limit_per_min: int = 20
    allow_crawler: bool = True
    retention_days_full_text: int = 7
    notes: str | None = None

    @property
    def source_tier_enum(self) -> SourceTier:
        return SourceTier.TIER_1 if self.tier == 1 else SourceTier.TIER_2

    @property
    def source_type_enum(self) -> SourceType:
        type_upper = self.type.upper()
        if "API" in type_upper:
            return SourceType.API
        if "RESMI" in type_upper or "OFFICIAL" in type_upper:
            return SourceType.OFFICIAL_GOV
        if "RSS" in type_upper:
            return SourceType.RSS
        return SourceType.SCRAPE


class SourceRegistry(BaseModel):
    """Registry maintaining authorized sources allowlist."""

    sources: list[SourceConfig] = Field(default_factory=list)
    _by_domain: dict[str, SourceConfig] = {}
    _by_id: dict[str, SourceConfig] = {}
    _by_family: dict[str, list[SourceConfig]] = {}

    def model_post_init(self, context: Any, /) -> None:
        self._by_domain = {}
        self._by_id = {}
        self._by_family = {}
        for src in self.sources:
            norm_domain = self.normalize_domain(src.domain)
            self._by_domain[norm_domain] = src
            self._by_id[src.id] = src
            self._by_family.setdefault(src.source_family, []).append(src)

    @classmethod
    def load_from_yaml(cls, path: Path | str | None = None) -> SourceRegistry:
        resolved_path = Path(path) if path else DEFAULT_SOURCES_PATH
        if not resolved_path.exists():
            raise FileNotFoundError(f"Sources config not found at: {resolved_path}")
        with open(resolved_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        raw_sources = data.get("sources", [])
        sources = [SourceConfig(**item) for item in raw_sources]
        return cls(sources=sources)

    @staticmethod
    def normalize_domain(domain_or_url: str) -> str:
        """Extract and normalize host domain."""
        raw = domain_or_url.strip().lower()
        if "://" in raw:
            parsed = urlparse(raw)
            raw = parsed.netloc or parsed.path
        if ":" in raw:
            raw = raw.split(":", 1)[0]
        raw = raw.removeprefix("www.")
        return raw

    def is_domain_allowed(self, domain_or_url: str) -> bool:
        domain = self.normalize_domain(domain_or_url)
        if domain in self._by_domain:
            return True
        # Check subdomains matching parent authorized domain
        for allowed_domain in self._by_domain:
            if domain == allowed_domain or domain.endswith("." + allowed_domain):
                return True
        return False

    def get_source_for_domain(self, domain_or_url: str) -> SourceConfig | None:
        domain = self.normalize_domain(domain_or_url)
        if domain in self._by_domain:
            return self._by_domain[domain]
        for allowed_domain, src in self._by_domain.items():
            if domain == allowed_domain or domain.endswith("." + allowed_domain):
                return src
        return None

    def get_source_by_id(self, source_id: str) -> SourceConfig | None:
        return self._by_id.get(source_id)

    def validate_article_source(self, domain_or_url: str) -> SourceConfig:
        """Validate source against allowlist. Raise UnauthorizedSourceError if not allowed."""
        source = self.get_source_for_domain(domain_or_url)
        if not source:
            raise UnauthorizedSourceError(
                f"DEC-0003 Violation: Domain '{domain_or_url}' is not in the authorized sources allowlist."
            )
        return source

    def is_same_source_family(self, domain_a: str, domain_b: str) -> bool:
        """Detect media conglomeration / syndication grouping (e.g. Detikcom and CNN Indonesia -> TRANSMEDIA)."""
        src_a = self.get_source_for_domain(domain_a)
        src_b = self.get_source_for_domain(domain_b)
        if not src_a or not src_b:
            return False
        return src_a.source_family == src_b.source_family
