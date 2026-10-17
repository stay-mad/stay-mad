"""Ingest package for Stay Mad."""

from backend.staymad.ingest.parser import (
    IngestedArticleVersion,
    RawArticle,
    map_category_string,
    parse_rss_feed_xml,
    process_raw_article,
)
from backend.staymad.ingest.sources import (
    SourceConfig,
    SourceRegistry,
    UnauthorizedSourceError,
)

__all__ = [
    "IngestedArticleVersion",
    "RawArticle",
    "SourceConfig",
    "SourceRegistry",
    "UnauthorizedSourceError",
    "map_category_string",
    "parse_rss_feed_xml",
    "process_raw_article",
]
