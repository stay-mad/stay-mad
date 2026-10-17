"""LLM package for Stay Mad."""

from backend.staymad.llm.base import (
    PROMPT_VERSION_EXTRACT,
    SCHEMA_VERSION_EXTRACT,
    SYSTEM_PROMPT_EXTRACT,
    BaseGeminiClient,
)
from backend.staymad.llm.deterministic_client import DeterministicGeminiClient
from backend.staymad.llm.factory import (
    StartupConfigurationError,
    get_llm_client,
    validate_production_startup,
)
from backend.staymad.llm.gemini_client import GeminiAPIError, GeminiClient
from backend.staymad.llm.schemas import (
    ExtractedClaim,
    ExtractedEntity,
    ExtractInput,
    ExtractResponse,
)

__all__ = [
    "PROMPT_VERSION_EXTRACT",
    "SCHEMA_VERSION_EXTRACT",
    "SYSTEM_PROMPT_EXTRACT",
    "BaseGeminiClient",
    "DeterministicGeminiClient",
    "ExtractInput",
    "ExtractResponse",
    "ExtractedClaim",
    "ExtractedEntity",
    "GeminiAPIError",
    "GeminiClient",
    "StartupConfigurationError",
    "get_llm_client",
    "validate_production_startup",
]
